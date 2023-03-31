import sys
import redis
import socket
import os
import threading
import queue

from aligner_config import global_settings, pubcloud_settings, genome_params, leangenes_params
from reads_pb2 import Read, PMT_Entry, Result, BatchID
from multiprocessing import pool
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint32
from vsock_handlers import VsockStream

debug = pubcloud_settings["debug"]
do_pmt_proxy = False

matched_reads = queue.Queue()

def client_handler(args): 
    client = VsockStream() 
    endpoint = (args.cid, args.port) 
    client.connect(endpoint) 
    msg = 'Hello, world!' 
    client.send_data(msg.encode()) 
    client.disconnect() 
 
def run_redis_server():
    os.system("redis-server aligner_redis.conf &")

def pmt_proxy(proxy_port, pmt_client_port):
    pmt_entry_block = 1000

    print("Waiting for enclave to send PMT...")
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(('', proxy_port))

    pmt_data = []
    proxy_socket.listen()
    proxy_conn, addr = proxy_socket.accept()

    while True:
        data = proxy_conn.recv(pmt_entry_block)
        pmt_data.append(data)
        if not data:
            break

    print("Waiting to send PMT to client...")
    pmt_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_client_socket.bind(('', pmt_client_port))
    pmt_client_socket.listen()
    conn, addr = pmt_client_socket.accept()

    begin_transfer = False
    while not begin_transfer:
        data = conn.recv(pmt_entry_block)
        if data.decode() == "Start":
            begin_transfer = True

    for entry in pmt_data:
        conn.send(entry)

    pmt_client_socket.close()
    return proxy_socket

def receive_reads(serialized_read_size, crypto, redis_table):
    
    print("CLIENT THREAD STARTED")

    unmatch_batch = b''
    read_parser = Read()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(('', pubcloud_settings["read_port"]))
    
    read_counter = 0
    exact_read_counter = 0
    unmatched_read_counter = 0

    batch_counter = 0

    while True:
        client_socket.listen()
        conn, addr = client_socket.accept()

        print("CLIENT CONNECTION ESTABLISHED!")

        while True:
            data = conn.recv(serialized_read_size * leangenes_params["READ_BATCH_SIZE"])
           
            if data == b'':
                break

            if debug:
                print("-->received data " + str(read_counter))

            data_attempts = 0
            while len(data) < (serialized_read_size * leangenes_params["READ_BATCH_SIZE"]):
                begin_len = len(data)
                remaining_len = (serialized_read_size * leangenes_params["READ_BATCH_SIZE"]) - len(data)
                data += conn.recv(remaining_len)
                end_len = len(data)

                if (end_len == begin_len) and (end_len % serialized_read_size == 0):
                    break

                if debug:
                    print("Data now len " + str(len(data)))
                data_attempts += 1
                if data_attempts > 10:
                    print("WARNING: Stuck in data receiving loop! Remaining bytes: ", remaining_len)

            read_counter += (len(data) / serialized_read_size)
            print("Reads from client: ", read_counter)
            print("Data received: ", len(data), " bytes")            
            
            if leangenes_params["disable_exact_matching"]:
                
                if debug: 
                    print("Passing batch for enclave [no matching check performed].")
                
                unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
                             
                batch_id = BatchID()
                batch_id.num = batch_counter
                batch_id.type = 0
               
                unmatched_socket.send(_VarintBytes(batch_id.ByteSize()))
                unmatched_socket.send(batch_id.SerializeToString())
                unmatched_socket.send(data)
                
                unmatched_socket.close()

                batch_counter += 1
                unmatched_read_counter += read_counter
                data = b''

            else:
                while data:
                    next_read = data[0: serialized_read_size]
                    data = data[serialized_read_size:]
                    check_read = read_parser.ParseFromString(next_read)

                    #Cloud can only see reads in debug mode
                    if debug:
                        decrypted_data = crypto.decrypt(read_parser.read)

                    read_found = redis_table.get(int.from_bytes(read_parser.hash, 'big'))
                    if read_found != None:
                        if debug: 
                            print("Exact match read found.")
                            print("exact: " + str(exact_read_counter))
                        
                        exact_read_counter += 1
                        matched_reads.put((next_read, read_found))

                        if debug: 
                            print("Match at: " + str(read_found, 'utf-8'))
                        
                    else:
                        if debug: 
                            print("Read was not exact match.")
                            print("unmatched: " + str(unmatched_read_counter))
                        unmatched_read_counter += 1
                        unmatch_batch += next_read            

                    if not (exact_read_counter % leangenes_params["LG_BATCH_SIZE"]):
                        if exact_read_counter:
                            print("Trigger normal exact match batch, exact read counter = ",exact_read_counter)
                            exma_thread = threading.Thread(target=send_exact_batch_to_client, args= (batch_counter,))
                            exma_thread.start() 
                            batch_counter += 1

                    if not (unmatched_read_counter % leangenes_params["BWA_BATCH_SIZE"]): 
                        print("Trigger normal BWA batch") 
                        
                        batch_id = BatchID()
                        batch_id.num = batch_counter
                        batch_id.type = 0

                        print("<unmatch_sender>: --> sending ", leangenes_params["BWA_BATCH_SIZE"]  ," non-matches to the enclave")

                        unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
                        
                        unmatched_socket.send(_VarintBytes(batch_id.ByteSize()))
                        unmatched_socket.send(batch_id.SerializeToString())
                        unmatched_socket.send(unmatch_batch)
                        
                        unmatched_socket.close()
                        
                        unmatch_batch = b''
                        batch_counter += 1

        conn.close()

        #FLUSH EXTRA UNALIGNED READS TO ENCLAVE
        pid = os.fork()
        if not pid:
            
            print("Process sending final batch to enclave")
           
            batch_id = BatchID()
            batch_id.num = batch_counter
            batch_id.type = 1

            unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
                         
            unmatched_socket.send(_VarintBytes(batch_id.ByteSize()))
            unmatched_socket.send(batch_id.SerializeToString())
            unmatched_socket.send(unmatch_batch)

            unmatched_socket.close()
            exit()
        else:
            unmatch_batch = b'' 

        #FLUSH EXTRA EXACT MATCHES WHEN ENABLED
        if not leangenes_params["disable_exact_matching"]:    
            pid = os.fork()
            if not pid:
                print("Process is serializing final batch")
                send_exact_batch_to_client(batch_counter + 1, True)
                exit()
            else:
                while not matched_reads.empty():
                    matched_reads.get()
        
        batch_counter = 0
        unmatched_read_counter = 0
        exact_read_counter = 0
    
def send_unmatches_to_enclave(unmatches, batch_id):

    print("<unmatch_sender>: --> sending ", unmatches.qsize()  ," non-matches to the enclave")

    unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
    
    if debug:
        print("Len of unmatched reads: ", unmatches.qsize())

    unmatched_socket.send(_VarintBytes(batch_id.ByteSize()))
    unmatched_socket.send(batch_id.SerializeToString())

    while not unmatches.empty(): 
        unmatched_socket.send(unmatches.get())
        
    unmatched_socket.close()

def send_exact_batch_to_client(batch_counter, last=False):
    global matched_reads

    batch_id = BatchID()
    batch_id.num = batch_counter
    if not last:
        batch_id.type = 0
    else:
        batch_id.type = 2

    batch_queue = queue.Queue()

    num_to_serialize = min(leangenes_params["LG_BATCH_SIZE"], matched_reads.qsize())
    
    print(num_to_serialize, " results to serialize")
    for i in range(num_to_serialize):
        batch_queue.put(matched_reads.get())
    serialize_exact_batch(batch_queue, batch_id)


def serialize_exact_batch(match_queue, batch_id):
    serialized_queue = queue.Queue() 
    read_parser = Read() 

    print("--> <exact match serializer>: serializing an exact batch")
    
    num_serialized = 0
    while not match_queue.empty():
        read, read_found = match_queue.get()
        read_parser.ParseFromString(read)
        serialized_queue.put(serialize_exact_match(read_parser.read, read_parser.align_score, read_found))
        num_serialized += 1
    print(num_serialized, " results have been serialized")

    matched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    matched_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))

    matched_socket.send(_VarintBytes(batch_id.ByteSize()))
    matched_socket.send(batch_id.SerializeToString())

    while not serialized_queue.empty():
        match_buf = serialized_queue.get()
        matched_socket.send(match_buf[0])
        matched_socket.send(match_buf[1])

    matched_socket.close()
    print("--> <exact match serializer>: Finished sending serialized batch.") 
    return True

def serialize_exact_match(seq, qual, pos, qname=b"unlabeled", rname=b"LG"):
    new_result = Result()
    new_result.qname = qname
    new_result.flag = b'0'
    new_result.rname = rname 
    new_result.pos = pos
    new_result.mapq = b'60'
    new_result.cigar = b'*'
    new_result.rnext = b'*'
    new_result.pnext = b'0'
    new_result.tlen = b'0'
    new_result.seq = seq
    new_result.qual = qual

    return (_VarintBytes(new_result.ByteSize()), new_result.SerializeToString())
        
def get_bwa_results(bwa_socket):

    print("ENCLAVE SIDE THREAD STARTS")

    while True:
        result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        bwa_socket.listen()
        conn, addr = bwa_socket.accept()

        if debug:
            print("-->BWA SOCKET CONNECTS SUCCESSFULLY")
       
        print("--> spawn BWA result process")

        pid = os.fork()

        if not pid:
            data = b''
            
            while True:
                begin_len = len(data)
                data += conn.recv(1000000)
                end_len = len(data)

                if not (end_len - begin_len):
                    break

            print(end_len, " bytes from enclave")
            #print(data) 

            result_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))
            result_socket.send(data)
            print("Data sent on result socket!")
            result_socket.close()

            conn.close()

def send_bwa_results(result_queue, batch_id):
    result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if debug:
        print("-->BWA result thread initiated")

    result_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))

    result_socket.send(_VarintBytes(batch_id.ByteSize()))
    result_socket.send(batch_id.SerializeToString())

    if debug:
        print("--> Sending BWA result data!") 
 
    while not result_queue.empty():
        
        #Send single BWA result back to client
        unmatch_buf = result_queue.get()
        result_socket.send(unmatch_buf[0])
        result_socket.send(unmatch_buf[1])
        if debug: 
            print("result: ", unmatch_buf[1]) 
            print("size: ", len(unmatch_buf[0]))
            print("---> Unmatched result back to client.")

    result_socket.close()
    return True

def main():
    global bwa_socket

    serialized_read_size = genome_params["SERIALIZED_READ_SIZE"]

    #Network params
    read_port = pubcloud_settings["read_port"]
    pmt_client_port = pubcloud_settings["pmt_client_port"]
    unmatched_port = pubcloud_settings["unmatched_port"]
    redis_port = global_settings["redis_port"]
    bwa_port = pubcloud_settings["bwa_port"]

    if leangenes_params["CRYPTO_MODE"] == "debug":
        cipherkey = b'0' * 32
    else:
        cipherkey = get_random_bytes(32)

    crypto = AES.new(cipherkey, AES.MODE_ECB) 

    if do_pmt_proxy: 
        proxy_socket = pmt_proxy(unmatched_port, pmt_client_port)
    else:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    run_redis_server()

    redis_table = redis.Redis(host=global_settings["redis_ip"], port=redis_port, db=0, password='lean-genes-17')

    if leangenes_params["disable_exact_matching"]:
        print("**************************************************************")
        print("You have disabled the LEAN-GENES exact matching functionality!")
        print("**************************************************************")
    
    if not pubcloud_settings["only_indexing"]:
        print("\n")
        print("~~~ PUBLIC CLOUD IS READY TO RECEIVE READS! ~~~")

        pid = os.fork()
        
        #Process to interact with client
        if pid:
            receive_reads(serialized_read_size, crypto, redis_table)
            return
        
        #from_client_thread = threading.Thread(target=receive_reads, args= (serialized_read_size, crypto, redis_table,))
        #from_client_thread.start()        

        #Process to interact with enclave
        else:
            bwa_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bwa_socket.bind(('', pubcloud_settings["bwa_port"]))
            get_bwa_results(bwa_socket)
            bwa_socket.close()

        #from_enclave_thread = threading.Thread(target=get_bwa_results, args= (bwa_socket,))
        #from_enclave_thread.start()

    else:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") 
        print("You have activated LeanGenes in ONLY INDEXING mode!")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    while True:
        pass 

if __name__ == "__main__":
    main()

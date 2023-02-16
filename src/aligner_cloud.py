import sys
import redis
import socket
import os
import threading
import queue

from aligner_config import global_settings, pubcloud_settings, genome_params, leangenes_params
from reads_pb2 import Read, PMT_Entry, Result
from multiprocessing import pool
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint32
from vsock_handlers import VsockStream

debug = pubcloud_settings["debug"]
mode = "DEBUG"
do_pmt_proxy = False

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

    unmatched_reads = queue.Queue()
    matched_reads = queue.Queue()
    read_parser = Read()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(('', pubcloud_settings["read_port"]))
    
    read_counter = 0
    exact_read_counter = 0
    unmatched_read_counter = 0

    while True:
        client_socket.listen()
        conn, addr = client_socket.accept()

        print("CLIENT CONNECTION ESTABLISHED!")

        while True:
            data = conn.recv(serialized_read_size)
            
            if data == b'':
                break

            read_counter += 1
            
            if debug:
                print("-->received data " + str(read_counter))

            data_attempts = 0
            while len(data) < serialized_read_size:
                data += conn.recv(serialized_read_size - len(data))
                if debug:
                    print("Data now len " + str(len(data)))
                data_attempts += 1
                if data_attempts > 10:
                    print("WARNING: Stuck in data receiving loop!")

            check_read = read_parser.ParseFromString(data)

	        #Cloud can only see reads in debug mode
            if debug:
                decrypted_data = crypto.decrypt(read_parser.read)

            if pubcloud_settings["disable_exact_matching"]:
                unmatched_read_counter += 1
                unmatched_reads.put(data)
                if debug: 
                    print("Storing data for enclave [no matching check performed].")
            else:
                #Sanity check, avoid looking in db for connection-ending/malformed msgs
                if len(read_parser.hash) > 0:
                    read_found = redis_table.get(int.from_bytes(read_parser.hash, 'big'))
                    if read_found != None:
                        if debug: 
                            print("Exact match read found.")
                            print("exact: " + str(exact_read_counter))
                        
                        exact_read_counter += 1
                        matched_reads.put((data, read_found))

                        if debug: 
                            print("Match at: " + str(read_found, 'utf-8'))
                        
                        #assemble SAM entry
                        #serialized_match = serialize_exact_match(read_parser.read, read_parser.align_score, read_found)
                        #serialized_matches.append(serialized_match)

                    else:
                        if debug: 
                            print("Read was not exact match.")
                            print("unmatched: " + str(unmatched_read_counter))
                        unmatched_read_counter += 1
                        unmatched_reads.put(data)                

            if matched_reads.qsize() >= leangenes_params["LG_BATCH_SIZE"]:
                if exact_read_counter % (leangenes_params["LG_BATCH_SIZE"]) == 0:
                    batch_queue = queue.Queue()
                    for i in range(leangenes_params["LG_BATCH_SIZE"]):
                        batch_queue.put(matched_reads.get())
                    match_serializer_thread = threading.Thread(target=serialize_exact_batch, args=(batch_queue,))
                    match_serializer_thread.start()

            if unmatched_reads.qsize() >= leangenes_params["BWA_BATCH_SIZE"]: 
                if unmatched_read_counter % (leangenes_params["BWA_BATCH_SIZE"]) == 0: 
                    batch_queue = queue.Queue()
                    for i in range(leangenes_params["BWA_BATCH_SIZE"]):
                        batch_queue.put(unmatched_reads.get())
                    unmatch_sender_thread = threading.Thread(target=send_unmatches_to_enclave, args=(batch_queue,))
                    unmatch_sender_thread.start()

            if debug:
                print("Data: ")
                print(decrypted_data)
                print("Hash: ")
                print(read_parser.hash)
            
            if not data:
                break

        #FLUSH EXTRA EXACT MATCHES
        if not matched_reads.empty():
            
            #match_serializer_thread = threading.Thread(target=serialize_exact_batch, args=(matched_reads,))
            #match_serializer_thread.start()
            
            pid = os.fork()
            if not pid:
                print("Process is serializing final batch")
                serialize_exact_batch(matched_reads)
                exit()

        #FLUSH EXTRA UNALIGNED READS TO ENCLAVE
        if not unmatched_reads.empty():
            
            #unmatch_sender_thread = threading.Thread(target=send_unmatches_to_enclave, args=(unmatched_reads,))
            #unmatch_sender_thread.start()

            pid = os.fork()
            if not pid:
                print("Process sending final batch to enclave")
                send_unmatches_to_enclave(unmatched_reads)
                exit()

        unmatched_read_counter = 0
        exact_read_counter = 0
    
    #unmatched_socket.send(unmatched_reads)
    unmatched_reads.clear()

def send_unmatches_to_enclave(unmatches):

    print("<unmatch_sender>: --> sending non-matches to the enclave")

    unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
    
    if debug:
        print("Len of unmatched reads: ", unmatches.qsize())
    
    while not unmatches.empty(): 
        unmatched_socket.send(unmatches.get())

    unmatched_socket.close()

def serialize_exact_batch(match_queue):
    serialized_queue = queue.Queue() 
    read_parser = Read() 

    print("--> <exact match serializer>: serializing an exact batch")

    while not match_queue.empty():
        read, read_found = match_queue.get()
        read_parser.ParseFromString(read)
        serialized_queue.put(serialize_exact_match(read_parser.read, read_parser.align_score, read_found))

    matched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    matched_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))

    while not serialized_queue.empty():
        match_buf = serialized_queue.get()
        matched_socket.send(match_buf[0])
        matched_socket.send(match_buf[1])

    matched_socket.close()
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
        bwa_socket.listen()
        conn, addr = bwa_socket.accept()

        if debug:
            print("-->BWA SOCKET CONNECTS SUCCESSFULLY")
       
        pid = os.fork()

        if not pid:
            print("--> spawn BWA result process")
            data = b''
            num_appended = 0

            serialized_unmatches = queue.Queue()

            while True:
                data += conn.recv(10000)

                if data == b'':
                    break

                msg_len, size_len = _DecodeVarint32(data, 0)
                        
                if (msg_len + size_len > len(data)):
                    data += conn.recv(10000)
                    continue

                serialized_unmatches.put((data[0:size_len], data[size_len: msg_len + size_len]))
                num_appended += 1
                if debug:
                    print("\nAPPEND TO UNMATCHES",data[size_len: msg_len+size_len])
                    print("size_len", size_len)
                    print("msg_len", msg_len) 
                data = data[msg_len + size_len:]

            conn.close()
            send_bwa_results(serialized_unmatches)

def send_bwa_results(result_queue):
    result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if debug:
        print("-->BWA result thread initiated")

    result_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))
    
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

    if mode == "DEBUG":
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

    if pubcloud_settings["disable_exact_matching"]:
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

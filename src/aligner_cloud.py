import sys
import redis
import socket
import os
import threading

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

matched_lock = threading.Lock()
unmatched_lock = threading.Lock()
serialized_matches = []
serialized_unmatches = []

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

    global serialized_matches

    read_parser = Read()

    #Use read size to calc expected bytes for a read
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_socket.settimeout(30)
    client_socket.bind(('', pubcloud_settings["read_port"]))
    read_counter = 0

    exact_read_counter = 0
    serialized_matches = []
    #serialized_unmatches = []
    unmatched_read_counter = 0
    unmatched_reads = []

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
                unmatched_reads.append(data)
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
                        
                        #assemble SAM entry
                        exact_read_counter += 1

                        if debug: 
                            print("Match at: " + str(read_found, 'utf-8'))
                        serialized_match = serialize_exact_match(read_parser.read, read_parser.align_score, read_found)
                        serialized_matches.append(serialized_match)
                        #print("\t-->Serialized match appended")
                    else:
                        if debug: 
                            print("Read was not exact match.")
                            print("unmatched: " + str(unmatched_read_counter))
                        unmatched_read_counter += 1
                        unmatched_reads.append(data)                

            if len(unmatched_reads) >= leangenes_params["BWA_BATCH_SIZE"]: 
                if unmatched_read_counter % (leangenes_params["BWA_BATCH_SIZE"]) == 0: 
                    unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
                    
                    if debug:
                        print("Len of unmatched reads: " + str(len(unmatched_reads)))
                    for read in unmatched_reads:
                        unmatched_socket.send(read)
                    #TODO: CHECK THIS!
                    unmatched_reads.clear()
                    unmatched_socket.close()

            if debug:
                print("Data: ")
                print(decrypted_data)
                print("Hash: ")
                print(read_parser.hash)
            
            if not data:
                break

        #FLUSH EXTRA UNALIGNED READS TO ENCLAVE
        if len(unmatched_reads) > 0:
            unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"]))
            while len(unmatched_reads) > 0:
                unmatched_socket.send(unmatched_reads.pop())
            unmatched_socket.close()

        #FLUSH EXTRA EXACT MATCHES
        #start_new_thread(aggregate_alignment_results, (0, len(serialized_matches),))

        unmatched_read_counter = 0
        exact_read_counter = 0
    
    #unmatched_socket.send(unmatched_reads)
    unmatched_reads.clear()

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
    global serialized_unmatches

    print("ENCLAVE SIDE THREAD STARTS")

    while True:
        bwa_socket.listen(10)
        conn, addr = bwa_socket.accept()

        if debug:
            print("-->BWA SOCKET CONNECTS SUCCESSFULLY")
        
        data = b''
        while True:
            data += conn.recv(10000)

            if data == b'':
                break

            msg_len, size_len = _DecodeVarint32(data, 0)
                    
            if (msg_len + size_len > len(data)):
                data += conn.recv(10000)
                continue

            serialized_unmatches.append((data[0:size_len], data[size_len: msg_len + size_len]))
            if debug:
                print("\nAPPEND TO UNMATCHES",data[size_len: msg_len+size_len])
                print("size_len", size_len)
                print("msg_len", msg_len) 
            data = data[msg_len + size_len:]

        conn.close()
        result_aggregate_thread = threading.Thread(target=aggregate_alignment_results, args=(len(serialized_unmatches), len(serialized_matches),))
        result_aggregate_thread.start()

def aggregate_alignment_results(num_unmatched, num_matched):
    global serialized_matches, serialized_unmatches
    global matched_lock, unmatched_lock

    result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #result_socket.settimeout(10)

    if (num_unmatched == 0) and (num_matched == 0):
        return True

    if debug:
        print("-->Aggregator thread initiated")
        print("-->Aggregator called with (" + str(num_unmatched) + "," + str(num_matched) + ")")

    matched_aggregate = 0
    unmatched_aggregate = 0

    result_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))
    
    if debug:
        print("-->Aggregator sending data!") 
 
    #We want atomic pops from the lists!
    got_unmatch_lock = False
    while not got_unmatch_lock:
        got_unmatch_lock = unmatched_lock.acquire()
        if got_unmatch_lock:
            if debug:
                print("Got unmatch lock.")
            real_unmatched = num_unmatched
            if len(serialized_unmatches) < num_unmatched:
                real_unmatched = len(serialized_unmatches)

            while (unmatched_aggregate < real_unmatched):
                
                #Send single BWA result back to client
                unmatch_buf = serialized_unmatches.pop()
                result_socket.send(unmatch_buf[0])
                result_socket.send(unmatch_buf[1])
                if debug: 
                    print("result: ", unmatch_buf[1]) 
                    print("size: ", len(unmatch_buf[0]))
                unmatched_aggregate += 1
                
                if debug:
                    print("---> Unmatched result back to client.")

            unmatched_lock.release()
            if debug:
                print("Release unmatch lock.")

    #Atomic pops, pt 2
    got_match_lock = False
    while not got_match_lock:
        got_match_lock = matched_lock.acquire()
        if got_match_lock:
            if debug: 
                print("Got match lock.")
            real_matched = num_matched
            if len(serialized_matches) < num_matched:
                real_matched = len(serialized_matches)

            while (matched_aggregate < real_matched):
                
                #Send single exact match back to client
                match_buf = serialized_matches.pop()
                result_socket.send(match_buf[0]) 
                result_socket.send(match_buf[1])
                
                matched_aggregate += 1
                
                if debug:
                    print("---> Matched result back to client.")

            matched_lock.release()
            if debug:
                print("Release match lock.")

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
        from_client_thread = threading.Thread(target=receive_reads, args= (serialized_read_size, crypto, redis_table,))
        from_client_thread.start()        

        bwa_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bwa_socket.bind(('', pubcloud_settings["bwa_port"]))
        
        from_enclave_thread = threading.Thread(target=get_bwa_results, args= (bwa_socket,))
        from_enclave_thread.start()

        #bwa_socket_list = [bwa_socket for i in range(1)]
        #bwa_pool = pool.ThreadPool(processes=1)
        #bwa_pool.map(get_bwa_results, bwa_socket_list)
        #bwa_pool.close()

    else:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") 
        print("You have activated LeanGenes in ONLY INDEXING mode!")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    while True:
        pass 

if __name__ == "__main__":
    main()

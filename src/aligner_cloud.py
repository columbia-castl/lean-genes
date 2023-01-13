import sys
import redis
import socket
import os
import threading

from aligner_config import global_settings, pubcloud_settings, genome_params, leangenes_params
from reads_pb2 import Read, PMT_Entry, Result
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from _thread import *
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint32
from vsock_handlers import VsockStream

debug = False
mode = "DEBUG"
do_pmt_proxy = False

bwa_socket = ""

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
    global serialized_matches, serialized_unmatches

    read_parser = Read()

    #Use read size to calc expected bytes for a read
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_socket.settimeout(30)
    client_socket.bind(('', pubcloud_settings["read_port"]))
    read_counter = 0

    exact_read_counter = 0
    serialized_matches = []
    serialized_unmatches = []
    unmatched_read_counter = 0
    unmatched_reads = []

    while True:
        client_socket.listen()
        conn, addr = client_socket.accept()
        
        while True:
            data = conn.recv(serialized_read_size)
            read_counter += 1
            
            if debug:
                print("-->received data " + str(read_counter))
            
            check_read = read_parser.ParseFromString(data)

	        #Cloud can only see reads in debug mode
            if debug:
                decrypted_data = crypto.decrypt(read_parser.read)

	        #Sanity check, avoid looking in db for connection-ending/malformed msgs
            if len(read_parser.hash) > 0:
                read_found = redis_table.get(int.from_bytes(read_parser.hash, 'big'))
                if read_found != None:
                    print("Exact match read found.")
                    #assemble SAM entry
                    exact_read_counter += 1
                    if debug: 
                        print("Match at: " + str(read_found, 'utf-8'))
                    serialized_match = serialize_exact_match(read_parser.read, read_parser.align_score, read_found)
                    serialized_matches.append(serialized_match)
                    print("\t-->Serialized match appended")
                else:
                    print("Read was not exact match.")
                    unmatched_read_counter += 1
                    unmatched_reads.append(data)                

            if len(unmatched_reads) > leangenes_params["unmatched_threshold"]: 
                if unmatched_read_counter == leangenes_params["unmatched_threshold"] + 1: 
                    unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    unmatched_socket.connect((pubcloud_settings["enclave_ip"], pubcloud_settings["unmatched_port"])) 
                if debug:
                    print("Len of unmatched reads: " + str(len(unmatched_reads)))
                for read in unmatched_reads:
                    unmatched_socket.send(read)
                unmatched_reads.clear()
                unmatched_socket.close()

            if debug:
                print("Data: ")
                print(decrypted_data)
                print("Hash: ")
                print(read_parser.hash)
            
            if not data:
                break

        #unmatched_socket.close()
        
        start_new_thread(aggregate_alignment_results, (unmatched_read_counter, exact_read_counter,))
        #start_new_thread(aggregate_alignment_results, (0, len(serialized_matches),))

        unmatched_read_counter = 0
        exact_read_counter = 0
    
    #unmatched_socket.send(unmatched_reads)
    unmatched_reads.clear()

def serialize_exact_match(seq, qual, pos, qname=b"unlabeled", rname=b"*"):
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
        

def aggregate_alignment_results(num_unmatched, num_matched):
    global bwa_socket, serialized_matches

    result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if (num_unmatched == 0) and (num_matched == 0):
        return True

    #if debug:
    print("-->Aggregator thread initiated")
    print("-->Aggregator called with (" + str(num_unmatched) + "," + str(num_matched) + ")")

    matched_aggregate = 0
    
    result_socket.connect((pubcloud_settings["client_ip"], pubcloud_settings["result_port"]))
    print("-->Aggregator sending data!") 
    #Initiate result transfer by enclave
    if num_unmatched > 0:
        bwa_socket.listen()
        conn, addr = bwa_socket.accept()

        print("-->BWA SOCKET CONNECTS SUCCESSFULLY")

        read_pair = []
        read_size = 0
        data = conn.recv(1024)
        while data != b'':
            msg_len, size_len = _DecodeVarint32(data, 0)
            print(str(msg_len) + " msg len")

            if (msg_len + size_len > len(data)):
                data += conn.recv(1024)
                continue

            #Send a single read back to client
            result_socket.send(data[0:msg_len+size_len])
            print("Unmatched read sent.")

            data = data[msg_len + size_len:]

            print("Data POST SEND")
            print(data)

        conn.close()

    while (matched_aggregate < num_matched):
        match_buf = serialized_matches.pop()
        result_socket.send(match_buf[0]) 
        result_socket.send(match_buf[1])
        print(match_buf[1])
        matched_aggregate += 1

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

    bwa_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bwa_socket.bind(('', bwa_port))

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
    receive_reads(serialized_read_size, crypto, redis_table)

if __name__ == "__main__":
    main()

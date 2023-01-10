import sys
import redis
import socket
import os

from aligner_config import global_settings, pubcloud_settings, genome_params
from reads_pb2 import Read, PMT_Entry, Result
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from vsock_handlers import VsockStream

debug = False
mode = "DEBUG"

do_pmt_proxy = False

unmatched_threshold = 0
matched_threshold = 0

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

def receive_reads(client_port, unmatched_socket, unmatched_port, serialized_read_size, crypto, redis_table):

    read_parser = Read()

    #Use read size to calc expected bytes for a read
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_socket.settimeout(30)
    client_socket.bind(('', client_port))
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

            if len(unmatched_reads) > unmatched_threshold: 
                if unmatched_read_counter == unmatched_threshold + 1: 
                    unmatched_socket.connect((pubcloud_settings["enclave_ip"], unmatched_port)) 
                if debug:
                    print("Len of unmatched reads: " + str(len(unmatched_reads)))
                for read in unmatched_reads:
                    unmatched_socket.send(read)
                unmatched_reads.clear()

            if debug:
                print("Data: ")
                print(decrypted_data)
                print("Hash: ")
                print(read_parser.hash)
            
            if not data:
                break

    #unmatched_socket.send(unmatched_reads)
    unmatched_reads.clear()

def serialize_exact_match(seq, qual, pos, qname=b"unlabeled", rname=b"unlabeled"):
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

    return new_result.SerializeToString()
        

def aggregate_alignment_results():
    pass

def main():
    serialized_read_size = genome_params["SERIALIZED_READ_SIZE"]

    #Network params
    read_port = pubcloud_settings["read_port"]
    pmt_client_port = pubcloud_settings["pmt_client_port"]
    vsock_port = pubcloud_settings["vsock_port"]
    redis_port = global_settings["redis_port"]

    if mode == "DEBUG":
        cipherkey = b'0' * 32
    else:
        cipherkey = get_random_bytes(32)

    crypto = AES.new(cipherkey, AES.MODE_ECB) 

    if do_pmt_proxy: 
        proxy_socket = pmt_proxy(vsock_port, pmt_client_port)
    else:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    run_redis_server()

    redis_table = redis.Redis(host=global_settings["redis_ip"], port=redis_port, db=0, password='lean-genes-17')
    receive_reads(read_port, proxy_socket, vsock_port, serialized_read_size, crypto, redis_table)

if __name__ == "__main__":
    main()

import hashlib
import hmac
import base64
import matplotlib.pyplot as plt
import sys
import time
import re
import redis
import socket

from Crypto.Random import get_random_bytes 
from Crypto.Random import random
from Crypto.Cipher import AES

#Global params to help with debug and test
debug = False
check_locations = False
verify_redis = False

limit_hashes = False 
hash_limit = 100

limit_lines = False
line_limit = 100

mode = "DEBUG"

#After x hashes print progress
progress_indicator = 5000000

class VsockListener:
    """Server"""
    def __init__(self, conn_backlog=128):
        self.conn_backlog = conn_backlog

    def bind(self, port):
        """Bind and listen for connections on the specified port"""
        self.sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
        self.sock.bind((socket.VMADDR_CID_ANY, port))
        self.sock.listen(self.conn_backlog)

    def recv_data(self):
        """Receive data from a remote endpoint"""
        while True:
            (from_client, (remote_cid, remote_port)) = self.sock.accept()
            # Read 1024 bytes at a time
            while True:
                try:
                    data = from_client.recv(1024).decode()
                except socket.error:
                    break
                if not data:
                    break
                print(data, end='', flush=True)
            print()
            from_client.close()

    def send_data(self, data):
        """Send data to a renote endpoint"""
        while True:
            (to_client, (remote_cid, remote_port)) = self.sock.accept()
            to_client.sendall(data)
            to_client.close()


def server_handler(port):
    server = VsockListener()
    server.bind(port)
    server.recv_data()

def get_ref(ref_file_path):
    print("\nRetrieve reference file at path " + ref_file_path)
    
    ref_file = open(ref_file_path, "r")
    full_ref = ref_file.readlines() 
  
    ref_file.close()
    return full_ref

def sliding_window_table(key, ref_lines, redis_table, read_size=151):

    #Important stat/debug counters
    hashes_generated = 0
    lines_processed = 0
    chrom_counter = 0
   
    #Data structure initialization
    hash_buffer = b''
    end_hashing = False

    #Redis pipeline
    redis_pipe = redis_table.pipeline()
    batch_size = 1000
    batch_counter = 0

    while (len(ref_lines) > 0): 

        if end_hashing:
            break

        if debug:
            print("Remaining ref lines: " + str(len(ref_lines)))

        load_line = ref_lines.pop(0)[:-1]
        if debug:
            print("Line loaded: " + load_line)

        # Detect the start of a new chromosome
        if ">" in load_line:
            chrom_counter += 1
            lines_processed += 1
            hash_buffer = b''
            print(">>>Processing next chromosome")
            continue
        
        # Filter out full lines of N bases
        elif load_line == ('N' * len(load_line)):
            lines_processed += 1
            continue
        
        # Default case: Load line into hash buffer
        else:
            hash_buffer += bytes(load_line, 'utf-8')

        if (hashes_generated == 0) and (len(hash_buffer) >= read_size):
            print("Chromosome has been filtered. Begin sliding window hash.")

        while (len(hash_buffer) >= read_size):
            if debug: 
                print("Hashing window: ")
                print(hash_buffer[0:read_size])
            
            newhash = hmac.new(key, hash_buffer[0:read_size], hashlib.sha256)
            curr_hash = newhash.digest()

            batch_counter += 1 
            redis_pipe.set(int.from_bytes(curr_hash, 'big'), hashes_generated) 
            if batch_counter % batch_size == 0:
                redis_response = redis_pipe.execute()
                print(redis_response)
                batch_counter = 0

            if verify_redis:
                print(redis_table.get(int.from_bytes(curr_hash, 'big')))

            if debug:
                print(curr_hash)
           
            hashes_generated += 1
            hash_buffer = hash_buffer[1:]          

            if limit_hashes and (hashes_generated > hash_limit):
                end_hashing = True
                break

            if hashes_generated % progress_indicator == 0:
                print(hashes_generated)

        lines_processed += 1
        
        if limit_lines and (lines_processed > line_limit):
            break
    
    #Final pipeline flush
    redis_response = redis_pipe.execute()
    print(redis_response)
    
    print("\n*******************************************")
    print(str(hashes_generated) + " hashes generated")
    print(str(lines_processed) + " lines processed") 
    print(str(chrom_counter) + " chromosome(s) processed")
    print("*******************************************")

    return True 

def main():
    #Parameters
    read_length = 15 #be sure this aligns with your fastq
    encrypted_port = 5005

    #Files
    if len(sys.argv) == 1:
        fasta = "../test_data/small_ref.fa" 
    else:
        fasta = sys.argv[1]
   
    #Cloud-side operations   
    #TODO: DONT HARDCODE THESE PARAMETERS 
    redis_table = redis.Redis(host='44.202.235.148', port=6379, db=0, password='lean-genes-17')

    #Reference setup
    processed_ref = get_ref(fasta)

    if mode == "DEBUG":
        key = b'0' * 32
    else:
        key = get_random_bytes(32)    
    sliding_window_table(key, processed_ref, redis_table, read_length)

    #Run server for receiving encrypted reads
    server_handler(encrypted_port)

if __name__ == "__main__":
    main()


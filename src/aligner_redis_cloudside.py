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
check_locations = True
verify_redis = True

limit_hashes = False 
hash_limit = 100

limit_lines = False
line_limit = 100

#After x hashes print progress
progress_indicator = 5000000

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
           
            redis_table.set(int.from_bytes(curr_hash, 'big'), hashes_generated) 
            
            if verify_redis:
                print(redis_table.get(int.from_bytes(curr_hash, 'big')))

            if debug:
                print(curr_hash)
                print("Placing hash in bucket " + str(table_index) + "\n")
           
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
      
    print("\n*******************************************")
    print(str(hashes_generated) + " hashes generated")
    print(str(lines_processed) + " lines processed") 
    print(str(chrom_counter) + " chromosome(s) processed")
    print("*******************************************")

    return True 

def receive_reads(read_port, read_size):
    #Use read size to calc expected bytes for a read
    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    read_socket.bind(('127.0.0.1', read_port))
    read_socket.listen()
    conn, addr = read_socket.accept()
    
    read_counter = 0

    while True:
        data = conn.recv(read_size)
        read_counter += 1
        print("-->received data " + str(read_counter))
        if not data:
            break


def main():
    #Parameters
    read_length = 15 #be sure this aligns with your fastq

    #Files
    if len(sys.argv) == 1:
        fasta = "../test_data/small_ref.fa" 
    else:
        fasta = sys.argv[1]
    fastq = "../test_data/samples.fq"
   
    #Cloud-side operations   
    #TODO: DONT HARDCODE THESE PARAMETERS 
    redis_table = redis.Redis(host='3.95.197.16', port=6379, db=0, password='lean-genes-17')

    #Reference setup
    processed_ref = get_ref(fasta)
    key = get_random_bytes(32)    
    sliding_window_table(key, processed_ref, redis_table, read_length)

    #Wait to process reads from client
    receive_reads(4444, read_length)

if __name__ == "__main__":
    main()


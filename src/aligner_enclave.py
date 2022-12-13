import hashlib
import hmac
import base64
import matplotlib.pyplot as plt
import sys
import time
import re
import redis
import socket
import time

from Crypto.Random import get_random_bytes 
from Crypto.Random import random
from Crypto.Cipher import AES
from reads_pb2 import PMT_Entry 
from vsock_handlers import VsockListener

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

def sliding_window_table(key, ref_lines, redis_table, pmt, read_size=151):

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
            redis_pipe.set(int.from_bytes(curr_hash, 'big'), pmt[hashes_generated]) 
            if batch_counter % batch_size == 0:
                while True:
                    try:
                        redis_response = redis_pipe.execute()
                        break
                    except ConnectionError:
                        print("Redis connection error... Trying again.")
                        sleep(10)

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
    while True:
        try:
            redis_response = redis_pipe.execute()
            break
        except ConnectionRefusedError:
            try:
                print("Redis connection error... Trying again.")
                sleep(10)
            except redis.ConnectionError:
                print("Redis connection error... Trying again.")
                sleep(10)
    print(redis_response)
    
    print("\n*******************************************")
    print(str(hashes_generated) + " hashes generated")
    print(str(lines_processed) + " lines processed") 
    print(str(chrom_counter) + " chromosome(s) processed")
    print("*******************************************")

    return True 

def gen_permutation(ref_length, read_size):
    permutation = [i for i in range(ref_length - read_size + 1)]
    for i in range(len(permutation)-1, 0, -1):
        j = random.randint(0, i+1)
        permutation[i], permutation[j] = permutation[j], permutation[i]
    return permutation

def transfer_pmt(pmt, pmt_port):    
    pmt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_socket.connect(('44.202.235.148', pmt_port)) 
    pmt_entry = PMT_Entry()
    for entry in pmt:
        pmt_entry.pos = bytes(entry)
        #print(len(pmt_entry.SerializeToString()))
        pmt_socket.send(pmt_entry.SerializeToString())
    return pmt_socket

def get_encrypted_reads(vsock_socket):
    while True: 
        vsock_socket.recv(1024)

def main():
    #Genome parameters
    ref_length = 100 #be sure this aligns with your fasta
    read_length = 15 #be sure this aligns with your fastq
    
    #Network parameters
    vsock_port = 5006

    #PMT generation
    print("Generate PMT permutation")
    pmt = gen_permutation(ref_length, read_length)

    #Send PMT
    print("Transferring PMT via proxy...")    
    vsock_socket = transfer_pmt(pmt, vsock_port)
    vsock_socket.close()

    #TODO: This is janky, change this
    time.sleep(30)

    #Reference setup
    if len(sys.argv) == 1:
        fasta = "../test_data/small_ref.fa" 
    else:
        fasta = sys.argv[1]
   
    processed_ref = get_ref(fasta)

    #Cloud-side operations   
    #TODO: DONT HARDCODE THESE PARAMETERS 
    while True:    
        try:
            redis_table = redis.Redis(host='44.202.235.148', port=6379, db=0, password='lean-genes-17',socket_connect_timeout=300)
            break 
        except ConnectionError:
            print("Couldn't connect to redis yet.")
            sleep(10)

    #Crypto key for hashes
    if mode == "DEBUG":
        key = b'0' * 32
    else:
        key = get_random_bytes(32)    

    #Hash ref genome
    sliding_window_table(key, processed_ref, redis_table, pmt, read_length)

    #Run server for receiving encrypted reads
    vsock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vsock_socket.connect(('44.202.235.148', vsock_port)) 
    get_encrypted_reads(vsock_socket)

if __name__ == "__main__":
    main()


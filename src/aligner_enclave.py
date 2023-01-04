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
import os

from aligner_config import global_settings, enclave_settings, genome_params
from Crypto.Random import get_random_bytes 
from Crypto.Random import random
from Crypto.Cipher import AES
from reads_pb2 import Read, PMT_Entry 
from vsock_handlers import VsockListener
from google.protobuf.internal.encoder import _VarintBytes

#Global params to help with debug and test
debug = False
check_locations = False
verify_redis = False
pmt_transfer = False
limit_hashes = False 
hash_limit = 100
limit_lines = False
line_limit = 100
mode = "DEBUG"

#After x hashes print progress
progress_indicator = 5000000

def trigger_bwa_indexing(bwa_path, fasta):
    print("Begin BWA indexing...") 
    os.system(bwa_path + "/bwa index " + fasta + " &")

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
    #print(redis_response)
    
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

def transfer_pmt(pmt, pmt_port, chrom_id=0):    
    pmt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_socket.connect(('3.87.229.175', pmt_port)) 
    pmt_entry = PMT_Entry()
    count_entries = 0
    for entry in pmt:
        #Fill in fields of PMT entry 
        pmt_entry.pos = entry
        if chrom_id != 0:
            pmt_entry.chrom = chrom_id
        #print(len(pmt_entry.SerializeToString()))
        if debug:
            print(entry)
        #Must allow client to properly parse PMT info
        pmt_socket.send(_VarintBytes(pmt_entry.ByteSize()))
        pmt_socket.send(pmt_entry.SerializeToString())
        count_entries += 1
    print(str(count_entries) + " PMT entries processed")
    return pmt_socket

def get_encrypted_reads(vsock_socket, serialized_read_size, batch_size):
    unmatched_fastq = ""
    read_parser = Read()

    anonymized_label = "@unlabeled"

    while True: 
        vsock_socket.listen()
        conn, addr = vsock_socket.accept()

        #TODO: Real crypto key management
        crypto_key = b'0' * 32
        crypto = AES.new(crypto_key, AES.MODE_ECB)
        unmatched_counter = 0

        data = 1 
        while data:
            if debug:
                print("-->received unmatched read from cloud")
        
            unmatched_counter += 1
        
            data = conn.recv(serialized_read_size)
            check_read = read_parser.ParseFromString(data)
            
            unmatched_fastq += (anonymized_label + "\n")
            
            read_size = genome_params["READ_LENGTH"]
            unmatched_fastq += str(crypto.decrypt(read_parser.read)[0:read_size], 'utf-8') + "\n"
            unmatched_fastq += "+\n"
            unmatched_fastq += str(read_parser.align_score) + "\n"

            if unmatched_counter % batch_size == 0:
                #IMMEDIATE TODO!!!
                #WHERE BWA WILL BE CALLED [ os.system()? ]
                print(unmatched_fastq)
                unmatched_fastq = ""

def main():

    ref_length = genome_params["REF_LENGTH"]
    read_length = genome_params["READ_LENGTH"]
    batch_size = genome_params["BATCH_SIZE"]	
    serialized_read_size = genome_params["SERIALIZED_READ_SIZE"]

    #Network parameters
    vsock_port = enclave_settings["vsock_port"]

    print("Generate PMT permutation")
    pmt = gen_permutation(ref_length, read_length)

    #PMT generation
    if pmt_transfer:
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
    while True:    
        try:
            redis_table = redis.Redis(host=global_settings["redis_ip"], port=global_settings["redis_port"], db=0, password='lean-genes-17',socket_connect_timeout=300)
            break 
        except ConnectionError:
            print("Couldn't connect to redis yet.")
            sleep(10)

    #Crypto key for hashes
    if mode == "DEBUG":
        key = b'0' * 32
    else:
        key = get_random_bytes(32)    

    #In background, allow BWA to index FASTA if index file doesn't exist
    bwa_path = enclave_settings["bwa_path"]
    if not global_settings["index_exists"]:
        trigger_bwa_indexing(bwa_path, fasta)

    #Hash ref genome
    sliding_window_table(key, processed_ref, redis_table, pmt, read_length)

    #Run server for receiving encrypted reads
    vsock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vsock_socket.bind(('', vsock_port)) 
    get_encrypted_reads(vsock_socket, serialized_read_size, batch_size)

if __name__ == "__main__":
    main()


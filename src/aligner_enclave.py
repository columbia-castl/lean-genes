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
import numpy as np
import threading

from aligner_config import global_settings, enclave_settings, genome_params, leangenes_params, secret_settings
from subprocess import Popen, PIPE, STDOUT
from Crypto.Random import get_random_bytes 
from Crypto.Random import random
from Crypto.Cipher import AES
from reads_pb2 import Read, Result, PMT_Entry 
from vsock_handlers import VsockListener
from google.protobuf.internal.encoder import _VarintBytes
from enum import Enum

#Global params to help with debug and test
debug = enclave_settings["debug"] 
debug_subprocess = False
check_locations = False
verify_redis = False
pmt_transfer = False
limit_hashes = False 
hash_limit = 100
limit_lines = False
line_limit = 100
mode = "DEBUG"

#After x hashes print progress
progress_indicator = enclave_settings["hashing_progress_indicator"]
pmt = []

class SamState(Enum):
    PROCESSING_HEADER = 1
    PROCESSING_READS = 2

class SamReadFields(Enum):
    qname = 1
    flag = 2
    rname = 3
    pos = 4
    mapq = 5
    cigar = 6
    rnext = 7
    pnext = 8
    tlen = 9
    seq = 10
    qual = 11
    additional = 12

def trigger_bwa_indexing(bwa_path, fasta):
    print("Begin BWA indexing...") 
    os.system(bwa_path + "bwa index " + fasta + " &")

def dispatch_bwa(bwa_path, fasta, fastq):
    print("Passing batched FASTQ to BWA...")
    if debug_subprocess: 
        call_bwa = Popen(["cat"], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    else:
        call_bwa = Popen([bwa_path + "bwa", "mem", fasta, "-"], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    stdout_data = call_bwa.communicate(input=fastq)[0]

    if debug:
        print(str(stdout_data, 'utf-8'))
        print(type(stdout_data))
    print(" ~~~ BWA HAS PROCESSED UNMATCHED READS! ~~~ ")
    return stdout_data

def process_read(protobuffer, read_bytes, crypto):
    global pmt

    if debug:
        print("READ_BYTES")
        print(read_bytes)

    protobuffer.qname = read_bytes[0]
    protobuffer.flag = read_bytes[1]
    protobuffer.rname = read_bytes[2]
    if read_bytes[3] != b'0':
        if debug:
            print("BWA maps read to pos... ")
            print(read_bytes[3].decode())
        protobuffer.pos = bytes(str(pmt[int(read_bytes[3].decode())]), 'utf-8')
    else:
        protobuffer.pos = b'0'
    protobuffer.mapq = read_bytes[4]
    protobuffer.cigar = read_bytes[5]
    protobuffer.rnext = read_bytes[6]
    protobuffer.pnext = read_bytes[7]
    protobuffer.tlen = read_bytes[8]
    while len(read_bytes[9]) % leangenes_params["AES_BLOCK_SIZE"] != 0:
        read_bytes[9] += b'0'
    protobuffer.seq = crypto.encrypt(read_bytes[9])
    protobuffer.qual = read_bytes[10]
    for i in range(11, len(read_bytes)): 
        protobuffer.additional_fields += read_bytes[i]

    if debug:
        print("Read size: " + str(protobuffer.ByteSize()))
    return (_VarintBytes(protobuffer.ByteSize()), protobuffer.SerializeToString())

def sam_sender(sam_data):

    if sam_data == b'':
        return ''

    if debug: 
        print("\tSAM SENDER RECEIVES: ", sam_data)

    new_result = Result()
    sam_lines = sam_data.split(b'\n')
    sep_read = b''

    bwa_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bwa_socket.connect((enclave_settings["server_ip"], enclave_settings["bwa_port"]))

    PARSING_STATE = SamState.PROCESSING_HEADER
    READ_STATE = SamReadFields.qname

    crypto_key = b'0' * 32
    crypto = AES.new(crypto_key, AES.MODE_ECB)

    result_counter = 0
    for line in sam_lines:
        if PARSING_STATE == SamState.PROCESSING_HEADER:
            if line[0] == 64: #ASCII for @
                new_result.sam_header += (line + b'\n')
            else:
                sep_read = line.split(b'\t')
                result_tuple = process_read(new_result, sep_read, crypto)
                bwa_socket.send(result_tuple[0])
                bwa_socket.send(result_tuple[1])
                if debug:    
                    print("BWA SOCK sends result: ", result_tuple[1])
                    print("BWA SOCK sends size: ", result_tuple[0])
                PARSING_STATE = SamState.PROCESSING_READS

                if debug:
                    print("----> Sending result " + str(result_counter) + " back to cloud")
                    print(result_tuple)
                result_counter += 1

        elif PARSING_STATE == SamState.PROCESSING_READS:
            sep_read = line.split(b'\t')
            if (len(sep_read[0]) > 0):
                new_result.sam_header = b''
                result_tuple = process_read(new_result, sep_read, crypto)
                bwa_socket.send(result_tuple[0])
                bwa_socket.send(result_tuple[1])

                if debug:
                    print("----> Sending result " + str(result_counter) + " back to cloud")
                    print(result_tuple)
                result_counter += 1

        else:
            printf("ERROR: Unexpected SAM parsing state")

    bwa_socket.close()

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
            redis_pipe.set(int.from_bytes(curr_hash, 'big'), int(pmt[hashes_generated])) 
            if batch_counter % batch_size == 0:
                while True:
                    try:
                        redis_response = redis_pipe.execute()
                        break
                    except ConnectionError:
                        print("Redis connection error... Trying again.")
                        sleep(10)

                if debug:
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
    print("*******************************************\n")

    return True 

def gen_permutation(ref_length, read_size):
    permutation = [i for i in range(ref_length - read_size + 1)]
    for i in range(len(permutation)-1, 0, -1):
        j = random.randint(0, i+1)
        permutation[i], permutation[j] = permutation[j], permutation[i]
    return permutation

def transfer_pmt(pmt, chrom_id=0):    
    pmt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_socket.connect((enclave_settings["server_ip"], enclave_settings["pmt_port"])) 
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

def get_encrypted_reads(unmatched_socket, serialized_read_size, batch_size, fasta_path):
    unmatched_fastq = ""
    read_parser = Read()

    anonymized_label = "@unlabeled"

    while True: 
        unmatched_socket.listen()
        conn, addr = unmatched_socket.accept()

        #TODO: Real crypto key management
        crypto_key = b'0' * 32
        crypto = AES.new(crypto_key, AES.MODE_ECB)
        unmatched_counter = 0

        print("CONNECTION TO PUBCLOUD ESTABLISHED")

        while True: 
            data = conn.recv(serialized_read_size) 
            
            if debug:
                print("-->received unmatched read from cloud")

            if not data:
                break

            while len(data) < serialized_read_size:
                data += conn.recv(serialized_read_size - len(data))
                if debug: 
                    print("Data now len " + str(len(data)))

            check_read = read_parser.ParseFromString(data)

            unmatched_counter += 1
            unmatched_fastq += (anonymized_label + "\n")

            read_size = genome_params["READ_LENGTH"]
            read_from_cloud = str(crypto.decrypt(read_parser.read)[0:read_size], 'utf-8')
            unmatched_fastq += read_from_cloud + "\n"
            if debug: 
                print("From the cloud we get this read: ",read_from_cloud)
                print("It has len: ", len(read_from_cloud))

            unmatched_fastq += "+\n"
            unmatched_fastq += str(read_parser.align_score) + "\n"

        #FLUSH READS
        if debug:
            print("Perform connection flush, unmatched_counter = " + str(unmatched_counter))
        result_thread = threading.Thread(target=send_back_results, args=(fasta_path, bytes(unmatched_fastq, 'utf-8'),unmatched_counter,)) 
        result_thread.start() 
        unmatched_fastq = ""

        conn.close()    

def send_back_results(fasta_path, fastq_bytes, num_reads):
    #WHERE BWA IS CALLED
    print("<enclave>: --> sending back result batch! [batch size = ", num_reads ,"]")
    if debug: 
        print("FASTQ: ", fastq_bytes)
    returned_sam = dispatch_bwa(enclave_settings["bwa_path"], fasta_path, fastq_bytes)
    if debug: 
        print(returned_sam)
        print("BWA RETURNS ^^")
    sam_sender(returned_sam) 
    

def main():
    global pmt

    ref_length = genome_params["REF_LENGTH"]
    read_length = genome_params["READ_LENGTH"]
    batch_size = leangenes_params["BWA_BATCH_SIZE"]	
    serialized_read_size = genome_params["SERIALIZED_READ_SIZE"]

    #Network parameters
    unmatched_port = enclave_settings["vsock_port"]
    bwa_port = enclave_settings["bwa_port"]

    print("Generate PMT permutation")
    #pmt = gen_permutation(ref_length, read_length)
    pmt = np.random.RandomState(seed=secret_settings["perm_seed"]).permutation(ref_length)
    if debug:    
        print(pmt)
    print("... PMT is generated!")

    #PMT generation
    if pmt_transfer:
        #Send PMT
        print("Transferring PMT via proxy...")    
        unmatched_socket = transfer_pmt(pmt)
        unmatched_socket.close()

        #TODO: This is janky, change this
        time.sleep(30)

    #Reference setup
    if len(sys.argv) == 1:
        fasta = "../test_data/small_ref.fa" 
    else:
        fasta = sys.argv[1]
   

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
    if not enclave_settings["bwa_index_exists"]:
        trigger_bwa_indexing(bwa_path, fasta)

    #Hash ref genome
    if not enclave_settings["separate_hashing"]:
        processed_ref = get_ref(fasta)
        sliding_window_table(key, processed_ref, redis_table, pmt, read_length)

    if not enclave_settings["only_indexing"]:
        #Run server for receiving encrypted reads
        unmatched_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        unmatched_socket.bind(('', unmatched_port)) 
        get_encrypted_reads(unmatched_socket, serialized_read_size, batch_size, fasta)

if __name__ == "__main__":
    main()


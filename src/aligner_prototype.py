import hashlib
import hmac
import base64
import matplotlib.pyplot as plt
import sys
import time
import re

from Crypto.Random import get_random_bytes 
from Crypto.Random import random
from Crypto.Cipher import AES

ref_list = []
ref_loc = []

#Global params to help with debug and test
debug = False
check_locations = True

limit_hashes = True
hash_limit = 100

limit_lines = False
line_limit = 100

def get_ref(ref_file_path):
    print("\nRetrieve reference file at path " + ref_file_path)
    
    ref_file = open(ref_file_path, "r")
    full_ref = ref_file.readlines() 
  
    ref_file.close()
    return full_ref

def sliding_window_table(key, ref_lines, read_size=100, hash_bits=15):

    #Important stat/debug counters
    hashes_generated = 0
    lines_processed = 0
    chrom_counter = 0
   
    #Data structure initialization
    hash_buffer = b''
    hash_table = [[] for _ in range(2**hash_bits)]
    ref_coords = [[] for _ in range(2**hash_bits)]

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
           
            table_index = int.from_bytes(curr_hash, 'big') % (2**hash_bits)
            bucket_index = len(hash_table[table_index]) 
            
            if debug:
                print(curr_hash)
                print("Placing hash in bucket " + str(table_index) + "\n")
           
            hash_table[table_index].append(curr_hash)
            ref_coords[table_index].append(hashes_generated)
            
            hashes_generated += 1
            hash_buffer = hash_buffer[1:]          

            if limit_hashes and (hashes_generated > hash_limit):
                end_hashing = True
                break
        
        lines_processed += 1
        
        if limit_lines and (lines_processed > line_limit):
            break
      
    print("\n*******************************************")
    print(str(hashes_generated) + " hashes generated")
    print(str(lines_processed) + " lines processed") 
    print(str(chrom_counter) + " chromosome(s) processed")
    print("*******************************************")

    return hash_table, ref_coords

def find_reads(key, hash_table, ref_coords, hash_bits, filename):
   
    print("\nProcessing reads from fastq: " + filename)
    read_file = open(filename, "r")
    read_count = 0
    find_count = 0

    while True:
        get_line = read_file.readline()
        if not get_line:
            break
        if re.search("A|C|G|T", get_line) != None:
            read_count += 1
            get_line_bytes = bytes(get_line[:-1], 'utf-8')
            if debug: 
                print(get_line_bytes) 
            
            newhash = hmac.new(key, bytes(get_line[:-1], 'utf-8'), hashlib.sha256) 
            curr_hash = newhash.digest()
            if debug:
                print(curr_hash)
            
            table_index = int.from_bytes(curr_hash, 'big') % (2**hash_bits)
            
            if debug:
                print("Looking in bucket " + str(table_index))
            
            for i in range(len(hash_table[table_index])):
                if hash_table[table_index][i] == curr_hash:
                    if debug: 
                        print("HASH FOUND!")
                    if check_locations:
                        print("Ref loc = " + str(ref_coords[table_index][i]))
                    find_count += 1
                    ref_loc.append(ref_coords[table_index][i])                    
                    break
    print(str(read_count) + " reads processed.")
    print(str(find_count) + "/" + str(read_count) + " READS ALIGNED")
    print(str((float(find_count)/float(read_count)) * 100) + "% of READS ALIGNED\n")

def get_bucket_lens(hash_table, hash_bits):
    bucket_lens = []
    for i in range(2**hash_bits):
        bucket_lens.append(len(hash_table[i]))
    return bucket_lens

def bucket_time_tests(num_trials, hash_table, hash_bits=15):
    time_vector = []
    indices = []

    for i in range(num_trials):
        bucket = random.randint(0, 2**hash_bits-1)
        index = random.randint(0, len(hash_table[bucket])-1)
        rand_hash = hash_table[bucket][index]
        found = False
        ind = 0

        time1 = time.time()
        while not found:
            if hash_table[bucket][ind] != rand_hash:
                ind += 1
            else:
                found = True
            if ind > len(hash_table[bucket]):
                print("Error: didn't find hash sampled from bucket?!?")
        time2 = time.time()
        time_vector.append(time2-time1)
        indices.append(index)
    return indices, time_vector

def make_plots(hash_table, hash_bits, num_samples):
  
    bucket_lens = get_bucket_lens(hash_table, hash_bits)
    
    plt.plot(bucket_lens)
    plt.title("Bucket distribution with " + str(2**hash_bits) + " buckets")
    plt.xlabel("Bucket index")
    plt.ylabel("Hashes in bucket")
    plt.grid()
    plt.savefig("bucket_data/buckets_" + str(2**hash_bits) + ".png")

    indices, times = bucket_time_tests(num_samples, hash_table, hash_bits)
    print(times)

    plt.clf()
    plt.plot(indices, times)
    plt.title("Hash access times given a hash table")
    plt.xlabel("Index")
    plt.ylabel("Time (s)")
    plt.grid()
    plt.savefig("bucket_data/access_times.png")

def main():
    #Timing samples
    num_samples = 200

    #Parameters
    hash_bits = 15
    read_length = 151 #be sure this aligns with your fastq

    #Files
    fasta = "../test_data/chr21.fa" 
    fastq = "../test_data/samples.fq"
   
    #Cloud-side operations   
    processed_ref = get_ref(fasta)
    
    key = get_random_bytes(32)    
    hash_table, ref_coords = sliding_window_table(key, processed_ref, read_length ,hash_bits)

    #Process reads from client side    
    #find_reads(key, hash_table, ref_coords, hash_bits, fastq)  
    
    #Performance measurements
    #make_plots(hash_table, hash_bits, num_samples)

if __name__ == "__main__":
    main()


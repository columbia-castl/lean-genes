import hashlib
import hmac
import sys
import re

from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES

debug = False

def send_reads(key, filename="../test_data/samples.fq"):
   
    print("\nProcessing reads from fastq: " + filename)
    read_file = open(filename, "r")
    read_count = 0
    find_count = 0

    ref_loc = []

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
            
    print(str(read_count) + " reads processed.")

    return ref_loc

def main():
    
    key = get_random_bytes(32)
    print("...")
    send_reads(key)

if __name__ == "__main__":
    main()

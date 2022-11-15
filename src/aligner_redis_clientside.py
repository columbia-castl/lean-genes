import hashlib
import hmac
import sys
import re
import socket

from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from enum import Enum
from reads_pb2 import Read

debug = False

class FastqState(Enum):
    READ_LABEL = 1
    READ_CONTENT = 2
    DIV = 3
    READ_QUALITY = 4

PARSING_STATE = FastqState.READ_LABEL

read_string = ""

def send_reads(key, filename="../test_data/samples.fq"):
    global PARSING_STATE

    print("\nProcessing reads from fastq: " + filename)
    read_file = open(filename, "r")
    read_count = 0
    find_count = 0

    ref_loc = []

    while True:
        get_line = read_file.readline()
        
        if not get_line:
            break

        if PARSING_STATE == FastqState.READ_LABEL:
            if get_line[0] != "@":
                printf("Error: Fastq is not formatted correctly.")
                exit(1)
            else:
                PARSING_STATE = FastqState.READ_CONTENT

        elif PARSING_STATE == FastqState.READ_CONTENT:

            if re.search("A|C|G|T", get_line) != None:
                #newread = reads_pb2.Read()

                read_count += 1
                get_line_bytes = bytes(get_line[:-1], 'utf-8')
                read_string = get_line

                if debug: 
                    print(get_line_bytes) 
                
                newhash = hmac.new(key, bytes(get_line[:-1], 'utf-8'), hashlib.sha256) 
                curr_hash = newhash.digest()
                
                if debug:
                    print(curr_hash)

                PARSING_STATE = FastqState.DIV

            else:
                printf("Error: fastq is not formatted correctly.")
                exit(1)

        elif PARSING_STATE == FastqState.DIV:
            if (get_line[0] != "+") or (len(get_line) > 2):
                printf("Error: fastq is not formatted correctly.")
                exit(1)
            else:
                PARSING_STATE = FastqState.READ_QUALITY

        elif PARSING_STATE == FastqState.READ_QUALITY:
            if (len(get_line) != len(read_string)):
                printf("Error: fastq is not formatted correctly.")

            else:
                PARSING_STATE = FastqState.READ_LABEL

        else:
            printf("Error: bad fastq parsing state!")
            exit(1)
    print(str(read_count) + " reads processed.")

    return ref_loc

def main():
    
    key = get_random_bytes(32)
    print("...")
    send_reads(key)

if __name__ == "__main__":
    main()

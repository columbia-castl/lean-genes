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

cipher_object = ""
read_string = ""
read_socket = ""

def send_reads(socket, encrypter, hashkey, filename="../test_data/samples.fq"):
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
            newread = Read()
            if re.search("A|C|G|T", get_line) != None:
                read_count += 1
                get_line_bytes = bytes(get_line[:-1], 'utf-8')
                read_string = get_line

                if debug: 
                    print(get_line_bytes) 
                
                newhash = hmac.new(hashkey, bytes(get_line[:-1], 'utf-8'), hashlib.sha256) 
                curr_hash = newhash.digest()
                
                if debug:
                    print(curr_hash)
            
                newread.read = encrypter.encrypt(bytes(get_line[:-1], 'utf-8'))
                newread.hash = curr_hash

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
                newread.align_score = encrypter.encrypt(bytes(get_line[:-1], 'utf-8'))
                serialized_read = newread.SerializeToString()
                socket.send(serialized_read)
                PARSING_STATE = FastqState.READ_LABEL

        else:
            printf("Error: bad fastq parsing state!")
            exit(1)

    print(str(read_count) + " reads processed.")

    return ref_loc

def main():
   
    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    read_socket.connect(('127.0.0.1', 4444))

    hashkey = get_random_bytes(32)
    cipherkey = get_random_bytes(32)
    cipher_object = AES.new(cipherkey, AES.MODE_CTR) 

    print("Parsing fastq...")
    send_reads(read_socket, cipher_object, hashkey)

if __name__ == "__main__":
    main()

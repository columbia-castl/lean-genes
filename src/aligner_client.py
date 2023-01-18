import hashlib
import hmac
import sys
import re
import socket
import os
import array
import threading

from aligner_config import global_settings, client_settings, genome_params, leangenes_params
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Util import Counter
from enum import Enum
from reads_pb2 import Read, PMT_Entry, Result
from google.protobuf.internal.decoder import _DecodeVarint32
from _thread import *

debug = False
mode = "DEBUG"
AES_BLOCK_SIZE = 16
result_socket = ""

class FastqState(Enum):
    READ_LABEL = 1
    READ_CONTENT = 2
    DIV = 3
    READ_QUALITY = 4

PARSING_STATE = FastqState.READ_LABEL

cipher_object = ""
read_string = ""
read_socket = ""

client_commands = ['help','get_pmt', 'send_reads', 'stop']

def receive_pmt(pmt_socket):
    pmt = []
    recv_block_size = 1024
    pmt_socket.send("Start".encode())

    #https://www.datadoghq.com/blog/engineering/protobuf-parsing-in-python/
    while True:
        data = pmt_socket.recv(recv_block_size)
        while data:
            msg_len, size_len = _DecodeVarint32(data, 0)

            while (size_len + msg_len > len(data)):
                data += pmt_socket.recv(recv_block_size)
            msg_buf = data[size_len: msg_len + size_len]

            new_entry = PMT_Entry()
            check_entry = new_entry.ParseFromString(msg_buf)
            if debug: 
                print(str(new_entry.pos) + " is PMT entry")

            pmt.append(new_entry.pos)
            data = data[msg_len+size_len:]

        if not data:
            break

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
                print("Error: Fastq is not formatted correctly.")
                exit()
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
                
                newhash = hmac.new(hashkey, get_line_bytes, hashlib.sha256) 
                curr_hash = newhash.digest()
                
                if debug:
                    print(curr_hash)

                #padding
                while len(get_line_bytes) % AES_BLOCK_SIZE != 0:
                    get_line_bytes += b'0'
                newread.read = encrypter.encrypt(get_line_bytes)
                newread.hash = curr_hash

                PARSING_STATE = FastqState.DIV

            else:
                printf("Error: fastq is not formatted correctly.")
                exit()

        elif PARSING_STATE == FastqState.DIV:
            if (get_line[0] != "+") or (len(get_line) > 2):
                printf("Error: fastq is not formatted correctly.")
                exit()
            else:
                PARSING_STATE = FastqState.READ_QUALITY

        elif PARSING_STATE == FastqState.READ_QUALITY:
            if (len(get_line) != len(read_string)):
                printf("Error: fastq is not formatted correctly.")

            else:
                qual_bytes = bytes(get_line[:-1], 'utf-8')
                qual_string = get_line[:-1]
                while len(qual_bytes) % leangenes_params["AES_BLOCK_SIZE"] != 0:
                    qual_bytes += b'0'

                #TODO: proper handling of quality encryption
                #newread.align_score = encrypter.encrypt(qual_bytes)
                newread.align_score = qual_string
                #print(qual_string)

                serialized_read = newread.SerializeToString()
                #print("Serialized read size: " + str(len(serialized_read)))
                socket.send(serialized_read)
                PARSING_STATE = FastqState.READ_LABEL

        else:
            printf("Error: bad fastq parsing state!")
            exit()

    crypto_key = b'0' * 32
    crypto = AES.new(crypto_key, AES.MODE_ECB)

    print(str(read_count) + " reads processed.")
    print("\t-->Initiate result processing thread") 
    #processing_thread = start_new_thread(process_alignment_results, (read_count,crypto,))
    
    #This is a change for NON-INTERACTIVE mode of the client
    t1 = threading.Thread(target=process_alignment_results, args=(read_count, crypto, filename + ".sam",))
    t1.start()
    #t1.join()

    return ref_loc


def receive_pmt_wrapper(server_ip, pmt_port):
    pmt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_socket.connect((server_ip, pmt_port))
    receive_pmt(pmt_socket)

def send_read_wrapper(server_ip, read_port, filename): 
    if mode == "DEBUG":
        hashkey = b'0' * 32
        cipherkey = b'0' * 32
    else:
        hashkey = get_random_bytes(32)
        cipherkey = get_random_bytes(32)
   
    #Implement *our* CTR mode on top of this, PyCrypto's encapsulation is super inconvenient
    crypto = AES.new(cipherkey, AES.MODE_ECB) 

    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    read_socket.connect((server_ip, read_port))

    print("Parsing fastq...")
    send_reads(read_socket, crypto, hashkey, filename)

def unpack_read(next_result, crypto):
    sam = b''
    sam += (next_result.qname + b"\t")
    sam += (next_result.flag + b"\t")
    sam += (next_result.rname + b"\t")
    sam += (next_result.pos + b"\t")
    sam += (next_result.mapq + b"\t")
    sam += (next_result.cigar + b"\t")
    sam += (next_result.rnext + b"\t")
    sam += (next_result.pnext + b"\t")
    sam += (next_result.tlen + b"\t")
    sam += (crypto.decrypt(next_result.seq)[:genome_params["READ_LENGTH"]] + b"\t")
    sam += (bytes(next_result.qual, 'utf-8') + b"\n")

    return sam

def process_alignment_results(num_reads, crypto, savefile): 
    global result_socket

    print("Result socket waiting...")

    #Wait for results
    result_socket.listen(5)
    conn, addr = result_socket.accept()
    print("Processing thread receives connection!")

    num_reads_processed = 0
    sam = b""

    while num_reads_processed < num_reads:
        data = conn.recv(1024) 
        while data:
            msg_len, size_len = _DecodeVarint32(data, 0)

            if debug:
                print("--------Size:")
                print(msg_len)

            if (msg_len + size_len > len(data)):
                data += conn.recv(1024)
                continue

            result = data[size_len: size_len + msg_len]
            if debug: 
                print("-------Result:")
                print(result)
            
            next_result = Result()
            check_result = next_result.ParseFromString(result)
        
            add_to_sam = unpack_read(next_result, crypto)
            if debug: 
                print("BYTES")
                print(add_to_sam) 
                print("STR")
                print(str(add_to_sam, 'utf-8'))           

            num_reads_processed += 1
            if debug: 
                print(str(num_reads_processed) + " reads processed")

            sam += add_to_sam
            data = data[size_len + msg_len:]
        #data = conn.recv(1024)
    
    print(str(num_reads_processed) + " reads processed")
    print("SAVING SAM FILE @ " + savefile) 
    #print(sam)
    conn.close()
    result_socket.close()

    file = open(savefile, 'wb')
    file.write(sam)

def main():
    global result_socket

    server_ip = client_settings["server_ip"]
    pmt_port = client_settings["pmt_port"]
    read_port = client_settings["read_port"]
    result_port = client_settings["result_port"]

    result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_socket.bind(('', result_port))

    print("Client initialized")
    if len(sys.argv) > 1:
        readfile = sys.argv[1]
        send_read_wrapper(server_ip, read_port, readfile)
    else:
        command_str = ""
        while True:
            command_str = input("Input command: ")
            if command_str not in client_commands:
                print("Please enter a valid command. See available commands with 'help'")
            elif command_str == "help":
                print("Available commands are: ")
                for command in client_commands:
                    print("\t" + command)
            elif command_str == "get_pmt":
                receive_pmt_wrapper(server_ip, pmt_port)
            elif command_str == "send_reads":
                readfile = input("\tEnter path to fastq: ")
                send_read_wrapper(server_ip, read_port, readfile)
            elif command_str == "stop":
                break
            else:
                print("CLIENT ERROR. PLEASE RESTART.")

    print("Exiting client.")
    #result_socket.close()

if __name__ == "__main__":
    main()

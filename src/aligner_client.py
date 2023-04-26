import hashlib
import hmac
import sys
import re
import socket
import os
import time
import array
import threading
import numpy as np

from aligner_config import global_settings, client_settings, genome_params, leangenes_params, secret_settings
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Util import Counter
from enum import Enum
from reads_pb2 import Read, PMT_Entry, Result, BatchID
from google.protobuf.internal.decoder import _DecodeVarint32
from multiprocessing import pool 

debug = client_settings["debug"]
result_socket = ""
pmt = []

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

done_sending = False
done_with_exact = leangenes_params["disable_exact_matching"]
done_with_bwa = False

reads_sent = 0

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

def send_reads(encrypter, hashkey, filename="../test_data/samples.fq"):
    global PARSING_STATE, reads_sent, done_sending

    print("\n<read sender>: Processing reads from fastq: " + filename)
    
    begin_time = time.time()

    read_file = open(filename, "r")
    reads_sent = 0

    serialized_batch = b""
    batch_counter = 0

    crypto_key = b'0' * 32
    crypto = AES.new(crypto_key, AES.MODE_ECB)

    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    read_socket.connect((client_settings["server_ip"], client_settings["read_port"]))

    while True:
        get_line = read_file.readline()
        
        if not get_line:
            break

        if PARSING_STATE == FastqState.READ_LABEL:
            if get_line[0] != "@":
                print("<read sender>: Error: fastq is not formatted correctly.")
                exit()
            else:
                PARSING_STATE = FastqState.READ_CONTENT

        elif PARSING_STATE == FastqState.READ_CONTENT:
            newread = Read()
            if re.search("A|C|G|T", get_line) != None:
                reads_sent += 1
                get_line_bytes = bytes(get_line[:-1], 'utf-8')
                read_string = get_line

                if debug: 
                    print(get_line_bytes) 
                
                newhash = hmac.new(hashkey, get_line_bytes, hashlib.sha256) 
                curr_hash = newhash.digest()
                
                if debug:
                    print(curr_hash)

                #padding
                while len(get_line_bytes) % leangenes_params["AES_BLOCK_SIZE"] != 0:
                    get_line_bytes += b'0'
                newread.read = encrypter.encrypt(get_line_bytes)
                newread.hash = curr_hash
                
                PARSING_STATE = FastqState.DIV

            else:
                print("<read sender>: Error: fastq is not formatted correctly.")
                exit()

        elif PARSING_STATE == FastqState.DIV:
            if (get_line[0] != "+") or (len(get_line) > 2):
                print("<read sender>: Error: fastq is not formatted correctly.")
                exit()
            else:
                PARSING_STATE = FastqState.READ_QUALITY

        elif PARSING_STATE == FastqState.READ_QUALITY:
            if (len(get_line) != len(read_string)):
                print("<read sender>: Error: fastq is not formatted correctly.")
            
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
                #read_socket.send(serialized_read) 
                serialized_batch += serialized_read
                batch_counter += 1

                if debug:
                    print("Serialized read size: " + str(len(serialized_read)))
                    print(serialized_read) 

                if batch_counter % leangenes_params["READ_BATCH_SIZE"] == 0:
                    print("<read sender>: -->Batch size reached. Sending to cloud.")
                     
                    #read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    #read_socket.connect((client_settings["server_ip"], client_settings["read_port"]))
                    read_socket.send(serialized_batch)
                    #read_socket.close()
                    
                    batch_counter = 0
                    serialized_batch = b""
                
                PARSING_STATE = FastqState.READ_LABEL

        else:
            print("<read sender>: " + "Error: bad fastq parsing state!")
            exit()

    if batch_counter:
        print("<read sender>: " + "-->Send final batch to cloud.")
        read_socket.send(serialized_batch)
        serialized_batch = b""

    done_sending = True

    end_time = time.time()

    print("<read sender>: " + str(reads_sent) + " reads processed in ", end_time - begin_time, " seconds")
    print("<read sender>: CLIENT HAS FINISHED SENDING READS\n")

def receive_pmt_wrapper():
    pmt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_socket.connect((client_settings["server_ip"], client_settings["pmt_port"]))
    receive_pmt(pmt_socket)

def send_read_wrapper(filename): 
    if leangenes_params["CRYPTO_MODE"] == "debug":
        hashkey = b'0' * 32
        cipherkey = b'0' * 32
    else:
        hashkey = get_random_bytes(32)
        cipherkey = get_random_bytes(32)
   
    #Implement *our* CTR mode on top of this, PyCrypto's encapsulation is super inconvenient
    crypto = AES.new(cipherkey, AES.MODE_ECB) 
    print("*********************************")
    print("* RESULTS THREAD POOL INITIATED *")
    print("*********************************")
    #result_manager = threading.Thread(target=track_reads_received, args=(crypto, filename+".sam",))
    result_manager = threading.Thread(target=spawn_results_processes, args=(crypto, filename+".sam")) 
    result_manager.start()

    print("*************************")
    print("* READ SENDER INITIATED *")
    print("*************************")
    read_sender = threading.Thread(target=send_reads, args=(crypto, hashkey, filename,))
    read_sender.start()

def unpack_read(next_result, crypto):
    global pmt

    sam = b''
    header = b''

    if next_result.sam_header != b'':
        header = (next_result.sam_header)
    sam += (next_result.qname + b"\t")
    sam += (next_result.flag + b"\t")
    sam += (next_result.rname + b"\t")
    if debug:
        print(np.where(pmt == int(next_result.pos))[0][0])
    if next_result.pos != b'0':
        sam += (str(np.where(pmt == int(next_result.pos))[0][0]).encode()  + b"\t")
    else:
        sam += (b'0' + b'\t')
    sam += (next_result.mapq + b"\t")
    sam += (next_result.cigar + b"\t")
    sam += (next_result.rnext + b"\t")
    sam += (next_result.pnext + b"\t")
    sam += (next_result.tlen + b"\t")
    sam += (crypto.decrypt(next_result.seq)[:genome_params["READ_LENGTH"]] + b"\t")
    sam += (bytes(next_result.qual, 'utf-8') + b"\n")

    return (sam, header)

def receive_and_process_results_thread(crypto, savefile, thread_id): 
    global result_socket

    print("<results>: Thread " + str(thread_id) + " -- " + "Result socket waiting...")

    num_reads_processed = 0
    sam = b""
    first_thread_header = False

    #while num_reads_processed < num_reads:
    #Wait for results
    result_socket.listen()
    conn, addr = result_socket.accept()
    print("<results>: Processing thread " + str(thread_id)  + " receives connection!")

    data = b''

    while True:
        begin_len = len(data)
        data = conn.recv(1000000) 
        end_len = len(data)

        if end_len == begin_len:
            break

    while data:
        msg_len, size_len = _DecodeVarint32(data, 0)

        if debug:
            print("--------Size:")
            print(msg_len)

        result = data[size_len: size_len + msg_len]
        
        if debug: 
            print("-------Result:")
            print(result)
        
        next_result = Result()
        check_result = next_result.ParseFromString(result)
    
        add_to_sam, header = unpack_read(next_result, crypto)
        
        if debug: 
            print("BYTES")
            print(add_to_sam) 
            print("STR")
            print(str(add_to_sam, 'utf-8'))           

        num_reads_processed += 1
        if debug: 
            print("<results>: Thread " + str(thread_id) + " -- " + str(num_reads_processed) + " reads processed so far")

        sam += add_to_sam
        if thread_id == 0 and (not first_thread_header):
            sam = header + sam
            first_thread_header = True

        data = data[size_len + msg_len:]

    conn.close()

    print("<results>: Thread " + str(thread_id) + " -- " + str(num_reads_processed) + " reads processed")
    print("<results>: Thread " + str(thread_id) + " -- " + "SAVING SAM RESULTS IN " + savefile + "_" + str(thread_id)) 
    
    file = open(savefile + "_" + str(thread_id), 'wb')
    file.write(sam)
    file.close()

    return num_reads_processed


def receive_and_process_results(crypto, savefile, thread_id, conn): 
    print("<results>: Thread " + str(thread_id) + " -- " + "Result socket waiting...")

    num_reads_processed = 0
    first_thread_header = False

    sam = b""
    data = b''
     
    while True:
        begin_len = len(data)
        data = conn.recv(1000000)
        end_len = len(data)

        if (end_len == begin_len) and (data != b''):
            break
        else:
            print("The socket hasn't received any data...")

    while data:
        msg_len, size_len = _DecodeVarint32(data, 0)

        if debug:
            print("--------Size:")
            print(msg_len)

        result = data[size_len: size_len + msg_len]
        
        if debug: 
            print("-------Result:")
            print(result)
        
        next_result = Result()
        check_result = next_result.ParseFromString(result)
    
        add_to_sam, header = unpack_read(next_result, crypto)
        if debug: 
            print("BYTES")
            print(add_to_sam) 
            print("STR")
            print(str(add_to_sam, 'utf-8'))           

        num_reads_processed += 1
        if debug: 
            print("<results>: Thread " + str(thread_id) + " -- " + str(num_reads_processed) + " reads processed so far")

        sam += add_to_sam
        if (not first_thread_header) and (thread_id == 0):
            sam = header + sam
            first_thread_header = True

        data = data[size_len + msg_len:]

    conn.close()

    print("<results>: Thread " + str(thread_id) + " -- " + str(num_reads_processed) + " reads processed")
    print("<results>: Thread " + str(thread_id) + " -- " + "SAVING SAM RESULTS IN " + savefile + "_" + str(thread_id)) 
    
    file = open(savefile + "_" + str(thread_id), 'wb')
    file.write(sam)
    file.close()

    return num_reads_processed

def process_results(crypto, savefile, thread_id, result_data): 
    print("<results>: Thread " + str(thread_id) + " processes results")

    begin_time = time.time()
    
    num_reads_processed = 0
    first_thread_header = False

    sam = b""
     
    while result_data:
        msg_len, size_len = _DecodeVarint32(result_data, 0)

        if debug:
            print("--------Size:")
            print(msg_len)

        result = result_data[size_len: size_len + msg_len]
        
        if debug: 
            print("-------Result:")
            print(result)
        
        next_result = Result()
        check_result = next_result.ParseFromString(result)
    
        add_to_sam, header = unpack_read(next_result, crypto)
        if debug: 
            print("BYTES")
            print(add_to_sam) 
            print("STR")
            print(str(add_to_sam, 'utf-8'))           

        num_reads_processed += 1
        if debug: 
            print("<results>: Thread " + str(thread_id) + " -- " + str(num_reads_processed) + " reads processed so far")

        sam += add_to_sam
        if (not first_thread_header) and (thread_id == 0):
            sam = header + sam
            first_thread_header = True

        result_data = result_data[size_len + msg_len:]

    end_time = time.time()

    print("<results>: Thread " + str(thread_id) + " -- " + str(num_reads_processed) + " reads processed in ", (end_time - begin_time), " seconds.")
    print("<results>: Thread " + str(thread_id) + " -- " + "SAVING SAM RESULTS IN " + savefile + "_" + str(thread_id)) 
    
    file = open(savefile + "_" + str(thread_id), 'wb')
    file.write(sam)
    file.close()

    return num_reads_processed


#This approach used w threads (as opposed to processes)
def track_reads_received(crypto, savefile):
    global reads_sent, done_sending
    threads_available = client_settings["results_threads"]
    thread_counter = 0
    reads_received = 0

    result_pool = pool.ThreadPool(processes=client_settings["results_threads"])
    
    #NOTE:  This is more concise, but iterating through 'result_counts' will block if ANY thread isn't finished
    #       We would like to dynamically check threads then kill the pool when all results are received
    #thread_args = [(crypto, savefile, i) for i in range(client_settings["results_threads"])]
    #result_counts = result_pool.starmap_async(receive_and_process_results_thread, thread_args)

    separable_results = [] 
    for i in range(client_settings["results_threads"]):
        result_count = result_pool.apply_async(receive_and_process_results_thread, args=(crypto, savefile, thread_counter))
        separable_results.append(result_count) 
        thread_counter += 1
    
    while not done_sending:
        pass

    for result_count in separable_results:
        reads_received += result_count.get()
        if reads_received >= reads_sent:
            break

    print("Client has received " + str(reads_received) + " reads")
    result_pool.close()
    print("Result threads pool shut down successfully")

def spawn_results_processes(crypto, savefile):
    global result_socket, done_with_bwa, done_with_exact
    result_socket.listen()

    batches = 0
    last_bwa_batch = 0
    last_lg_batch = 0
    bwa_set = False
    lg_set = False

    processes = []

    while True:

        sam_file = open('lg_out_' + str(batches) + ".sam", 'wb')
        read_file = open('enclave_' + str(batches) + '.bytes', 'wb')
    
        batches +=1

        print("<results>: Wait to accept another process")
        conn, addr = result_socket.accept()
        print("<results>: Client receives connection. Spawn result processor")
        
        size_bytes = conn.recv(10)
        size, ids = _DecodeVarint32(size_bytes, 0)
        
        if debug:
            print("size:", size)
            print("ids:", ids)
            print("len(size bytes):", len(size_bytes))
           
        batch_bytes = b''
        result_data = b''

        if (size > len(size_bytes[ids:])):
            batch_bytes = size_bytes[ids:] + conn.recv(size - len(size_bytes[ids:]))
        else:
            batch_bytes = size_bytes[ids:ids+size]
            result_data += size_bytes[ids+size:]

        while len(batch_bytes) < size:
            batch_bytes += conn.recv(size - len(batch_bytes))

        batch_id = BatchID()
        check_id = batch_id.ParseFromString(batch_bytes)
        print("This batch was able to check its id")

        print("Batch #", batch_id.num)
        print("Batch ID Type: ", batch_id.type)
        print("|Encrypted Bytes|: ", len(batch_id.encrypted_seqs))
        if batch_id.type == 1:
            print("<results>: Last BWA batch num indicated")
            last_bwa_batch = batch_id.num
            bwa_set = True 
        elif batch_id.type == 2: 
            print("<results>: Last LG batch num indicated")
            last_lg_batch = batch_id.num 
            lg_set = True

        begin_time = time.time()
        while True:
            begin_len = len(result_data) 
            result_data += conn.recv(1000000)
            end_len = len(result_data)

            if end_len == begin_len:
                break

        receive_data_time = time.time()
        print("All data for batch received in ", receive_data_time - begin_time, " seconds")
        read_file.write(batch_id.encrypted_seqs)
        
        if debug:
            print(result_data)
        
        sam_file.write(result_data)
        write_file_time = time.time()
        print("Data received + written in ", write_file_time - begin_time, " seconds")
        
        sam_file.close() 
        read_file.close()

        if leangenes_params["disable_exact_matching"]:
            if bwa_set and (batches > last_bwa_batch):
                print("<results>: Client done accepting results!")
                result_socket.close() 
                dispatch_post_proc()
                break
        else:
            if bwa_set and lg_set:
                if batches > max(last_bwa_batch, last_lg_batch):
                    print("<results>: Client done accepting results!")
                    result_socket.close() 
                    dispatch_post_proc()
                    break


#            pid = os.fork()
#            if not pid:
#                process_results(crypto, savefile, thread_counter, result_data)
#                receive_and_process_results(crypto, savefile, thread_counter, conn)
#                exit()
#            else:
#                thread_counter += 1
#                processes.append(pid)
#                print(len(processes), " processes")

    #code-maven.com/python-fork-and-wait
#    while processes:
#        print("Waiting for ", len(processes), " processes")
#       pid, exit_code = os.wait()
#       if pid == 0:
#           time.sleep(1)
#       else:
#           processes.remove(pid)

def write_ipmt():
    global pmt

    begin_time = time.time()

    ipmt = [0 for i in range(len(pmt))]
    for i in range(len(pmt)):
        ipmt[pmt[i]] = i

    print("Write iPMT to file....")
    ipmt_file = open('ipmt.csv','w')
    ipmt_file.write(str(len(ipmt)) + ":")
    for entry in ipmt[:-1]:
        ipmt_file.write(str(entry) + ",")
    ipmt_file.write(str(ipmt[-1]) + "\n")
    ipmt_file.close()

    end_time = time.time()
    print("iPMT generated and written in ", end_time - begin_time, " seconds")

def dispatch_post_proc():
    begin_time = time.time()
    os.system("./post_process.sh")
    end_time = time.time()
    print("Post-processor executed in", end_time - begin_time, " seconds")

def main():
    global result_socket, pmt

    result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_socket.bind(('', client_settings["result_port"]))

    begin_time = time.time()
    pmt = np.random.RandomState(seed=secret_settings["perm_seed"]).permutation(genome_params["REF_LENGTH"])
    end_time = time.time()
    print("PMT permutation generated in ", end_time - begin_time, "seconds.")

    if debug:
        print("PMT")
        print(pmt)

    if client_settings["write_ipmt"]:
        write_ipmt()
        exit()

    print("Client initialized")
    if len(sys.argv) > 1:
        readfile = sys.argv[1] 
        send_read_wrapper(readfile)
    
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
                receive_pmt_wrapper()
            elif command_str == "send_reads":
                readfile = input("\tEnter path to fastq: ")
                send_read_wrapper(readfile)
            elif command_str == "stop":
                break
            else:
                print("CLIENT ERROR. PLEASE RESTART.")

    return

if __name__ == "__main__":
    main()

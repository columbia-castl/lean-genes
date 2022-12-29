import sys
import redis
import socket
import os

from reads_pb2 import Read, PMT_Entry
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from vsock_handlers import VsockStream

debug = False
mode = "DEBUG"

do_pmt_proxy = False

unmatched_threshold = 0

def client_handler(args): 
    client = VsockStream() 
    endpoint = (args.cid, args.port) 
    client.connect(endpoint) 
    msg = 'Hello, world!' 
    client.send_data(msg.encode()) 
    client.disconnect() 
 
def run_redis_server():
    os.system("redis-server aligner_redis.conf &")

def pmt_proxy(proxy_port, pmt_client_port):
    pmt_entry_block = 1000

    print("Waiting for enclave to send PMT...")
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(('', proxy_port))

    pmt_data = []
    proxy_socket.listen()
    proxy_conn, addr = proxy_socket.accept()

    while True:
        data = proxy_conn.recv(pmt_entry_block)
        pmt_data.append(data)
        if not data:
            break

    print("Waiting to send PMT to client...")
    pmt_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pmt_client_socket.bind(('', pmt_client_port))
    pmt_client_socket.listen()
    conn, addr = pmt_client_socket.accept()

    begin_transfer = False
    while not begin_transfer:
        data = conn.recv(pmt_entry_block)
        if data.decode() == "Start":
            begin_transfer = True

    for entry in pmt_data:
        conn.send(entry)

    pmt_client_socket.close()
    return proxy_socket

def receive_reads(client_port, unmatched_socket, unmatched_port, serialized_read_size, crypto, redis_table):

    read_parser = Read()

    #Use read size to calc expected bytes for a read
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_socket.settimeout(30)
    client_socket.bind(('', client_port))
    read_counter = 0

    exact_read_counter = 0
    unmatched_read_counter = 0
    unmatched_reads = []

    while True:
        client_socket.listen()
        conn, addr = client_socket.accept()
        
        while True:
            data = conn.recv(serialized_read_size)
            read_counter += 1

            if debug:
                print("-->received data " + str(read_counter))
            
            check_read = read_parser.ParseFromString(data)

	        #Cloud can only see reads in debug mode
            if debug:
                decrypted_data = crypto.decrypt(read_parser.read)

	        #Sanity check, avoid looking in db for connection-ending/malformed msgs
            if len(read_parser.hash) > 0:
                read_found = redis_table.get(int.from_bytes(read_parser.hash, 'big'))
                if read_found != None:
                    print("Exact match read found.")
                    exact_read_counter += 1
                else:
                    print("Read was not exact match.")
                    unmatched_read_counter += 1
                    unmatched_reads.append(data)                

            if len(unmatched_reads) > unmatched_threshold: 
                if unmatched_read_counter == unmatched_threshold + 1: 
                    unmatched_socket.connect(('3.87.229.175', unmatched_port)) 
                for read in unmatched_reads:
                    unmatched_socket.send(read)
                unmatched_reads.clear()

            if debug:
                print("Data: ")
                print(decrypted_data)
                print("Hash: ")
                print(read_parser.hash)
            
            if not data:
                break

    unmatched_socket.send(unmatched_reads)
    unmatched_reads.clear()

def main():
    #TODO: This shouldn't have to be defined here like this...
    serialized_read_size = 70

    #Network params
    read_port = 4444
    pmt_client_port = 4445
    vsock_port = 5006
    redis_port = 6379

    if mode == "DEBUG":
        cipherkey = b'0' * 32
    else:
        cipherkey = get_random_bytes(32)

    crypto = AES.new(cipherkey, AES.MODE_ECB) 

    if do_pmt_proxy: 
        proxy_socket = pmt_proxy(vsock_port, pmt_client_port)
    else:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    run_redis_server()

    redis_table = redis.Redis(host='3.87.229.175', port=redis_port, db=0, password='lean-genes-17')
    receive_reads(read_port, proxy_socket, vsock_port, serialized_read_size, crypto, redis_table)

if __name__ == "__main__":
    main()

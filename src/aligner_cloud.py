import sys
import redis
import socket
import os

from reads_pb2 import Read
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

debug = False
mode = "DEBUG"

def run_redis_server():
    os.system("redis-server aligner_redis.conf &")

def receive_reads(read_port, serialized_read_size, crypto, redis_table):

    read_parser = Read()

    #Use read size to calc expected bytes for a read
    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #read_socket.settimeout(30)
    read_socket.bind(('127.0.0.1', read_port))
    read_counter = 0

    found_reads = 0

    while True:
        read_socket.listen()
        conn, addr = read_socket.accept()
        
        while True:
            data = conn.recv(serialized_read_size)
            read_counter += 1

            if debug:
                print("-->received data " + str(read_counter))
            
            check_read = read_parser.ParseFromString(data)
            decrypted_data = crypto.decrypt(read_parser.read)

            read_found = redis_table.get(int.from_bytes(read_parser.hash, 'big'))
            if read_found != None:
                print("Exact match read found.")
                found_reads += 1
            else:
                print("Read was not exact match.")

            if debug:
                print("Data: ")
                print(decrypted_data)
                print("Hash: ")
                print(read_parser.hash)
            
            if not data:
                break

def main():
    serialized_read_size = 70

    if mode == "DEBUG":
        cipherkey = b'0' * 32
    else:
        cipherkey = get_random_bytes(32)

    crypto = AES.new(cipherkey, AES.MODE_ECB) 

    run_redis_server()

    redis_table = redis.Redis(host='44.202.235.148', port=6379, db=0, password='lean-genes-17')
    receive_reads(4444, serialized_read_size, crypto, redis_table)

if __name__ == "__main__":
    main()

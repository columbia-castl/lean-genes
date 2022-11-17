import sys
import redis
import socket
import os

from reads_pb2 import Read
from Crypto.Cipher import AES

def run_redis_server():
    os.system("redis-server aligner_redis.conf &")


#Deserialize: read.ParseFromString(serialized_read)
def receive_reads(read_port, read_size):

    read_parser = Read()

    #Use read size to calc expected bytes for a read
    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #read_socket.settimeout(30)
    read_socket.bind(('127.0.0.1', read_port))
    read_counter = 0

    while True:
        read_socket.listen()
        conn, addr = read_socket.accept()
        
        while True:
            data = conn.recv(read_size)
            read_counter += 1
            print("-->received data " + str(read_counter))
            new_read = read_parser.ParseFromString(data)
            print(read_parser.hash)
            if not data:
                break



def main():
    read_length = 360

    run_redis_server()
    receive_reads(4444, read_length)

if __name__ == "__main__":
    main()

#Run redis server in background, then process reads and go through redis db
import sys
import redis
import socket
import os

def run_redis_server():
    os.system("redis-server aligner_redis.conf &")

def receive_reads(read_port, read_size):
   
    #Use read size to calc expected bytes for a read
    read_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    read_socket.settimeout(30)
    read_socket.bind(('127.0.0.1', read_port))
    read_counter = 0

    while True:
        read_socket.listen()
        conn, addr = read_socket.accept()
        
        while True:
            data = conn.recv(read_size)
            read_counter += 1
            print("-->received data " + str(read_counter))
            if not data:
                break

def main():
    read_length = 151

    run_redis_server()
    receive_reads(4444, read_length)

if __name__ == "__main__":
    main()

#!/usr/bin/python3

import sys
import hashlib
import hmac

from reads_pb2 import Read
from Crypto.Cipher import AES

AES_BLOCK = 16

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_fastq.py <fastq>")
        exit()

    fq_file = open(sys.argv[1], 'r')
    fq_file.readline()
    read = fq_file.readline()

    print(len(read) - 1, " is length of reads in this fastq")

    testread = Read()
    testkey = b'0' * 32
    
    testcrypto = AES.new(testkey, AES.MODE_ECB)

    read_bytes = bytes(read[:-1], 'utf-8')

    testhash = hmac.new(testkey, read_bytes, hashlib.sha256)
    testdigest = testhash.digest()

    while len(read_bytes) % AES_BLOCK != 0:
        read_bytes += b'0'

    testread.read = testcrypto.encrypt(read_bytes)
    testread.hash = testdigest

    fq_file.readline()
    qual_string = fq_file.readline()[:-1]
    testread.align_score = qual_string

    serialized_read = testread.SerializeToString()

    print(len(serialized_read), " is length of a serialized read")
    
if __name__ == "__main__":
    main()

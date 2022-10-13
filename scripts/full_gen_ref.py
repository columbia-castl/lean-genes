import hashlib
import base64
import matplotlib.pyplot as plt
import sys

from Crypto.Random import get_random_bytes 
from Crypto.Cipher import AES

def encrypt_ref():

    print("Begin encryption")
    encrypted_ref = []
    ref_file = open("chr21.fa", "rb")

    key = get_random_bytes(AES.block_size)
    encrypter = AES.new(key, AES.MODE_GCM)
    #decrypter = AES.new(key, AES.MODE_EAX, encrypter.nonce)

    num_hashes = 0

    #Create encrypted reference
    while True: 
        chunk = ref_file.read(AES.block_size)
        if not chunk:
            break
        encrypted_chunk = encrypter.encrypt(chunk)
        encrypted_ref.append(encrypted_chunk)

        num_hashes += 1
        
    print(num_hashes)
    print("Theoretical size of encrypted ref = " + str(num_hashes * AES.block_size))
    #print("Actual size of encrypted ref = " + str(sys.getsizeof(encrypted_ref[7])))
    
    print("End encryption")
    ref_file.close()
    return encrypted_ref 

def sliding_window_table(encrypted_ref, read_size=100, hash_bits=15):
    blocks_read = 0
    hashes_generated = 0
    hash_buffer = b''

    hash_table = [[] for _ in range(2**hash_bits)]
    
    num_encrypted_blocks = len(encrypted_ref)

    while (len(hash_buffer) < read_size):

        if blocks_read < num_encrypted_blocks:
            hash_buffer += encrypted_ref[blocks_read]
            blocks_read += 1
        else:
            break

        if blocks_read % 100000 == 0:
            print(blocks_read)
            print(str(hashes_generated * 32) + " bytes generated from hashing")

        while (len(hash_buffer) >= read_size):
            curr_hash = hashlib.sha3_256(hash_buffer).digest()
            hash_table[int.from_bytes(curr_hash, 'big') % (2**hash_bits)].append(curr_hash)
            hashes_generated += 1
            hash_buffer = hash_buffer[1:]          

    print(str(hashes_generated) + " hashes generated")
    return hash_table


def get_bucket_lens(hash_table, hash_bits):
    bucket_lens = []
    for i in range(2**hash_bits):
        bucket_lens.append(len(hash_table[i]))
    return bucket_lens



def main():
    hash_bits = 17

    encrypted_ref = encrypt_ref()
    hash_table = sliding_window_table(encrypted_ref, hash_bits=hash_bits)
    bucket_lens = get_bucket_lens(hash_table, hash_bits)
   
    plt.plot(bucket_lens)
    plt.title("Bucket distribution with " + str(2**hash_bits) + " buckets")
    plt.xlabel("Bucket index")
    plt.ylabel("Hashes in bucket")
    plt.grid()
    plt.savefig("bucket_data/buckets_" + str(2**hash_bits) + ".png")

if __name__ == "__main__":
    main()


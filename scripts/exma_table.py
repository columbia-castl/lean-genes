import hashlib
import base64
import matplotlib.pyplot as plt

from Crypto import Random
from Crypto.Cipher import AES

linear_hash_array = []
read_size = 150

hash_bits = 10

# https://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
class AESCipher(object):

    def __init__(self, key): 
        self.bs = AES.block_size
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode()))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

def get_bucket_lens(hash_table, hash_bits):
    bucket_lens = []
    for i in range(2**hash_bits):
        bucket_lens.append(len(hash_table[i]))
    return bucket_lens

def single_run(hash_bits):

    hash_table = [[] for _ in range(2**hash_bits)]
   
    ref_file = open("chr21.fa", "r")
    
    encrypter = AESCipher("01234")

    print(len(hash_table))

    num_hashes = 0
    while True: 
        chunk = ref_file.read(AES.block_size)
        if not chunk:
            break
        encrypted_chunk = encrypter.encrypt(chunk)
        hash_table[int.from_bytes(base64.b64decode(encrypted_chunk), 'big') % (2**hash_bits)].append(encrypted_chunk)
        num_hashes += 1
    print(num_hashes)

    ref_file.close()
    
    b_lens = get_bucket_lens(hash_table, hash_bits)
    plt.plot(b_lens)
    plt.title("Bucket distribution with " + str(2**hash_bits) + " buckets")
    plt.xlabel("Bucket index")
    plt.ylabel("Hashes in bucket")
    plt.grid()
    plt.savefig("bucket_data/buckets_" + str(2**hash_bits) + ".png")

def main():
    for i in range(10,15):
        single_run(i)

if __name__ == "__main__":
    main()


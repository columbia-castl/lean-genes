import numpy as np
import tensorflow_text as tf_text
import hashlib
import hmac

ref_length = 35106643
read_length = 151
fastq = "../test_data/chr21_preprocess.fa"

def main():
    pmt_table = np.random.permutation(ref_length)
    fastq_lines = open(fastq).readlines()

    filtered_fastq = ""
    for line in fastq_lines:
        if line[0] != ">":
            filtered_fastq += line[:-1]
    
    windows = tf_text.sliding_window(list(filtered_fastq), read_length, 0)
    print(str(len(windows)) + " windows in the sliding window")
    print(str(len(windows[0])) + " is the length of a window")

    key = b'0' * 32
   
    window_count = 0

    for window in windows:
        newhash = hmac.new(key, window, hashlib.sha256)
        curr_hash = newhash.digest()
        window_count += 1
        if window_count % 1000 == 0:
            print(window_count)

if __name__ == "__main__":
    main()



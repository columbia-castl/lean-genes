import tensorflow as tf
import numpy as np
import tensorflow_text as tf_text
import hashlib
import hmac
import redis
import threading

from _thread import *
from aligner_config import global_settings, secret_settings

#ref_length = 35106643
#read_length = 151
#fastq = "../test_data/chr21_preprocess.fa"

ref_length = 100
read_length = 15
fastq = "../test_data/small_reftest_15.fa"

pmt_table = ""

num_threads = 3

def main():
    global pmt_table

    pmt_table = np.random.RandomState(seed=secret_settings["perm_seed"]).permutation(ref_length)
    fastq_lines = open(fastq).readlines()

    filtered_fastq = ""
    for line in fastq_lines:
        if line[0] != ">":
            filtered_fastq += line[:-1]
    
    windows = tf_text.sliding_window(list(filtered_fastq), read_length, 0)
    print(str(len(windows)) + " windows in the sliding window")
    print(str(len(windows[0])) + " is the length of a window")

    init_index = 0
    thread_id = 0
    for i in range(num_threads-1):
        new_thread = threading.Thread(target=send_some_hashes, args=(windows[init_index:init_index + int(len(windows)/num_threads)], init_index, thread_id,))
        init_index += int(len(windows)/num_threads)
        thread_id += 1
        new_thread.start()

    last_thread = threading.Thread(target=send_some_hashes, args=(windows[init_index:], init_index, thread_id,))
    last_thread.start()

def send_some_hashes(windows, init_pmt_index, thread_id):

    print("function called with init index = " + str(init_pmt_index) + " from THREAD ID " + str(thread_id))

    redis_table = redis.Redis(host=global_settings["redis_ip"], port=global_settings["redis_port"], db=0, password='lean-genes-17', socket_connect_timeout=300)
    redis_pipe = redis_table.pipeline()

    window_count = 0
    key = b'0' * 32

    for window in windows:
        #print(tf.strings.join(window).numpy())
        newhash = hmac.new(key, tf.strings.join(window).numpy() , hashlib.sha256)
        curr_hash = newhash.digest()
        #print("WINDOW")
        #print(window.numpy())
        #print("HASH")
        #print(curr_hash)
        
        redis_pipe.set(int.from_bytes(curr_hash, 'big'), int(pmt_table[init_pmt_index + window_count]))
        window_count += 1
        if window_count % 100000 == 0:
            print(window_count)
            redis_pipe.execute()

    resp = redis_pipe.execute()
    #print(resp)
    print("fast indexing complete")
   

if __name__ == "__main__":
    main()



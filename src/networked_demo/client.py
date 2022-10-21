#client.py
import os
import requests
import random
import hashlib
import csv 
import math

ref_bases = 230464284
read_size = 148
seed_size = 2
ref_indices = [i for i in range(ref_bases - read_size + 1)] 
ref = ""
hashed_ref = []
seed_pointer_table = []
seed_locs = []
reads = []
chr_list = ['21']

CONNECT_AT = "http://3.91.218.191"

REF_NAME = "chr21.fa"
READ_FILE = "chr21.0.01.L150.100k.fastq"
READ_LENGTH = 148

DSOFT_BINS = 10
BIN_THRESHOLD = 5

def permute_indices():
    #Fisher-Yates
    for i in range(len(ref_indices)-1, 0, -1):
        j = random.randint(0, i+1)
        ref_indices[i], ref_indices[j] = ref_indices[j], ref_indices[i]

def load_ref(refname):
    ref_filename = refname + ".txt"
    return open(ref_filename, "r").read()

def load_ptable(refname):
    ptable_filename = refname + "_spt.txt"
    table_file = open(ptable_filename, "r")
    for i in range (int(4**seed_size)):
        seed_pointer_table.append(int(table_file.readline()))

def load_plocs(refname):
    loc_filename = refname + "_loc.txt"
    loc_file = open(loc_filename, "r")
    for i in range(ref_bases - read_size + 1):
        seed_locs.append(int(loc_file.readline()))

def hash_ref():
    for i in range(ref_bases - read_size + 1):
        hashed_ref.append(hashlib.sha3_256(ref[i : i + read_size].encode()))

def load_reads(readfile):
    read_file = open(readfile, 'r')
    csv_read = csv.reader(read_file)
    for row in csv_read:
        for read in row:
            reads.append(read)

def seed_lookup(seed):
    last_index = int(4**seed_size) - 1
    ptable_index = 0
    for i in range(len(seed)):
        ptable_index = ptable_index << 2
        if seed[i] == 'A':
            pass
        elif seed[i] == 'C':
            ptable_index += 1
        elif seed[i] == 'G':
            ptable_index += 2
        elif seed[i] == 'T':
            ptable_index += 3
        else:
            print("Problem processing a seed when doing lookup")
    print("index calculated = " + str(ptable_index))

    start_loc = seed_pointer_table[ptable_index]
    end_loc = -1

    if start_loc == -1:
        return -1
    elif ptable_index == last_index:
        end_loc = ref_bases - seed_size + 1
    else:
        next_index = ptable_index + 1
        while (seed_pointer_table[next_index] == -1 and next_index < last_index):
            next_index+=1
        if (seed_pointer_table[next_index] == -1):
            end_loc = ref_bases - seed_size
        else:
            end_loc = seed_pointer_table[next_index]

    print("start loc: " + str(start_loc))
    print("end loc: " + str(end_loc))
    
    locs = []
    for i in range(end_loc - start_loc):
        locs.append(seed_locs[start_loc + i])

    return locs

def dsoft(read):
    candidates = []
    last_hit_pos = [-1 * seed_size] * DSOFT_BINS
    bp_count = [0] * DSOFT_BINS

    for i in range(read_size - seed_size + 1):
        seed = read[i:i+seed_size]
        locs = seed_lookup(seed)
        if locs != -1:
            for loc in locs:
                bin = math.ceil((loc - i) / DSOFT_BINS)
                overlap = max(0, last_hit_pos[bin] + seed_size - i)
                last_hit_pos[bin] = i
                bp_count[bin] += seed_size - i
                if ((BIN_THRESHOLD + seed_size - overlap) > bp_count(bin)) and (bp_count[bin] >= BIN_THRESHOLD):
                    candidates.append((loc, i))
        else:
            return -1

    return candidates

def send_hashes():
    resp = requests.put(CONNECT_AT + "?num_hashes=" + str(len(hashed_ref)))
    for i in range(len(hashed_ref)):
        resp = requests.put(CONNECT_AT, data = hashed_ref[ref_indices[i]].hexdigest())
        print(resp)
    return resp

def get_match(index):
    print("getting this hash: " + hashed_ref[ref_indices[index]].hexdigest())
    resp = requests.get(CONNECT_AT + '?key=' + str(index))
    print(resp.text)

def query_cloud(hash, locs):
    loc_string = ""
    for loc in locs[:-1]:
        loc_string = loc_string + str(loc) + ","
    loc_string = loc_string + str(locs[-1]) + "&hash="
    loc_string += hash
    resp = requests.get(CONNECT_AT + '?locs=' + loc_string)
    return resp

def process_ref():
    global chr_list
    ref_file = open(REF_NAME, "r")
    
    # chr_list = [str(i+1) for i in range(22)]
    # chr_list.append('X')
    # chr_list.append('Y')
    
    doing_chromosome = False
    scanbuffer = ""

    testfile_str = "chr_text.txt"
    #testfile = open(testfile_str, 'w')

    resp = requests.put(CONNECT_AT + "?initiate_hashes=1" )

    send_hashes = []
    hash_per_packet = 10000000
    running_hash_count = 0
    early_stop = False

    while True:
        if early_stop:
            break
        nextline = ref_file.readline()
        if nextline == "":
            break
        if (nextline[0:4] == '>chr'):
            if len (chr_list) == 0:
                break
            elif (nextline[0:(4 + len(chr_list[0]))]) == ('>chr' + chr_list[0]):
                print('at chromosome ' + chr_list[0])
                chr_list.pop(0)
                scanbuffer = ""
        else:
            scanbuffer += nextline[:-1].upper()
            while len(scanbuffer) >= READ_LENGTH:
                hash_window = scanbuffer[0:READ_LENGTH]
                if not 'N' in hash_window:
                    #testfile.write(hash_window + "\n")
                    #resp = requests.put(CONNECT_AT, data = hashlib.sha3_256(hash_window.encode()).digest())
                    send_hashes.append(hashlib.sha3_256(hash_window.encode()).hexdigest())
                if (len(send_hashes) == hash_per_packet):
                    resp = requests.put(CONNECT_AT, json=send_hashes)
                    #early_stop = True
                    if (resp.status_code == 200):
                        send_hashes.clear()
                        running_hash_count += hash_per_packet
                        print(str(running_hash_count) + " hashes")
                    else:
                        print(resp)
                        print("There was a problem sending hashes, " + str(running_hash_count) + " hashes sent")
                        break
                scanbuffer = scanbuffer[1:]
    #If hashing windows didn't perfectly align to hash_per_packet!
    if (len(send_hashes) > 0):
        resp = requests.put(CONNECT_AT, json=send_hashes)

    #testfile.close()
    ref_file.close()
    print("ref scanned successfully")
    resp = requests.put(CONNECT_AT + "?stop_hashing=1")

def process_reads():
    resp = requests.put(CONNECT_AT + "?initiate_align=1")
    fastq_file = open(READ_FILE, 'r')
    one_read = [next(fastq_file) for i in range(4)]
    #while one_read[0] != "":
    read = one_read[1][:-1]
    readhash = hashlib.sha3_256(read.encode()).hexdigest()
    resp = query_cloud(readhash, [0])
    print(resp)
    #print ("read processed: " + str(len(read)))
    fastq_file.close()
    resp = requests.put(CONNECT_AT + "?end_align=1")


if __name__ == "__main__":
    #permute_indices()
    #print(ref_indices)

    #ref = load_ref("ref1")
    #print(ref)

    #hash_ref()
    #print(str(len(hashed_ref)) + " hashes stored from ref")

    #load_ptable("ref1")
    #print("seed pointer table loaded")
    #print(seed_pointer_table)

    #load_plocs("ref1")
    #print("seed locs loaded")
    #print(seed_locs)

    #load_reads("reads.csv")
    #print("reads loaded")
    
    process_ref()
    #dsoft("AA")
    process_reads()

    #send_hashes()
    #query_cloud(hashed_ref[ref_indices[1]].hexdigest(),[1])
    #get_match(1)



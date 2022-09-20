import hashlib

linear_hash_array = []
read_size = 150

def main():
    ref_file = open("chr21.fa", "r")
    
    lines_read = 0
    hashes_generated = 0
    hash_buffer = ""
    start = False

    while (len(hash_buffer) < read_size) or (start is False):
        start = True
        prev_size = len(hash_buffer)
        hash_buffer += ref_file.readline()
        lines_read += 1
        #if lines_read % 100000 == 0:
            #print(str(lines_read) + " lines read")
        new_size = len(hash_buffer)
        if prev_size == new_size:
            break
        while (len(hash_buffer) >= read_size):
            if 'N' not in hash_buffer[0:read_size-1]:
                linear_hash_array.append(hashlib.sha3_256(str(hash_buffer).encode()))
                hashes_generated += 1
            hash_buffer = hash_buffer[1:]          

    print(str(lines_read) + " lines in the file")
    print(str(hashes_generated) + " hashes generated")
    ref_file.close()

if __name__ == "__main__":
    main()


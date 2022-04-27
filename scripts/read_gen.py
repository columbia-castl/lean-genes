import random, sys

bases = ['A','C','G','T']

#for now, just support uniform read size generation
def generate_random_reads(num_reads, read_length):
    #read generation
    full_reads = []
    for i in range(num_reads):
        read = ''
        for j in range(read_length):
            read = read + bases[random.randint(0,3)]
        full_reads.append(read)

    #write reads to file
    readfile = open('reads.csv', 'w')
    for i in range(num_reads):
        if i != num_reads - 1:
            readfile.write(full_reads[i] + ',')
        else:
            readfile.write(full_reads[i] + '\n')
    readfile.close()

def generate_from_ref(num_reads, read_length, ref_source):
    full_reads = []
    ref_file = open(ref_source, "r")
    ref = ref_file.read()
    for i in range(num_reads):
        rand_index = random.randint(0, len(ref) - read_length)
        full_reads.append(ref[rand_index:rand_index+read_length])

    #write reads to file
    readfile = open('reads.csv', 'w')
    for i in range(num_reads):
        if i != num_reads - 1:
            readfile.write(full_reads[i] + ',')
        else:
            readfile.write(full_reads[i] + '\n')
    readfile.close()

def main():
    if (len(sys.argv) != 3) and (len(sys.argv) != 4):
        print("usage: <num_reads> <read_length> [<ref_source>]")
        exit(1)

    num_reads = int(sys.argv[1])
    read_length = int(sys.argv[2])

    if (len(sys.argv) == 4):
        ref_source = sys.argv[3]
        generate_from_ref(num_reads, read_length, ref_source)

    else:
        generate_random_reads(num_reads, read_length)

if __name__ == "__main__":
    main()

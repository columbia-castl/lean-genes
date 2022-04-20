import random, sys

bases = ['A','C','G','T']

#given all kmers of length n, this returns all kmers of length n+1
def generate_kmers(kmers):
    if len(kmers) == 0:
        kmers.append('')
    immutable_kmers = kmers.copy()
    for kmer in immutable_kmers:
        kmers.remove(kmer)
        for base in bases:
            #print('appending' + kmer + base)
            kmers.append(kmer + base)
    return kmers
        
def generate_reference(ref_length, ref_name):
    ref = ''
    for i in range(ref_length):
        ref += bases[random.randint(0, 3)]
    ref_file = open(ref_name + ".txt", 'w')
    ref_file.write(ref + "\n")
    ref_file.close()

def construct_tables(ref_name, kmer):
    #Read the reference genome into a string
    ref_file = open(ref_name + ".txt", "r")
    ref_string = ref_file.read()[:-1] #fixed bug- must trim newline
    ref_file.close()

    #Generate all kmers for given seed size from parameter 'kmer'
    all_kmers = []
    for i in range(kmer):
        all_kmers = generate_kmers(all_kmers)

    #initialize lists that tables will be constructed into
    seed_pointers = []
    seed_locations = []

    #search through reference for every possible kmer to make pointer and location tables
    num_entries = 0
    for potential_seed in all_kmers:
        preseed_length = len(seed_locations)
        for i in range(len(ref_string) - (kmer - 1)):
            if potential_seed == ref_string[i : i + kmer]:
                seed_locations.append(i)
        postseed_length = len(seed_locations)

        if not (postseed_length - preseed_length):
            seed_pointers.append(-1)
        else:
            seed_pointers.append(num_entries)

        num_entries += (postseed_length - preseed_length)


    #write pointer table to CSV
    pointer_file = open(ref_name + "_spt.txt", "w")
    for i in range(len(seed_pointers)):
            pointer_file.write(str(seed_pointers[i]) + "\n")    
    pointer_file.close()

    #write location table to CSV
    loc_file = open(ref_name + "_loc.txt", "w")   
    for i in range(len(seed_locations)):
            loc_file.write(str(seed_locations[i]) + "\n")
    loc_file.close()
    
def main():
    if len(sys.argv) != 4:
        print("usage: <reference length> <reference name> <seed length> ")
        exit(1)

    ref_length = int(sys.argv[1])
    ref_name = sys.argv[2]
    kmer = int(sys.argv[3])

    generate_reference(ref_length, ref_name)
    construct_tables(ref_name, kmer)

if __name__ == "__main__":
    main()
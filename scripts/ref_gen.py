import random, sys, itertools

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

def construct_txt_tables(ref_name, kmer):
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

def construct_fa_tables(ref_name, kmer):
        #Read the reference genome into a string
    ref_file = open(ref_name + ".fa", "r")
    #ref_string = ref_file.read()[:-1] #fixed bug- must trim newline
    #ref_file.close()

    #Generate all kmers for given seed size from parameter 'kmer'
    all_kmers = [''.join(k) for k in itertools.product(bases, repeat=kmer)]
    print('Created list of all kmers')

    #chr_list = [str(i+1) for i in range(22)]
    #chr_list.append('X')
    #chr_list.append('Y')

    chr_list = ['6']

    seed_dict = {}
    for seed in all_kmers:
        seed_dict[seed] = []
    print('Initialized seed dict')

    scanbuffer = ""
    loc = 0
    last_chr = ""

    chr_line_counter = 0

    starting_list_chr = False
    finishing_list_chr = False

    #search through reference for every possible kmer to make pointer and location tables
    while True:
        nextline = ref_file.readline()
        chr_line_counter += 1

        if (nextline[0] == '>'):
            finishing_list_chr = len(last_chr) > 0
            if (len(chr_list) > 0):
                starting_list_chr = nextline[0:(4 + len(chr_list[0]))] == ('>chr' + chr_list[0])
            elif not finishing_list_chr:
                break

            if finishing_list_chr:
                #write pointer and location table to .csv
                print("chr " + last_chr + ": " + str(chr_line_counter) + " lines")
                chr_line_counter = 0
                filter_file = open("filter_tables/" + ref_name + "_chr" + last_chr + "_" + str(kmer) + ".csv", "w")

                curr_seed_pt = 0
                for seed in all_kmers:
                    if (len(seed_dict[seed]) == 0):
                        filter_file.write(seed + ",-1\n")
                    else:
                        filter_file.write(seed + "," + str(len(seed_dict[seed])) + ",")    
                        for loc in seed_dict[seed][:-1]:
                            filter_file.write(str(loc) + ",")
                        filter_file.write(str(seed_dict[seed][-1]) + "\n")
                        curr_seed_pt += len(seed_dict[seed])
                    seed_dict[seed] = []

                filter_file.close()
                last_chr = ""
                scanbuffer = ""

            if starting_list_chr:
                print('at chromosome ' + chr_list[0])
                if (len(chr_list) > 0):
                    last_chr = chr_list.pop(0)

        elif starting_list_chr:
            scanbuffer += nextline[:-1].upper()
            while len(scanbuffer) >= kmer:
                seed_window = scanbuffer[0:kmer]
                if not 'N' in seed_window:
                    #print(str(seed_index) + "\n")
                    #print(seed_window)
                    seed_dict[seed_window].append(loc)
                    loc += 1
                    if (loc % 20000000) == 0:
                        print("\t" + str(loc) + " locs")
                scanbuffer = scanbuffer[1:]

def main():
    if len(sys.argv) != 4:
        print("usage: <reference length> <reference name> <seed length> ")
        exit(1)

    ref_length = int(sys.argv[1])
    ref_name = sys.argv[2]
    kmer = int(sys.argv[3])
    
    print("ref_length: " + str(ref_length))
    print("ref_name: " + ref_name)
    print("kmer: " + str(kmer))

    #generate_reference(ref_length, ref_name)
    #construct_txt_tables(ref_name, kmer)

    construct_fa_tables(ref_name, kmer)
    print("Finished constructing tables!")

if __name__ == "__main__":
    main()

#!/usr/bin/python3
import sys
import nltk

fastq_set = []
sam_set = []
sam_origin = []

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 sam_verifier.py <fastq> <sam>")
        exit()

    fastq = sys.argv[1]
    fq_file = open(fastq, 'r')

    fastq_lines = fq_file.readlines()
    append_next = False
    for line in fastq_lines:
        if line[0] == "@":
            append_next = True
        elif append_next:
            fastq_set.append(line[:-1])
            append_next = False
    fq_file.close()

    #print("READS FROM FASTQ:\n")
    #print(fastq_set)

    sam = sys.argv[2]
    sam_file = open(sam, 'r')

    result = sam_file.readline()
    while result:
        if result[0] == "@":
            pass
        else:
            sam_set.append(result.split('\t')[9])
            #print(len(sam_set[-1])) 
        result = sam_file.readline()
    sam_file.close()

    #print("READS FROM SAM:\n")
    #print(sam_set)
    
    read_count = 0
    not_count = 0
    all_in_sam = True
    no_duplicates = True
    for read in fastq_set:
        read_count += 1
        if read not in sam_set:
            print("!!! Read " + str(read_count) + " not in SAM!")
            edit_dist = [nltk.edit_distance(read, sam_read) for sam_read in sam_set]
            print(min(edit_dist), " is minimum edit distance.") 
            all_in_sam = False
            not_count += 1
        else:
            duplicate_count = -1
            while read in sam_set:
                sam_set.remove(read)
                duplicate_count += 1
            if duplicate_count:
                print("!!! Read " + str(read_count) + " duplicated in SAM!")
                print("Num duplicates: ", duplicate_count)
                no_duplicates = False 

    not_in_fastq = False
    if len(sam_set) > 0:
        not_in_fastq = True
        #print("Leftover reads =", len(sam_set))
    for leftover_read in sam_set:
        #print("LEFTOVER READ: ", leftover_read)
        pass

    print("***************************") 
    if all_in_sam:
        print("All reads from FASTQ in SAM")
    else:
        print(not_count, " reads were not in the SAM")
    if no_duplicates:
        print("No duplicate reads in SAM")
    else:
        print("The SAM had duplicate reads!!!")
    if not_in_fastq:
        print("The SAM contained " + str(len(sam_set)) + " reads not in the FASTQ")
    print("***************************") 

if __name__ == "__main__":
    main()

#!/usr/bin/python3
import sys

bwa_sam = []
lg_sam = []

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 sam_verifier.py <bwa_sam> <lg_sam>")
        exit()

    b_sam = sys.argv[1]
    b_file = open(b_sam, 'r')
    result = b_file.readline()
    while result:
        if result[0] == "@":
            pass
        else:
            bwa_sam.append(result.split('\t')[9])
        result = b_file.readline()
    b_file.close()

    l_sam = sys.argv[2]
    lg_file = open(l_sam, 'r')

    result = lg_file.readline()
    while result:
        if result[0] == "@":
            pass
        else:
            lg_sam.append(result.split('\t')[9])
            #print(len(lg_sam[-1])) 
        result = lg_file.readline()
    lg_file.close()

    read_count = 0
    not_count = 0
    all_in_lg = True
    no_duplicates = True
    for read in bwa_sam:
        read_count += 1
        if read not in lg_sam:
            print("!!! Read " + str(read_count) + " from BWA SAM not found in LEAN-GENES SAM!")
            all_in_lg = False
            not_count += 1
        else:
            duplicate_count = -1
            while read in lg_sam:
                lg_sam.remove(read)
                duplicate_count += 1
            if duplicate_count:
                print("!!! Read " + str(read_count) + " duplicated in LEAN-GENES SAM!")
                print("Num duplicates: ", duplicate_count)
                no_duplicates = False 

    not_in_bwa = False
    if len(lg_sam) > 0:
        not_in_bwa = True
        #print("Leftover reads =", len(lg_sam))
    for leftover_read in lg_sam:
        #print("LEFTOVER READ: ", leftover_read)
        pass

    print("***************************") 
    if all_in_lg:
        print("All reads from BWA SAM in LEAN-GENES SAM")
    else:
        print(not_count, " reads were not in the LEAN-GENES SAM")
    if no_duplicates:
        print("No duplicate reads in LEAN-GENES SAM")
    else:
        print("The SAM had duplicate reads!!!")
    if not_in_bwa:
        print("The SAM contained " + str(len(lg_sam)) + " reads not produced in BWA SAM")
    print("***************************") 

if __name__ == "__main__":
    main()

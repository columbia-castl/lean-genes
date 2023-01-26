import sys

def main():
    sam_file = sys.argv[1]
    sam = open(sam_file, 'r')

    header_len = 3
    for i in range(header_len):
        sam.readline()

    reads = sam.readlines()

    lg_count = 0
    bwa_count = 0
    unmapped = 0

    for read in reads:
        if read.split("\t")[2] == 'LG':
            lg_count += 1
        else:
            if read.split("\t")[3] != '0':
                bwa_count += 1
            else:
                unmapped += 1 

    print("\n*****************************************************************************************")
    print("SAM file " + sys.argv[1] + " contains " + str(len(reads)) + " reads")
    print("-----------------------------------------------------------------------------------------")
    print( str(lg_count) + "/" + str(len(reads)) + " mapped w lean-genes = " + str(float(lg_count)/float(len(reads))*100) + "%")
    print( str(bwa_count) + "/" + str(len(reads)) + " mapped w BWA = " + str(float(bwa_count)/float(len(reads))*100) + "%")
    print( str(unmapped) + "/" + str(len(reads)) + " unmapped = " + str(float(unmapped)/float(len(reads))*100) + "%")
    print("*****************************************************************************************\n")

if __name__ == "__main__":
    main()

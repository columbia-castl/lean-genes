#!/usr/bin/python3

import sys

def main():
    
    if len(sys.argv) != 3:
        print("Usage: python3 calc_accuracy.py <SAM file> <threshold>")
        exit()

    sam_file = open(sys.argv[1], 'r')
    threshold = int(sys.argv[2])

    num_reads = 0
    correct_reads = 0

    for line in sam_file:
        if line[0] == "@":
            continue

        result = line.split("\t")

        wgsim_pos = int(result[0].split("_")[1])
        mapped_pos = int(result[3])

        #print(wgsim_pos)
        #print(mapped_pos)
        diff = abs(wgsim_pos - mapped_pos)

        num_reads += 1
        if diff < threshold:
            correct_reads += 1
        else:
            print("Outside threshold: ", diff)

    print("SAM accuracy: ", correct_reads, "/", num_reads)
    print(correct_reads/num_reads * 100, " %")

if __name__ == "__main__":
    main()

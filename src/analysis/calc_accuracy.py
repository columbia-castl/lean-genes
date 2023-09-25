#!/usr/bin/python3

import os
import sys

def gather_files(search_dir, ext):
    found_files = []
    for root, dirs, files in os.walk(search_dir):
        for file in files:
            if (file.split(".")[-1] in ext):
                found_files.append(file)

    return found_files

def bwa_funnel(fastqs, bwa_path, ref, do_index=False):
    if do_index:
        os.system(bwa_path + "/bwa index " + ref)

    for fastq in fastqs:
        cmd_str = bwa_path + "/bwa mem " + ref + " " + fastq + " > " + fastq.rsplit(".", 1)[0] + ".sam"
        print(cmd_str)
        os.system(cmd_str)

def acc_from_sam(sam_name, threshold):
    
    sam_file = open(sam_name, 'r')
    print(sam_name)

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


def main():
    if (len(sys.argv) < 4) or (len(sys.argv) > 5):
        print("Usage: python3 calc_accuracy.py <FQ directory> <BWA path> <BWA ref> <OPT acc threshold>")
        exit()

    fastq_dir = sys.argv[1]
    fastqs = gather_files(fastq_dir, ["fq", "fastq"])
    print(fastqs)

    bwa_path = sys.argv[2]
    ref = sys.argv[3]
    bwa_funnel(fastqs, bwa_path, ref)

    sams = gather_files(fastq_dir, ["sam"])
    print("SAMs:\n_____")
    print(sams)
  
    if (len(sys.argv) == 5):
        threshold = int(sys.argv[4])
        for sam in sams:
            acc_from_sam(sam, threshold)

if __name__ == "__main__":
    main()

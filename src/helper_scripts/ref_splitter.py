split_set = [4, 10, 17]
ref_base = "GRCh38"

def split_ref(ref_file, chrom_partition):
    splitfile = open(ref_file, "r")
    splitlines = splitfile.readlines()
    
    splitter_index = 0

    part_files = []
    for i in range(len(chrom_partition) + 1):
        part_files.append(open(ref_base + "_split" + str(i) + ".fa", "w"))

    print("Begin partition 1...")
    for line in splitlines:

        if ">" in line:
            print("\t>>Chromosome reached")
            if (splitter_index < len(chrom_partition)) and (("chr" + str(chrom_partition[splitter_index])) in line):
                splitter_index += 1
                print("Begin partition " + str(splitter_index + 1) + "...")

        part_files[splitter_index].write(line)

    for i in range(len(chrom_partition) + 1):
        part_files[i].close()

    splitfile.close()

def verify_split(split_set):
    split_set.append(1000000) 
    split_index = 0
    chrom_index = 1
    for split_chrom in split_set:
        splitfile = open(ref_base + "_split" + str(split_index) + ".fa", "r")
        print("IN PARTITION " + str(split_index))
        while chrom_index < split_set[split_index]:
            for line in splitfile.readlines():
                if ">" in line:
                    print("\t" + line)
                    chrom_index += 1
        split_index += 1
        splitfile.close()

def main():
    refpath = "../test_data/GRCh38.fa" 
    print("Splitting ref for following partition")  
    print(split_set)
    split_ref(refpath, split_set)
    print("Splitting complete. Check folder of refpath to verify splitting")
    print("Verifying automatically...")
    verify_split(split_set)

if __name__ == "__main__":
    main()

filter_set = ['X','Y']
ref_base = "GRCh38"

def main():
    trimfile = open(ref_base + "_filtered.fa", "w")

    for i in range(1,23):
        filter_set.append(str(i))

    write_me = False

    refpath = "../../test_data/GRCh38.fa"
    filterfile = open(refpath, "r")
    print("opening filterfile...")

    for line in filterfile.readlines():
        if ">" in line:
            #Not magic... going off of fasta format >chrX for [4:]
            chrom_identifier = line.split()[0][4:]
            print("\t>>Chromosome " + chrom_identifier + " reached")
            if line.split()[0][4:] in filter_set:
                write_me = True
                filter_set.remove(line.split()[0][4:])
            else:
                write_me = False
        if write_me:
            trimfile.write(line)
        if len(filter_set) == 0:
            break

    filterfile.close()
    trimfile.close()

    for not_found in filter_set:
        print("Chromosome " + not_found + " was not found in this fasta file.")

if __name__ == "__main__":
    main()

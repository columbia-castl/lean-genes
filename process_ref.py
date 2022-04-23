refname = "GRCh38_latest_genomic.fna"

def main():
    ref_file = open(refname, "r")
    for line in ref_file.readlines():
        if line[0] == ">":
            print(line)

if __name__ == "__main__":
    main()
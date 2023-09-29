#!/usr/bin/python3

import os
import sys

error_rates = [0.01, 0.02, 0.05, 0.1]
read_sizes = [150,350,1000]

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 multi_wgsim.py <wgsim path> <ref>")
        exit()

    wgsim_path = sys.argv[1]
    ref = sys.argv[2]

    for error_rate in error_rates:
        for read_size in read_sizes:
            cmd_str = wgsim_path + "/wgsim -N 100000 -e " + str(error_rate) + " -1 " + str(read_size) + " " + ref + " reads_100k_" + str(error_rate) + "_" + str(read_size) + ".fq /dev/null > /dev/null"
            print(">>> " + cmd_str)
            os.system(cmd_str)

if __name__ == "__main__":
    main()

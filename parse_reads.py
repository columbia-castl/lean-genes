readfile = "chr21.0.01.L150.100k.fastq"

def main():
	rfile = open(readfile, 'r')
	reads = 0
	count = 0
	while True:
		line = rfile.readline()
		if len(line) == 0:
			break		
		if (count % 4) == 0:
			reads += 1
			#print("read " + str(reads))
		count += 1
		#print("line length: " + str(len(line)))
	rfile.close()
	print("file had " + str(reads) + " reads")

if __name__ == "__main__":
	main()

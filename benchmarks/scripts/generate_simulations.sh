./samtools-1.16.1/misc/wgsim -1 150 -2 150 -e 0.01 ./ref.fa 150-0.01.L.fastq 150-0.01.R.fastq > /dev/null
./samtools-1.16.1/misc/wgsim -1 150 -2 150 -e 0.02 ./ref.fa 150-0.02.L.fastq 150-0.02.R.fastq > /dev/null

./samtools-1.16.1/misc/wgsim -1 350 -2 350 -e 0.01 ./ref.fa 350-0.01.L.fastq 350-0.01.R.fastq > /dev/null
./samtools-1.16.1/misc/wgsim -1 350 -2 350 -e 0.02 ./ref.fa 350-0.02.L.fastq 350-0.02.R.fastq > /dev/null

./samtools-1.16.1/misc/wgsim -1 1000 -2 1000 -e 0.01 ./ref.fa 1000-0.01.L.fastq 1000-0.01.R.fastq > /dev/null
./samtools-1.16.1/misc/wgsim -1 1000 -2 1000 -e 0.02 ./ref.fa 1000-0.02.L.fastq 1000-0.02.R.fastq > /dev/null

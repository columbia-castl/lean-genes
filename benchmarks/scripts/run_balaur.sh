#!/bin/sh

/usr/bin/time -v ./balaur/src-cpp/balaur index ref.fa -t 25 > /dev/null
/usr/bin/time -v ./balaur/src-cpp/balaur ref.fa out.R1.fastq -t 25 > aln-se.sam 2> /dev/null
./samtools-1.16.1/misc/wgsim_eval.pl alneval -ag 20 ./out.R1.fastq.sam

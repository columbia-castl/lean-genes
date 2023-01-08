#!/bin/sh

/usr/bin/time -v ./bwa/bwa index ./ref.fa
/usr/bin/time -v ./bwa/bwa mem ./ref.fa ./out.R1.fastq ./out.R2.fastq -t 25 > aln-se.sam 

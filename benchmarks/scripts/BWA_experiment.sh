#!/bin/bash

./install_samtools.sh

wget ftp://ftp.sra.ebi.ac.uk/vol1/run/ERR324/ERR3240144/HG00138.final.cram -O subject.cram
wget ftp://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/reference/GRCh38_reference_genome/GRCh38_full_analysis_set_plus_decoy_hla.fa -O ref.fa

./samtools-1.16.1/samtools sort subject.cram -o subject.sorted.cram --threads 30
./samtools-1.16.1/samtools fastq --reference ref.fa -1 out.R1.fastq -2 out.R2.fastq subject.sorted.cram --threads 30

time bwa index ref.fa
time bwa mem ref.fa out.R1.fastq out.R2.fastq > aln-pe.sam

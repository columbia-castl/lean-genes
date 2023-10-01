#!/bin/bash

# COPY ALIGNER COMPONENTS TO DOCKER CONTAINER
cp ../src/aligner_enclave.py .
cp ../src/aligner_config.py .
cp ../src/reads_pb2.py .

# COPY BWA-MEMe
cp ../bwa/bwa .
cp ../src/pmt.csv .

# COPY REFERENCE TO DOCKER CONTAINER
#cp ../test_data/chr21.fa* .
cp ../../real_reads/GRCH38_21.fa* .

docker build -t lean_genes:v1 .
#docker run lean_genes:v1

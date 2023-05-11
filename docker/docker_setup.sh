#!/bin/bash

# COPY ALIGNER COMPONENTS TO DOCKER CONTAINER
cp ../src/aligner_enclave.py .
cp ../src/aligner_config.py .
cp ../src/reads_pb2.py .

# COPY BWA-MEMe
cp ../bwa/bwa .

# COPY REFERENCE TO DOCKER CONTAINER
#python3 ../src/helper_scripts/ref_gen.py 100 small_ref 1
cp ../test_data/chr21.fa .

docker build -t lean_genes:v1 .
#docker run lean_genes:v1

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
	git \
	python3 \
	python3-dev \
	python3-pip \
	redis-server 

RUN pip install pycryptodome redis numpy google protobuf pexpect

#Aligner code copy
COPY aligner_enclave.py bin/aligner_enclave.py
COPY aligner_config.py bin/aligner_config.py
COPY reads_pb2.py bin/reads_pb2.py

#BWA copy
COPY bwa bwa/bwa
COPY pmt.csv pmt.csv

#Data copy
COPY GRCH38_21.fa* data/
#CMD bwa/bwa index data/ref.fa && python3 bin/aligner_enclave.py data/ref.fa
CMD python3 bin/aligner_enclave.py data/GRCH38_21.fa

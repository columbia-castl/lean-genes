# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
	git \
	python3 \
	python3-dev \
	python3-pip \
	redis-server 

RUN pip install pycryptodome redis numpy google protobuf

#Code copy
COPY aligner_enclave.py bin/aligner_enclave.py
COPY aligner_config.py bin/aligner_config.py
COPY reads_pb2.py bin/reads_pb2.py
COPY bwa bwa/bwa

#Data copy
COPY chr21.fa test_data/ref.fa

CMD bwa/bwa index ref.fa
CMD python3 bin/aligner_enclave.py ref.fa

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
	git \
	python3 \
	python3-dev \
	python3-pip 

RUN pip install matplotlib pycryptodome 

COPY small_ref.fa small_ref.fa
COPY aligner_prototype.py bin/aligner_prototype.py
CMD python3 bin/aligner_prototype.py small_ref.fa

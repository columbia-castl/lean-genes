#!/bin/bash

git clone https://github.com/kokke/tiny-AES-c.git 

git clone https://github.com/lh3/bwa.git
cp bwa_patch/* bwa
cp bwa_patch/read_pmt* src
cd bwa
git apply bwa_pmt.patch
make clean; make

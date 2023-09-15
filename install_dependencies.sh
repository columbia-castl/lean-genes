#!/bin/bash

git clone https://github.com/kokke/tiny-AES-c.git 

rm -rf bwa
git clone https://github.com/lh3/bwa.git
cp bwa_patch/read_pmt* bwa
cd bwa
git apply --whitespace=fix ../bwa_patch/bwa_pmt.patch
#git apply --whitespace=fix --reverse ../bwa_patch/bwa_pmt.patch
#patch -p1 < bwa_pmt.patch
make

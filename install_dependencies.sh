#!/bin/bash

git clone https://github.com/kokke/tiny-AES-c.git 

git clone https://github.com/lh3/bwa.git
cp bwa_patch/* bwa
cd bwa
git apply --whitespace=fix bwa_pmt.patch
make

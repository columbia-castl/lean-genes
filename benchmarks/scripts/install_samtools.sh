#!/bin/bash
#
sudo yum -y groupinstall "Development Tools"
sudo yum -y install curl-devel ncurses-devel bzip2-devel xz-devel

wget https://github.com/samtools/samtools/releases/download/1.16.1/samtools-1.16.1.tar.bz2

tar -xvf samtools-1.16.1.tar.bz2
cd samtools-1.16.1 
./configure
make -j



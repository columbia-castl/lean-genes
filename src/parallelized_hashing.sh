#!/bin/bash

NUM_SPLITS=22

for (( i=1; i<=$NUM_SPLITS; i++ )) 
do
	python3 -u aligner_prototype.py ../test_data/GRCh38_split$i.fa > chr_$i.out &
done

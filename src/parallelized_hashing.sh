#!/bin/bash

NUM_SPLITS=22
ALIGNER=redis_cloudside

for (( i=1; i<=$NUM_SPLITS; i++ )) 
do
	time python3 -u aligner_$ALIGNER.py ../test_data/GRCh38_split$i.fa > chr_$i.out &
done

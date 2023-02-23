#!/bin/bash

for PERCENT in 1 2 3 4 5 6 7 8 9
do
	echo PERCENT = $PERCENT
	time python3 aligner_client.py ../test_data/sample-reads/matches_0.$PERCENT.fastq > client_log_$PERCENT
	cat ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam_* > ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam
	python3 analysis/sam_stats.py ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam > align_stats_$PERCENT	
	sleep 120
done

mkdir run
mv align_stats_* run
mv client_log_* run

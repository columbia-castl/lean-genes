#!/bin/bash

for PERCENT in 1 2 3 4 5 6 7 8 9 10
do
	echo PERCENT = $PERCENT
	rm ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam_*
	time python3 aligner_client.py ../test_data/sample-reads/matches_0.$PERCENT.fastq > client_log_$PERCENT
	cat ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam_* > ../test_data/matches_0.$PERCENT_lg.sam
	cd ../test_data
	../bwa/bwa mem ../test_data/chr21.fa ../test_data/sample-reads/matches_0.$PERCENT.fastq > ../test_data/matches_0.$PERCENT_bwa.sam
	cd -
	python3 analysis/sam_verifier.py ../test_data/matches_0.$PERCENT_bwa.sam ../test_data/matches_0.$PERCENT_lg.sam > verify_$PERCENT
	rm ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam_*	
	python3 analysis/sam_stats.py ../test_data/sample-reads/matches_0.$PERCENT.fastq.sam > align_stats_$PERCENT	
	sleep 120
done

mkdir last_lg_run
mv align_stats_* last_lg_run
mv verify_* last_lg_run
mv client_log_* last_lg_run

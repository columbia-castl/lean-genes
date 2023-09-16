proto: reads.proto
	protoc -I=. --python_out=. ./reads.proto

proto_clean:
	rm reads_pb2.py

post_proc:
	gcc post_process.c read_pmt.c ../tiny-AES-c/aes.c -g -o post_proc -I../tiny-AES-c

lg_clean:
	rm lg_*

clean_all:
	rm *.rdb post_proc lg_*

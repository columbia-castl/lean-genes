proto: reads.proto
	protoc -I=. --python_out=. ./reads.proto

proto_clean:
	rm reads_pb2.py

post_proc:
	gcc post_process.c read_pmt.c ../tiny-AES-c/aes.c -g -o post_proc -I../tiny-AES-c

clean:
	rm *.rdb post_proc

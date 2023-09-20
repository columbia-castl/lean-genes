lean_genes: proto post_proc

clean: lg_clean proto_clean post_proc_clean

proto: reads.proto
	protoc -I=. --python_out=. ./reads.proto

post_proc:
	gcc post_process.c read_pmt.c ../tiny-AES-c/aes.c -g -o post_proc -I../tiny-AES-c

lg_clean:
	rm -f lg_*

proto_clean:
	rm -f reads_pb2.py

post_proc_clean:
	rm -f post_proc


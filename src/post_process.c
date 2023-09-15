#include "post_process.h"

struct sam_line* init_sam_line_struct(int read_size){
        struct sam_line* line_reader = (struct sam_line*) malloc(sizeof(struct sam_line));
	line_reader->seq = (char*) malloc(read_size + (AES_BLOCK_SIZE - (read_size % AES_BLOCK_SIZE))); 
	line_reader->qual = (char*) malloc(read_size + 1);	
	return line_reader;
}

void delete_sam_line_struct(struct sam_line* line_reader) {
	free(line_reader->seq);
	free(line_reader->qual);
	free(line_reader);
}

int read_sam_line(struct sam_line* line_reader, FILE* fp) {
	return fscanf(fp, "%s\t%d\t%s\t%ld\t%d\t%s\t%c\t%c\t%c\t%s\t%s", line_reader->qname, &line_reader->flag, line_reader->rname, &line_reader->pos, &line_reader->mapq, line_reader->cigar, &line_reader->rnext, &line_reader->pnext, &line_reader->tlen, line_reader->seq, line_reader->qual);
}

char* decrypt_read(struct AES_ctx* ctx_ptr, struct sam_line* line_reader, FILE* decrypt_fp, int encrypted_size, int read_size) {

	unsigned char* read_bytes = malloc(encrypted_size + 1);	
	fread(read_bytes, encrypted_size, 1, decrypt_fp);

	unsigned char byte_block[AES_BLOCK_SIZE];

	for (int i = 0; i < (encrypted_size/AES_BLOCK_SIZE); i++) {
		memcpy(byte_block, read_bytes + (i*AES_BLOCK_SIZE), AES_BLOCK_SIZE);
		if (DEBUG) {
			printf("Encrypted block: %s\n", byte_block);
			for (int j = 0; j < AES_BLOCK_SIZE; j++) {
				printf("%02X ", byte_block[j]);
			}
			printf("\n");
		}
		AES_ECB_decrypt(ctx_ptr, byte_block);
		if (DEBUG) printf("Decrypt block: %s\n", byte_block);			
		memcpy(read_bytes + (i*AES_BLOCK_SIZE), byte_block, AES_BLOCK_SIZE);
	}
	
	read_bytes[read_size] = 0;
	line_reader->seq = (char*) read_bytes;	
}

void append_to_sam(struct sam_line* line_reader, FILE* new_sam, int read_size){

	char next_sam_line[3*read_size];

	sprintf(next_sam_line, "%s\t%d\t%s\t%ld\t%d\t%s\t%c\t%c\t%c\t%s\t%s\n", line_reader->qname, line_reader->flag, line_reader->rname, line_reader->pos, line_reader->mapq, line_reader->cigar, line_reader->rnext, line_reader->pnext, line_reader->tlen, line_reader->seq, line_reader->qual);
	
	fprintf(new_sam, "%s", next_sam_line);	

}

int run_batch(struct file_names* files, int read_size) {
	
	//scan thru the SAM file using the above fcns
	struct sam_line* line_reader = init_sam_line_struct(read_size);
	if (line_reader == NULL) {
		printf("The line reader did not initialize correctly.\n");
		return -1;
	}
	
	FILE* fp = fopen(files->sam_name, "r");
	if (fp == NULL) {
		printf("We couldn't find the SAM file: <%s>\n", files->sam_name);
		return -1;
	}

	FILE* decrypt_fp = fopen(files->bytes_name, "rb");
	if (decrypt_fp == NULL) {
		printf("Couldn't open encrypted bytes file <%s>\n", files->bytes_name);
		return -1;
	}
	FILE* new_sam = fopen(files->processed_name, "w");
	
	uint8_t key[AES_BLOCK_SIZE];
	unsigned char data_buf[AES_BLOCK_SIZE + 1];
	struct AES_ctx ctx;

	for (int i = 0; i < AES_BLOCK_SIZE; i++){
		key[i] = 0;
	}

	AES_init_ctx(&ctx, key);

	char sam_line[1024];
	int num_vals = 0;
	int read_counter = 0;
	
	int num_blocks = read_size / AES_BLOCK_SIZE;

	if (read_size % AES_BLOCK_SIZE) {
		num_blocks++;
	}
	if (DEBUG) printf("NUM BLOCKS: %d\n", num_blocks);

	int bytes_read = 0;	
	data_buf[AES_BLOCK_SIZE] = 0;

	while (num_vals = read_sam_line(line_reader, fp) != EOF) {
		if (DEBUG) printf("We scanned %d vals\n", num_vals);
		fgets(sam_line, INT_MAX, fp);

		if (line_reader->qname[0] == '@') {
			if (DEBUG) printf("Correct detection of header line.\n");
			continue;
		}
		else if (line_reader->qname[0] == '[') {
			if (DEBUG) printf("Correct detection of tool metadata.\n");
			continue;
		}
		else {
			int new_pos;	
			if ((int)line_reader->pos < i_pmt->pmt_size) {	
				new_pos = i_pmt->pmt_table[(int)line_reader->pos];
			}
			else {
				fprintf(stderr, "Post processor unable to load correct iPMT. Please regenerate w client.\n");
				fprintf(stderr, "iPMT size is %d, attempted loc %d\n", i_pmt->pmt_size, line_reader->pos);	
				exit(1);
			}
			if (DEBUG) printf("Old pos: %ld, ", line_reader->pos);
			line_reader->pos = new_pos;
			if (DEBUG) printf("new pos: %ld\n", line_reader->pos);

			if (DEBUG) print_sam_line_struct(line_reader);
			
			if (line_reader->flag != 2048) {
				decrypt_read(&ctx, line_reader, decrypt_fp, num_blocks*AES_BLOCK_SIZE, read_size);
			}
			if (DEBUG) print_sam_line_struct(line_reader);
			
			append_to_sam(line_reader, new_sam, read_size);

			read_counter++;

		}

	}
	
	printf("The post processor has gone through %d reads\n", read_counter);

	delete_sam_line_struct(line_reader);
	fclose(fp);
	fclose(decrypt_fp);
	fclose(new_sam);

	return 0;

}

struct file_names* init_file_names(struct file_names* files){
	
	if (files == NULL) {
		files = (struct file_names*) malloc(sizeof(struct file_names));
	}
	
	strcpy(files->sam_name, SAM_NAME);
	strcpy(files->bytes_name, ENCRYPTED_NAME);
	strcpy(files->processed_name, PROCESSED_NAME);

	return files;
}

void make_batch_file_names(struct file_names* files, char* batch_num){
	strcat(files->sam_name, "_");
	strcat(files->sam_name, batch_num);

	strcat(files->bytes_name, "_");
	strcat(files->bytes_name, batch_num);

	strcat(files->processed_name, "_");
	strcat(files->processed_name, batch_num);
}

void check_file_names(struct file_names* files){
	printf("SAM filename: %s\n", files->sam_name);
	printf("enc bytes filename: %s\n", files->bytes_name);
	printf("Results filename: %s\n", files->processed_name);
}

void print_help() {
	printf("Not enough args to post processor.\n");
	printf("Usage: ./post_proc <options>\n");
	printf("OPTIONS:\n");
	printf("\t-i --> run post-processor interactively\n");
	printf("\t-r <read size> --> size of reads post proc will process [MANDATORY]\n");
	printf("\t-l <label num> --> if provided, search for a batch\n\n");
	exit(1);
}

void print_sam_line_struct(struct sam_line* line_reader){
	printf("************************\n");
	printf("<qname>: %s\n", line_reader->qname);
	printf("<flag>: %d\n", line_reader->flag);
	printf("<rname>: %s\n", line_reader->rname);
	printf("<pos>: %ld\n", line_reader->pos);
	printf("<mapq>: %d\n", line_reader->mapq);
	printf("<cigar>: %s\n", line_reader->cigar);
	printf("<rnext>: %c\n", line_reader->rnext);
	printf("<pnext>: %c\n", line_reader->pnext);
	printf("<tlen>: %c\n", line_reader->tlen);
	printf("<seq>: %s\n", line_reader->seq);
	printf("<qual>: %s\n", line_reader->qual);
	printf("************************\n");
}

int main(int argc, char** argv) {
	//We are being given a batch number
	char sam_name[50];
	char bytes_name[50];	
	char processed_name[50];

	int interactive = 0;
	int subbatch = 0;
	char* batch_num;
	int read_size = 0;

	if (argc < 2) print_help(); 
	
	int c;
	while ((c = getopt(argc, argv, "ir:l:")) != -1) {
		switch(c)
			{
			case 'i':
				interactive = 1;
				break;
			case 'r':
				read_size = atoi(optarg);
				break;
			case 'l':
				subbatch = 1;
				batch_num = optarg;
				break;
			}
	}

	if (!read_size) {
		printf("The -r <read_size> option is MANDATORY!\n");
		print_help();
	}

	if (interactive && subbatch) {
		printf("!!! CANNOT run post-processor interactively and give sub-batch!\n");
		print_help();
	}

	struct file_names* files = init_file_names(NULL);
	if (subbatch) {
		printf("Performing sub-batch.\n");	
		make_batch_file_names(files, batch_num);		
	}

	i_pmt = read_pmt(INVERSE);

	if (interactive) {
		while (1) {
			printf("Wait to process batch.\n");
			char batch_num[10];
			scanf("%s", batch_num);
			
			if (!strcmp(batch_num, "quit")) {
				break;
			}
			
			init_file_names(files);
			make_batch_file_names(files, batch_num);
			run_batch(files, read_size);
		}	
	}
	else {
		run_batch(files, read_size);
	}	

	return 0;
}

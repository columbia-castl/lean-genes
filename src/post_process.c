#include "post_process.h"

struct sam_line* init_sam_line_struct(){
        struct sam_line* line_reader = (struct sam_line*) malloc(sizeof(struct sam_line));
	line_reader->seq = (char*) malloc(READ_LENGTH + (AES_BLOCK_SIZE - (READ_LENGTH % AES_BLOCK_SIZE))); 
	return line_reader;
}

void delete_sam_line_struct(struct sam_line* line_reader) {
	free(line_reader->seq);
	free(line_reader);
}

int read_sam_line(struct sam_line* line_reader, FILE* fp) {
	return fscanf(fp, "%s\t%d\t%s\t%ld\t%d\t%s\t%c\t%c\t%c\t%s\t%s", line_reader->qname, &line_reader->flag, line_reader->rname, &line_reader->pos, &line_reader->mapq, line_reader->cigar, &line_reader->rnext, &line_reader->pnext, &line_reader->tlen, line_reader->seq, line_reader->qual);
}

char* decrypt_read(struct AES_ctx* ctx_ptr, struct sam_line* line_reader, FILE* decrypt_fp, int encrypted_size) {

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
	
	read_bytes[READ_LENGTH] = 0;
	line_reader->seq = (char*) read_bytes;	
}

void append_to_sam(struct sam_line* line_reader, FILE* new_sam){

	char next_sam_line[3*READ_LENGTH];

	sprintf(next_sam_line, "%s\t%d\t%s\t%ld\t%d\t%s\t%c\t%c\t%c\t%s\t%s\n", line_reader->qname, line_reader->flag, line_reader->rname, line_reader->pos, line_reader->mapq, line_reader->cigar, line_reader->rnext, line_reader->pnext, line_reader->tlen, line_reader->seq, line_reader->qual);
	
	fprintf(new_sam, "%s", next_sam_line);	

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

int main() {
	//return the iPMT
	struct pmt_struct* i_pmt = read_pmt(INVERSE);
	//exit(1);

	//then scan thru the SAM file using the above fcns
	struct sam_line* line_reader = init_sam_line_struct();
	if (line_reader == NULL) {
		printf("The line reader did not initialize correctly.\n");
		exit(1);
	}
	
	FILE* fp = fopen(SAM_NAME, "r");
	if (fp == NULL) {
		printf("We couldn't find the SAM file.\n");
		exit(1);
	}

	FILE* decrypt_fp = fopen(ENCRYPTED_NAME, "rb");
	FILE* new_sam = fopen(PROCESSED_NAME, "w");

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
	
	int num_blocks = READ_LENGTH / AES_BLOCK_SIZE;

	if (READ_LENGTH % AES_BLOCK_SIZE) {
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
			
			decrypt_read(&ctx, line_reader, decrypt_fp, num_blocks*AES_BLOCK_SIZE);

			if (DEBUG) print_sam_line_struct(line_reader);
			
			append_to_sam(line_reader, new_sam);

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

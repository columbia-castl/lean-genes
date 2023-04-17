#include "post_process.h"

struct sam_line* init_sam_line_struct(){
        struct sam_line* line_reader = (struct sam_line*) malloc(sizeof(struct sam_line));
	line_reader->seq = (char*) malloc(READ_LENGTH + (AES_BLOCK_SIZE - (READ_LENGTH % AES_BLOCK_SIZE)) + 1);
	line_reader->seq[READ_LENGTH + (AES_BLOCK_SIZE - (READ_LENGTH % AES_BLOCK_SIZE))] = 0;
        return line_reader;
}

void delete_sam_line_struct(struct sam_line* line_reader) {
	free(line_reader->seq);
	free(line_reader);
}

int read_sam_line(struct sam_line* line_reader, FILE* fp) {
	return fscanf(fp, "%s\t%d\t%s\t%ld\t%d\t%s\t%c\t%c\t%c\t", line_reader->qname, &line_reader->flag, line_reader->rname, &line_reader->pos, &line_reader->mapq, line_reader->cigar, &line_reader->rnext, &line_reader->pnext, &line_reader->tlen);
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
	int* i_pmt = read_pmt(INVERSE);

	//then scan thru the SAM file using the above fcns
	struct sam_line* line_reader = init_sam_line_struct();
	if (line_reader == NULL) {
		printf("The line reader did not initialize correctly.\n");
		exit(1);
	}
	
	FILE* fp = fopen(SAM_NAME, "rb");
	if (fp == NULL) {
		printf("We couldn't find the SAM file.\n");
		exit(1);
	}
	
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
	printf("NUM BLOCKS: %d\n", num_blocks);

	int bytes_read = 0;	
	data_buf[AES_BLOCK_SIZE] = 0;

	while (num_vals = read_sam_line(line_reader, fp) != EOF) {
		printf("We scanned %d vals\n", num_vals);
		
		if (line_reader->qname[0] == '@') {
			printf("Correct detection of header line.\n");
			fgets(sam_line, INT_MAX, fp);
			continue;
		}
		else {
			bytes_read = fread(line_reader->seq, num_blocks * AES_BLOCK_SIZE , 1, fp);
			printf("Call to get read received %d bytes\n", bytes_read);
			fscanf(fp, "\t%s", line_reader->qual);
			fgets(sam_line, INT_MAX, fp);

			printf("encrypted bytes: %s\n", line_reader->seq);
			printf("LEN(encrypted bytes): %u\n", strlen(line_reader->seq));

			//decrypt the encrypted read
			for (int i = 0; i < num_blocks; i++) {
				memcpy(data_buf, (line_reader->seq) + (i*AES_BLOCK_SIZE), AES_BLOCK_SIZE);
				printf("Encrypted block: %s\n", data_buf);
				for (int j = 0; j < AES_BLOCK_SIZE; j++) {
					printf("%02X ", data_buf[j]);
				}
				printf("\n");
				AES_ECB_decrypt(&ctx, data_buf);
				printf("Decrypt block: %s\n", data_buf);			
				memcpy((line_reader->seq) + (i*AES_BLOCK_SIZE), data_buf, AES_BLOCK_SIZE);
			}
			
			print_sam_line_struct(line_reader);
			printf("\n\nIN THE REST OF LINE: %s\n", sam_line);

			read_counter++;

		}
		/*else {
			int num_scanned = read_sam_line(line_reader, sam_line, fp);	
			printf("We scanned %d things into the line reader.\n", num_scanned);

			if (num_scanned == FULL_SAM_LINE_LEN) {
				//decrypt the encrypted read
				int num_blocks = READ_LENGTH / AES_BLOCK_SIZE;

				if (READ_LENGTH % AES_BLOCK_SIZE) {
					num_blocks++;
				}

				for (int i = 0; i < num_blocks; i++) {
					memcpy(data_buf, (line_reader->seq) + (i*AES_BLOCK_SIZE), AES_BLOCK_SIZE);
					AES_ECB_decrypt(&ctx, data_buf);			
					memcpy((line_reader->seq) + (i*AES_BLOCK_SIZE), data_buf, AES_BLOCK_SIZE);
				}
				printf("The decrypted read is: %s\n", line_reader->seq);

				//De-permute the pos
				int new_pos = i_pmt[(int)line_reader->pos];
				printf("The new pos is: %d\n", new_pos);
			}
			else {
				printf("WARNING! SAM had badly formatted line!\n");
			}
		}*/
	}
	
	printf("The post processor has gone through %d reads\n", read_counter);

	delete_sam_line_struct(line_reader);
	fclose(fp);
	
	return 0;
}

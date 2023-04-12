#include "post_process.h"

struct sam_line* init_sam_line_struct(){
        struct sam_line* line_reader = (struct sam_line*) malloc(sizeof(struct sam_line));
        return line_reader;
}

void delete_sam_line_struct(struct sam_line* line_reader) {
	free(line_reader);
}

int read_sam_line(struct sam_line* line_reader, char* sam_string) {
	return sscanf(sam_string, "%s\t%d\t%s\t%ld\t%d\t%c\t%c\t%c\t%c\t%s\t%s", line_reader->qname, &line_reader->flag, line_reader->rname, &line_reader->pos, &line_reader->mapq, &line_reader->cigar, &line_reader->rnext, &line_reader->pnext, &line_reader->tlen, line_reader->seq, line_reader->qual);
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
	
	FILE* fp = fopen(SAM_NAME, "r");
	if (fp == NULL) {
		printf("We couldn't find the SAM file.\n");
		exit(1);
	}
	
	uint8_t key[AES_BLOCK_SIZE];
	char data_buf[AES_BLOCK_SIZE];
	struct AES_ctx ctx;

	for (int i = 0; i < AES_BLOCK_SIZE; i++){
		key[i] = 0;
	}

	AES_init_ctx(&ctx, key);

	char sam_line[1024];

	while (fgets(sam_line, sizeof(sam_line), fp) != NULL) {
		if (sam_line[0] == '@') {
			continue;
		}
		else {
			int num_scanned = read_sam_line(line_reader, sam_line);	
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
		}
	}

	delete_sam_line_struct(line_reader);
	fclose(fp);
	
	return 0;
}

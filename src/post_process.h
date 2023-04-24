#include "aes.h"
#include "read_pmt.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#define READ_LENGTH 151
#define AES_BLOCK_SIZE 16
#define SAM_NAME "lg_out.sam"
#define ENCRYPTED_NAME "enclave.bytes"
#define PROCESSED_NAME "stitched.sam"
#define FULL_SAM_LINE_LEN 11

#define DEBUG 0

struct sam_line{
	char qname[40];
	int flag;
	char rname[20];
	long pos;
	int mapq;
	char cigar[20];
	char rnext;
	char pnext;
	char tlen;
	char* seq;
	char qual[READ_LENGTH+1];	
};

struct sam_line* init_sam_line_struct();
void delete_sam_line_struct(struct sam_line* line_reader);

int read_sam_line(struct sam_line* line_reader, FILE* fp);
char* decrypt_read(struct AES_ctx* ctx_ptr, struct sam_line* line_reader, FILE* decrypt_fp, int encrypted_size);

void append_to_sam(struct sam_line* line_reader, FILE* new_sam);

void print_sam_line_struct(struct sam_line* line_reader);


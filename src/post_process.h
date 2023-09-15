#include "aes.h"
#include "read_pmt.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <unistd.h>

#define AES_BLOCK_SIZE 16
#define SAM_NAME "lg_secure_batch"
#define ENCRYPTED_NAME "lg_enclave.bytes"
#define PROCESSED_NAME "lg_stitched.sam"
#define FULL_SAM_LINE_LEN 11

#define DEBUG 0

struct pmt_struct* i_pmt;

struct file_names{
	char sam_name[50];
	char bytes_name[50];
	char processed_name[50];
};

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
	char* qual;	
};

struct sam_line* init_sam_line_struct(int read_size);
void delete_sam_line_struct(struct sam_line* line_reader);
int read_sam_line(struct sam_line* line_reader, FILE* fp);

char* decrypt_read(struct AES_ctx* ctx_ptr, struct sam_line* line_reader, FILE* decrypt_fp, int encrypted_size, int read_size);

struct file_names* init_file_names(struct file_names* files);
void make_batch_file_names(struct file_names* files, char* batch_num);
void append_to_sam(struct sam_line* line_reader, FILE* new_sam, int read_size);
int run_batch(struct file_names* files, int read_size);

void print_help();
void print_sam_line_struct(struct sam_line* line_reader);


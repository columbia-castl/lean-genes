#include "aes.h"
#include <stdio.h>
#include <stdlib.h>

#define READ_LENGTH 151
#define AES_BLOCK_SIZE 16
#define SAM_NAME "done.sam"

struct sam_line{
	char qname[20];
	int flag;
	char rname[20];
	long pos;
	int mapq;
	char cigar;
	char rnext;
	char pnext;
	char tlen;
	//NOTE: THIS SHOULD BE UNCOMMENTED WHEN READ LENGTH IS LONGER	
	//char seq[READ_LENGTH + (READ_LENGTH % AES_BLOCK_SIZE)];
	char seq[READ_LENGTH];
	char qual[READ_LENGTH];	
};

struct sam_line* init_sam_line_struct();
void delete_sam_line_struct(struct sam_line* line_reader);
int read_sam_line(struct sam_line* line_reader, char* sam_string);

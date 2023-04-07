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
	//TODO: return the PMT
	
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

	char sam_line[1024];

	while (fgets(sam_line, sizeof(sam_line), fp) != NULL) {
		if (sam_line[0] == '@') {
			continue;
		}
		else {
			int num_scanned = read_sam_line(line_reader, sam_line);	
			printf("We scanned %d things into the line reader.\n", num_scanned);
		}
	}

	delete_sam_line_struct(line_reader);
	fclose(fp);
	
	return 0;
}

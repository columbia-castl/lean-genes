#include "read_pmt.h"

struct pmt_struct* read_pmt(int type) {

	FILE* pmt_file;
	if (type) {
		pmt_file = fopen("ipmt.csv","r");
	}
	else {
		pmt_file = fopen("pmt.csv","r");
	}
	
	struct pmt_struct* pmt_buf = (struct pmt_struct*) malloc(sizeof(struct pmt_struct));

	if (pmt_file == NULL) {
		printf("Could not find the PMT file!\n");
		exit(1);
	}
	else {
		int perm_len;
		int items_scanned;

		items_scanned = fscanf(pmt_file, "%d:", &perm_len);

		pmt_buf->pmt_size = perm_len;
		//printf("Perm len is %d\n", perm_len);

		pmt_buf->pmt_table = (int*) malloc(perm_len * sizeof(int));
		int buf_index = 0;
		
		int nums_remaining = perm_len - 1;
		
		while (nums_remaining) {
			items_scanned = fscanf(pmt_file, "%d,", pmt_buf->pmt_table + buf_index);
			nums_remaining--;
			buf_index++;

			if (!items_scanned) {
				fprintf(stderr, "Expected another PMT entry, there was none.\n");
				fprintf(stderr, "PMT size %d, %d items remaining\n", pmt_buf->pmt_size, nums_remaining);	
				exit(1);
			}		
		}

		items_scanned = fscanf(pmt_file, "%d", pmt_buf->pmt_table + buf_index);
		if (!items_scanned) {
			fprintf(stderr, "Expected final PMT entry, there was none.\n");
			exit(1);	
		}
	
	}
	
	fclose(pmt_file);	
	//printf("PMT fully scanned.\n");
	return pmt_buf;
}

/*
int main() {
	struct pmt_struct* pmt = read_pmt(DEFAULT);
	printf("Entry 42836700: %d\n", pmt->pmt_table[42836700]);
	free(pmt->pmt_table);
	free(pmt);
	return 0;
}*/ 

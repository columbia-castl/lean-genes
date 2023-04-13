#include "read_pmt.h"

int* read_pmt(int type) {

	FILE* pmt_file;
	if (type) {
		pmt_file = fopen("ipmt.csv","r");
	}
	else {
		pmt_file = fopen("pmt.csv","r");
	}
	
	int* pmt_buf = NULL;

	if (pmt_file == NULL) {
		printf("Could not find the PMT file!\n");
		exit(1);
	}
	else {
		int perm_len;
		int items_scanned;

		items_scanned = fscanf(pmt_file, "%d:", &perm_len);

		//printf("Perm len is %d\n", perm_len);

		pmt_buf = (int*) malloc(perm_len * sizeof(int));
		int buf_index = 0;
		
		int nums_remaining = perm_len - 1;
		
		while (nums_remaining) {
			items_scanned = fscanf(pmt_file, "%d,", pmt_buf + buf_index);
			nums_remaining--;
			buf_index++;

			if (!items_scanned) {
				fprintf(stderr, "Expected another PMT entry, there was none.\n");
				exit(1);
			}		
		}

		items_scanned = fscanf(pmt_file, "%d", pmt_buf + buf_index);
		if (!items_scanned) {
			fprintf(stderr, "Expected final PMT entry, there was none.\n");
			exit(1);	
		}
	
	}
	
	fclose(pmt_file);	
	//printf("PMT fully scanned.\n");
	return pmt_buf;
}

/* int main() {
	int* pmt = read_pmt();
	printf("Entry 42836700: %d\n", pmt[42836700]);
	free(pmt);
	return 0;
} */

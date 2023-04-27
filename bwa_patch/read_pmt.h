#include <stdio.h>
#include <stdlib.h>

#define INVERSE 1
#define DEFAULT 0

struct pmt_struct {
	int pmt_size;
	int* pmt_table;
};

struct pmt_struct* read_pmt(int type);

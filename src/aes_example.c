#include <stdio.h>
#include <stdlib.h>
#include "aes.h"

#define ECB 1
#define KEYLEN 16

int main() {
	
	struct AES_ctx ctx;
	uint8_t key[16];
	char data_buf[16];
	
	for (int i = 0; i < KEYLEN; i++) {
		key[i] = 0;
		data_buf[i] = 0;
	}

	AES_init_ctx(&ctx, key);

	data_buf[0] = 'h';
	data_buf[1] = 'e';
	data_buf[2] = 'l';
	data_buf[3] = 'p';

	printf("Input string: %s\n",data_buf);
	
	AES_ECB_encrypt(&ctx, data_buf);
	printf("Encrypted input string: %s\n",data_buf);

	AES_ECB_decrypt(&ctx, data_buf);
	printf("Decrypted input string: %s\n",data_buf);

	return 0;
}

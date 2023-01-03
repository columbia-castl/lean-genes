
global_settings = dict(
    redis_port = 6379,
    redis_ip = '54.166.184.178'
)

client_settings = dict(
    pmt_port = 4445,
    read_port = 4444,
    server_ip = '54.166.184.178'
)

pubcloud_settings = dict(
    enclave_ip = '54.166.184.178',
    read_port = 4444,
    pmt_client_port = 4445,
    vsock_port = 5006
)

enclave_settings = dict(
    vsock_port = 5006
)

#CHR21 parameters 
#ref_length = 35106643 
#read_length = 151 
genome_params = dict(
    REF_LENGTH = 100, #Length of FASTA sequence
    READ_LENGTH = 15,  #Length of individual FASTQ reads
    SERIALIZED_READ_SIZE = 70,
    BATCH_SIZE = 1
)

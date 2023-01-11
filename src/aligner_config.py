
global_settings = dict(
    redis_port = 6379,
    redis_ip = '54.210.209.15',
    index_exists = True
)

client_settings = dict(
    server_ip = '54.210.209.15',
    pmt_port = 4445,
    read_port = 4444,
    result_port = 4446
)

pubcloud_settings = dict(
    enclave_ip = '54.210.209.15',
    client_ip = '54.210.209.15',
    read_port = 4444,
    pmt_client_port = 4445,
    result_port = 4446,
    vsock_port = 5006,
    bwa_port = 5007,
)

enclave_settings = dict(
    server_ip = '54.210.209.15',
    vsock_port = 5006,
    bwa_path = "../bwa",
    bwa_port = 5007
)

leangenes_params = dict(
    unmatched_threshold = 1,
    matched_threshold = 1
)

#CHR21 parameters 
#ref_length = 35106643 
#read_length = 151 
genome_params = dict(
    REF_LENGTH = 100, #Length of FASTA sequence
    READ_LENGTH = 15,  #Length of individual FASTQ reads
    SERIALIZED_READ_SIZE = 69,
    BATCH_SIZE = 2 #Length of FASTQs created by enclave
)

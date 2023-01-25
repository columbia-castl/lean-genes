
global_settings = dict(
    redis_port = 6379,
    redis_ip = '18.208.155.212',
)

#IP addresses refer to the machines that each component is connecting to, and not itself
#Currently, the pubcloud's IP is potentially misleadingly named "server_ip"
client_settings = dict(
    server_ip = '18.208.155.212',
    pmt_port = 4445,
    read_port = 4444,
    result_port = 4446,
    debug = False
)

pubcloud_settings = dict(
    enclave_ip = '18.208.155.212',
    client_ip = '54.210.209.15',
    read_port = 4444,
    pmt_client_port = 4445,
    result_port = 4446,
    unmatched_port = 5006,
    bwa_port = 5007,
    debug = False
)

enclave_settings = dict(
    server_ip = '18.208.155.212',
    vsock_port = 5006,
    #If this path isn't empty (i.e. BWA is on PATH), make sure it ends with /"
    bwa_path = "../bwa/",
    bwa_port = 5007,
    bwa_index_exists = True,
    separate_hashing = True,
    debug = False
)

secret_settings = dict(
    #Placeholder for key shared w/ client and enclave
    perm_seed = 7
)

leangenes_params = dict(
    unmatched_threshold = 1,
    matched_threshold = 1,
    AES_BLOCK_SIZE = 16
)

#CHR21 parameters 
#ref_length = 35106643 
#read_length = 151
#serialized = 351

#Sample testing parameters
#ref_length = 100
#read_length = 15
#serialized = 69
genome_params = dict(
    REF_LENGTH = 100, #Length of FASTA sequence
    READ_LENGTH = 15,  #Length of individual FASTQ reads
    SERIALIZED_READ_SIZE = 69, #Length of a protobuf message read
    BATCH_SIZE = 2 #Length of FASTQs created by enclave
)

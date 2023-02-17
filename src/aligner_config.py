
global_settings = dict(
    redis_port = 6379,
    redis_ip = '3.84.84.168',
)

#IP addresses refer to the machines that each component is connecting to, and not itself
#Currently, the pubcloud's IP is misleadingly named "server_ip"
client_settings = dict(
    server_ip = '3.84.84.168',
    pmt_port = 4445,
    read_port = 4444,
    result_port = 4446,
    control_port = 4447,
    debug = False,
    #results_threads = 11
)

pubcloud_settings = dict(
    enclave_ip = '3.84.84.168',
    client_ip = '3.84.84.168',
    read_port = 4444,
    pmt_client_port = 4445,
    result_port = 4446,
    control_port = 4447,
    unmatched_port = 5006,
    bwa_port = 5007,
    only_indexing = False,
    disable_exact_matching = False,
    debug = False
)

enclave_settings = dict(
    server_ip = '3.84.84.168',
    vsock_port = 5006,
    #If this path isn't empty (i.e. BWA is on PATH), make sure it ends with /"
    bwa_path = "../bwa/",
    bwa_port = 5007,
    bwa_index_exists = True,
    separate_hashing = True,
    only_indexing = False,
    hashing_progress_indicator = 1000000,
    debug = False
)

secret_settings = dict(
    #Placeholder for key shared w/ client and enclave
    perm_seed = 7
)

leangenes_params = dict(
    BWA_BATCH_SIZE = 1000, #Length of FASTQs created by enclave
    LG_BATCH_SIZE = 1000, #Serialized exact match batches 
    READ_BATCH_SIZE = 1000, #How many reads client sends at once
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
    REF_LENGTH = 48932067, #Length of FASTA sequence
    READ_LENGTH = 150,  #Length of individual FASTQ reads
    SERIALIZED_READ_SIZE = 350, #Length of a protobuf message read
)

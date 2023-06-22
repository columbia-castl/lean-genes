
global_settings = dict(
    redis_port = 6379,
    redis_ip = '127.0.0.1',
)

#IP addresses refer to the machines that each component is connecting to, and not itself
#Currently, the pubcloud's IP is misleadingly named "server_ip"
client_settings = dict(
    server_ip = '127.0.0.1',
    pmt_port = 4445,
    read_port = 4444,
    result_port = 4446,
    debug = False,
    write_ipmt = False,
    interactive_post_proc = True
    #results_threads = 11
)

pubcloud_settings = dict(
    enclave_ip = '0.0.0.0',
    client_ip = '127.0.0.1',
    read_port = 4444,
    pmt_client_port = 4445,
    result_port = 4446,
    unmatched_port = 5006,
    bwa_port = 5007,
    only_indexing = False,
    debug = False
)

enclave_settings = dict(
    server_ip = '0.0.0.0',
    vsock_port = 5006,
    #If this path isn't empty (i.e. BWA is on PATH), make sure it ends with /"
    bwa_path = "../bwa/",
    bwa_port = 5007,
    bwa_index_exists = True,
    separate_hashing = True,
    only_indexing = False,
    write_pmt = False,
    enable_bwa_pmt = True,
    hashing_progress_indicator = 1000000,
    debug = False
)

secret_settings = dict(
    #Placeholder for key shared w/ client and enclave
    perm_seed = 7
)

leangenes_params = dict(
    BWA_BATCH_SIZE = 100000, #Length of FASTQs created by enclave
    LG_BATCH_SIZE = 10000, #Serialized exact match batches 
    READ_BATCH_SIZE = 10000, #How many reads client sends at once
    AES_BLOCK_SIZE = 16,
    CRYPTO_MODE = "debug",
    disable_exact_matching = True,
    nitro_enclaves = False
)

#CHR21 parameters 
#ref_length = 35106643 
#read_length = 151
#serialized = 351

#CHR21 not preproc
#    REF_LENGTH = 48932067, #Length of FASTA sequence
#    READ_LENGTH = 150,  #Length of individual FASTQ reads
#    SERIALIZED_READ_SIZE = 350, #Length of a protobuf message read

#Sample testing parameters
#ref_length = 100
#read_length = 15
#serialized = 69
genome_params = dict(
    REF_LENGTH = 48932067, #Length of FASTA sequence
    READ_LENGTH = 150,  #Length of individual FASTQ reads
    SERIALIZED_READ_SIZE = 350, #Length of a protobuf message read
)

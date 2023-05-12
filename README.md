# leangenes

The code in this repository enables privacy-preserving DNA sequence alignment using BWA and a throughput-increasing shim using exact matching that together we call Lean Genes.

As of right now, dependencies + versions are tracked (loosely, TODO) in requirements-unofficial.txt

## SETUP

- Make sure dependencies are installed from requirements-unofficial.txt
- Use the Makefile to generate the Python protobuf classes for message passing between the scheme's components by simply typing ``make``. If successful this should generate a file called ``reads_pb2.py``
- Once you have done this, you can run the three separate components of the scheme and set them up using the following scripts in the ``src`` folder.

## ``src`` folder

##### Configuration
`` aligner_config.py `` 
This script is used to configure the remaining components of the scheme. Parameters are relatively self-explanatory from their names and are generally separated into global constants needed by all the scripts,
parameters specific to each component (client, public cloud, enclave cloud), and parameters specific to the genome that is being worked with. Parameters are designed to promote flexibility by allowing the scheme to be 
run on a single machine (by setting all IP addresses to 127.0.0.1 for example) or to be run on 3 completely separate machines.
Note that each component has a set of parameters specific to it that you should verify for your use case -- for example the `aligner_cloud.py` component uses the dict `pubcloud_settings` for ports and IPs that it uses whereas `aligner_enclave.py` uses the dict `enclave_settings`, and in this sense the IP addresses are relative per-component. If you are testing with `aligner_enclave` and `aligner_cloud` on different machines, for example, `aligner_enclave` will never use the `pubcloud_settings` and `aligner_cloud` will never use `enclave_settings`.

##### Enclave Cloud Component
`` aligner_enclave.py ``
This component can be used to simulate or actually be run within a trusted enclave cloud component associated with or connected to a public cloud component.
Its responsibilities include generation of a secure permutation, a sliding hash window of the entire FASTA that is sent to a redis db being run by the public cloud, and a 
server-type component that receives not exactly-matched reads from the public cloud component, batches them into FASTQ files, and dispatches them to be run by BWA.

###### BWA
If you want to use a pre-existing copy of BWA with `lean-genes`, ensure that the configuration file points to where your BWA copy is installed, unless it is on the system PATH, in which case you could indicate this with the empty string. Otherwise, the `install_dependencies.sh` includes installation of BWA as a subtask of its functionality.

###### BWA-MEMe
`lean-genes` makes use of an extension to BWA that encrypts output sequences with AES and conceals its output positions using a secure permutation so that new cloud technologies allow the full read-mapping task to take place in the cloud. To make use of this, `lean-genes` applies a patch to BWA that is stored in the `bwa_patch` folder. You can take care of this process automatically by running `install_dependencies.sh`.

###### Running the enclave on its own machine
To run `aligner_enclave.py`, simply enter this command into the terminal
 `` python3 aligner_enclave.py <path to FASTA> ``
 
###### Running the enclave in a Docker container
You can package the enclave component to run in a Docker container by running the `docker_setup.sh` script in the `docker/` folder. The output is a docker image. It assumes that you already have Docker installed on your system and working. To do this consult the official Docker documentation. When you run the Docker container (which will be called `lean_genes:v1`) use the following command to ensure the public cloud host can communicate with the containerized enclave component:

`` docker run --network="host" lean_genes:v1 ``

It is the responsibility of the user to configure the right IP addresses in `aligner_config.py`. Using `0.0.0.0` works for Docker containers.

###### Running the enclave in an AWS Nitro Enclave
`lean-genes` can perform full cloud alignment by using BWA-MEMe within an AWS Nitro Enclave (or a Google Confidential VM). To make use of AWS Nitro Enclaves, set the `nitro_enclaves` parameter to `True` within `aligner_config.py`. Then, follow the process of packaging code to run in an AWS Nitro Enclave:

1) See the previous section to package the enclave component into a Docker container
2) Install the AWS Nitro Enclaves CLI (consult AWS' documentation on this)
3) Build the Nitro Enclave from the Docker image:
`` nitro-cli build-enclave --docker-uri lean_genes:v1 --output-file lean_genes.eif``
4) The previous step produces an enclave image file than can be run with:
`` nitro-cli run-enclave --cpu-count <x> --memory <y> --enclave-cid 16 --eif-path lean_genes.eif ``
Optionally, you can append `--debug-mode` to this command to be able to check the enclave with a console.

###### Indexing configurations for `aligner_enclave`
`aligner_enclave` has configuration options to increase the number of different ways that you can supply `aligner_cloud` with the Lean Genes index.
The `separate_hashing` option determines whether or not you want/need the enclave script to perform the Lean Genes indexing process. 
Say for example that you already have generated the index and stored it as an `.rdb` file, you would want to skip indexing and set this option to be `False`, whereas if you have never generated the Lean Genes index, you would set it to be `True`.

Additionally, `aligner_enclave` has the `bwa_index_exists` option. If you haven't generated the BWA index for your reference yet, you can set this option to `True` in order to trigger your copy of BWA creating the index it needs to allow it to function correctly once `aligner_enclave` begins to receive the unmatched reads.

##### Public Cloud Component
`` aligner_cloud.py ``
This component can be used to simulate or actually be run within an untrusted public cloud. Its responsibilities include setting up a redis server that will serve as a database for keyed hashes of reads for a genome.
It receives encrypted reads in a protobuf format, searches for exact matches via the redis DB, and dispatches unmatched reads into the trusted enclave to be run by BWA.

If you would like to run this script PURELY TO COLLECT AN INDEX, there is a config option called `only_indexing` in the `dict` `pubcloud_settings` in `aligner_config.py`

###### Running it
To run it, simply enter this command into the terminal
 `` python3 aligner_cloud.py``

###### Post-run
After running the public cloud component, there will be a redis DB file. If you wish to remove it enter the command `` make clean ``. However, it is convenient to keep a copy of this file because it allows you to bypass index generation for a given reference and permutation.

##### Client-side Component
`` aligner_client.py ``
This component can be used to simulate/be run to represent the client side of the privacy preserving read-mapping scheme.
Its main responsibilities include processing fastq files into a protobuf message format that can be used to quickly search for exact matches on the public cloud component, then receiving results from the pubcloud/enclave cloud that can be interpreted safely into SAM files.

###### Running it
To run it, simply enter this command into the terminal
 `` python3 aligner_client.py``
 
 This script runs interactively with different commands. To see them, type "help" after initially running the script.
If you do not wish to run the script interactively, provide the FASTQ of reads you wish to map as a command line argument, i.e.:
 `` python3 aligner_client.py my_fastq.fastq ``

To use the post-processor, compilation command is:
`` make post_proc ``

##### ``test_data`` folder
This folder contains some example FASTQ and FASTA files that were used to verify the functionality of this tool before scaling it up to full chromosomes and genomes, as well as some example SAM results created by running the tool previously in tests, etc. for verification.

##### ``src/analysis`` folder
This folder contains some useful scripts that can perform useful functions like tell you how many reads in a SAM were mapped by lean-genes vs BWA, verify that a SAM from BWA alone has the same results as a SAM including results from lean-genes, and telling you the length of reads/serialized reads in a FASTQ.

#### FAQs 
1. When running, make sure you check that you have a new enough version of redis
2. Make sure you have the right version of the protobuf compiler ``protoc``
3. Make sure you have built the protobuf message format classes (with `make proto`)
4. Make sure that any firewalls have been configured to work with the ports you assign in the configuration file
5. Ensure that your cloud resources are large enough to support the genome you want to work with. This scheme is designed to tradeoff cloud space for decreased runtime and increased throughput, so don't expect the scheme, especially the indexing portion, to work well with limited resources.

The code in this repository enables privacy-preserving DNA sequence alignment using BWA and a throughput-increasing shim using exact matching that together we call Lean Genes.

As of right now, dependencies are tracked (loosely, TODO) in requirements-unofficial.txt

**SETUP**

- Make sure dependencies are installed from requirements-unofficial.txt
- Use the Makefile to generate the Python protobuf classes for message passing between the scheme's components by simply typing ``make``. If successful this should generate a file called ``reads_pb2.py``
- Once you have done this, you can run the three separate components of the scheme and set them up using the following scripts in the ``src`` folder.

**src folder**

** aligner_config.py ** 
This script is used to configure the remaining components of the scheme. Parameters are relatively self-explanatory from their names and are generally separated into global constants needed by all the scripts,
parameters specific to each component (client, public cloud, enclave cloud), and parameters specific to the genome that is being worked with. Parameters are designed to promote flexibility by allowing the scheme to be 
run on a single machine (by setting all IP addresses to 127.0.0.1 for example) or to be run on 3 completely separate machines.

** aligner_enclave.py **
This component can be used to simulate or actually be run within a trusted enclave cloud component associated with or connected to a public cloud component.
Its responsibilities include generation of a secure permutation, a sliding hash window of the entire FASTA that is sent to a redis db being run by the public cloud, and a 
server-type component that receives not exactly-matched reads from the public cloud component, batches them into FASTQ files, and dispatches them to be run by BWA.

To run it, simply enter this command into the terminal
 `` python3 aligner_enclave.py <path to FASTA> ``

** aligner_cloud.py **
This component can be used to simulate or actually be run within an untrusted public cloud. Its responsibilities include setting up a redis server that will serve as a database for keyed hashes of reads for a genome.
It receives encrypted reads in a protobuf format, searches for exact matches via the redis DB, and dispatches unmatched reads into the trusted enclave to be run by BWA.

To run it, simply enter this command into the terminal
 `` python3 aligner_cloud.py``

** aligner_client.py **
This component can be used to simulate or actually be run to represent the client side of the privacy preserving read-mapping scheme.
Its main responsibilities include processing fastq files into a protobuf message format that can be used to quickly search for exact matches on the public cloud component, then receiving results from the pubcloud/enclave cloud that can be interpreted safely into SAM files.

To run it, simply enter this command into the terminal
 `` python3 aligner_client.py``
 
 This script runs interactively with different commands. To see them, type "help" after initially running the script.

**test_data folder**
This folder contains some example FASTQ and FASTA files that were used to verify the functionality of this tool before scaling it up to full chromosomes and genomes.

** FAQs **
- When running, make sure you check that you have a new enough version of redis
- Make sure you have the right version of the protobuf compiler ``protoc``
- Make sure you have built the protobuf message format classes
- Make sure that any firewalls have been configured to work with the ports you assign in the configuration file
- Ensure that your cloud resources are large enough to support the genome you want to work with. This scheme is designed to tradeoff cloud space for decreased runtime and increased throughput.

**TODOS**
Explaining PMT functionality, updating all global variables into config.
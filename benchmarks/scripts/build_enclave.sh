docker build $1/ -t $1
nitro-cli build-enclave --docker-uri $1:latest --output-file $1.eif
nitro-cli run-enclave --cpu-count 26 --memory 150512 --enclave-cid 16 --eif-path $1.eif --debug-mode

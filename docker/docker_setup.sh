#!/bin/bash

cp ../src/aligner_prototype.py .
python3 ../src/helper_scripts/ref_gen.py 100 small_ref 1
docker build -t lean_genes:v1 .
docker run lean_genes:v1

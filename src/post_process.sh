#!/bin/bash

cat lg_out_*.sam > lg_out.sam
rm lg_out_*.sam

cat enclave_*.bytes > enclave.bytes
rm enclave_*.bytes

./post_proc

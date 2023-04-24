#!/bin/bash

head -n3 lg_out_0.sam > lg_out.sam
sed -i '1,3d' lg_out_*.sam
cat lg_out_*.sam >> lg_out.sam
rm lg_out_*.sam

cat enclave_*.bytes > enclave.bytes
rm enclave_*.bytes

./post_proc

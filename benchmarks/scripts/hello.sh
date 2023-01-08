#!/bin/sh
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

echo "started shit"s

sleep 40

./install_bwa.sh
#./run_bwa.sh
count=1
while true; do
    printf "[%4d] $HELLO\n" $count
    count=$((count+1))
    sleep 5000
done

#!/bin/sh

mkdir -p logs
./j2735_decoder.py -d -m -s -B -O "logs" $@


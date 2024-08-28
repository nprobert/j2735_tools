#!/bin/sh

rm -rf logs/*
mkdir -p logs
for i in tests/*.pcap tests/*.pcapng
do
  ./j2735_decoder.py -d -m -s -B -O "logs" $i
done

ls -l logs

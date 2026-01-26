#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  1 14:28:09 2021

@author: neal
"""

import os
import sys, getopt
import signal
import re

class_path = os.path.dirname(os.path.abspath(__file__)) + '/classes'
if os.path.isdir(class_path):
  sys.path.append(class_path)
  sys.path.append(class_path + '/j2735')

from j2735_logcore import J2735_TOOL_VERSION, J2735_FILE_VERSION
from j2735_decode import j2735_decode

# keep the decoder warnings quiet (usually unknown exceptions)
from pycrate_asn1rt import asnobj
asnobj.ASN1Obj._SILENT = True

###############################################################################
# MAIN
###############################################################################

opt_list = "bcdf:hmo:su:v:BO:"

help_text = """\t-b        Split BSMs to file by ID
\t-c        Converting BSM enabled
\t-d        Debugging enabled to debug.txt
\t-f        Filter by message name, comma seperated list
\t-h        Help
\t-m        Binary MAP output in J2735 UPER format
\t-o <offs> UDP offset to data in bytes
\t-s        Split MAPs/SPATs to file by ID in JSON
\t-u <port> UDP port
\t-v vid    BSMs extracted by vehicle id
\t-B        Use PCAP file base name as base path to output directory
\t-O <path> Path to output base directory
\t Creates JSON and KML (MAP) files with metadata.txt to <path>/<base>
"""

def main(argv):
  output = ""
  convert = 0
  debug_on = 0
  msg_list = ""
  bin_maps = 0
  split_bsm = 0
  split_map = 0
  vehicle_id = 0
  udp_port = 0
  offset_bytes = 0
  basepath= 0
  
  print("Python3 J2735-%s PCAP Decoder V%s" % (J2735_FILE_VERSION,J2735_TOOL_VERSION))
  
  try:
    opts, args = getopt.getopt(argv, opt_list, [])
  except getopt.GetoptError:
    print("j2735_decoder.py " + opt_list + " <input PCAP files>")
    sys.exit(2)
  
  for opt, arg in opts:
    if opt in ('-h'):
      print("j2735_decoder.py " + opt_list + " <input PCAP files>")
      print(help_text)
      sys.exit()
    elif opt in ('-b'):
      print("\tSplit BSMs to file by ID")
      split_bsm = 1
    elif opt in ('-c'):
      print("\tConverting BSM enabled")
      convert = 1
    elif opt in ('-d'):
      print("\tDebugging enabled")
      debug_on = 1
    elif opt in ('-f'):
      print("\tFiltered output")
      msg_list = arg
    elif opt in ('-m'):
      print("\tBinary MAP output")
      bin_maps = 1
    elif opt in ('-o'):
      offset_bytes = int(arg)
    elif opt in ('-s'):
      if split_map == 0:
        print("\tSplit MAPs/SPATs to file by ID")
        split_map = 1
      elif split_map == 1:
        print("\tSeparate MAPs from SPATs to file")
        split_map = 2        
    elif opt in ('-u'):
      udp_port = int(arg)
    elif opt in ('-v'):
      vehicle_id = int(arg)
    elif opt in ('-B'):
      basepath = 1
    elif opt in ('-O'):
      output = arg
    else:
      print("Argument error!")
      print("j2735_decoder.py " + opt_list + " <input PCAP files>")
      sys.exit()

  # allocate
  decode = j2735_decode()

  for arg in args: 
    # output directory
    if output == "":
      decode.logdir = "."
    else:
      decode.logdir = output
    decode.basepath = basepath

    # options
    decode.convert = convert
    decode.debug_on = debug_on
    if msg_list != "":
        decode.msg_filter = msg_list.split(',')
    else:
        decode.msg_filter = []
    decode.bin_maps = bin_maps
    decode.splitbsms = split_bsm
    decode.splitmapspat = split_map
    decode.bsm_hv_id = vehicle_id
    decode.udp_port = udp_port
    decode.offset_bytes = offset_bytes
    break
 
  # create log
  for arg in args:
    # use basename of file for output
    decode.log_make(arg)
    print("Input PCAP File: %s" % (arg))
    print("Output JSON File: %s" % (decode.logfile))

    # input file types
    if re.search('.json$', arg, re.IGNORECASE):
      decode.parse_json_file(arg)
    elif re.search('.log$', arg, re.IGNORECASE):
      decode.parse_json_file(arg)
    elif re.search('.pcap$', arg, re.IGNORECASE):
      decode.parse_pcap_file(arg)
    elif re.search('.pcapng$', arg, re.IGNORECASE):
      decode.parse_pcap_file(arg)
    elif re.search('.bin$', arg, re.IGNORECASE):
      decode.parse_binfile(arg)
    elif re.search('.uper$', arg, re.IGNORECASE):
      decode.parse_binfile(arg)
    elif re.search('.hex$', arg, re.IGNORECASE):
      decode.parse_hexfile(arg)
    else:
      print("Unknown file type: ", arg)
      sys.exit()
 
    decode.print_report()

def signal_handler(signal, frame):
  # your code here
  print("Aborted!")
  sys.exit(2)

# catch ^C or kill signal
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
  main(sys.argv[1:])

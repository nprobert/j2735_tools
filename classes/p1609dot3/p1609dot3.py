#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  6 08:50:18 2021

@author: neal
"""

#
# constants
#
PSID_VEHICLE      = 0x20
PSID_CORRECTIONS  = 0x80
PSID_INTERSECTION = 0x82
PSID_TRAVELER     = 0x83
PSID_EMERGENCY    = 0x85
PSID_WAVE_ADVERT  = 0x87
PSID_CV_PILOT_MIN = 0x204090
PSID_CV_PILOT_MAX = 0x204097
PSID_TRAFFIC_SIGNAL = 2113685
PSID_ROAD_MAPPING = 2113687

def wsmp_parse_length(pkt):
  val = pkt[0] & 0xff
  leng = 1
  if val & 0x80:
    val = (val & 0x7f) << 8
    val = (val | pkt[1]) & 0xff
    leng += 1
  return (val, leng)

# WSMP only
def wsmp_parse_pcoded(pkt):
  act = pkt[0] & 0xff
  index = 1
  psid_len = 0
  
  # lifted and modified from Wireshark
  if (act & 0xF0) == 0xF0:
    psid_len = 255
  elif (act & 0xF0) == 0xE0:
    psid_len = 4
  elif (act & 0xE0) == 0xC0:
    psid_len = 3
  elif (act & 0xC0) == 0x80:
    psid_len = 2
  elif (act & 0x80) == 0x00:
    psid_len = 1
  
  # slurp in big endian order
  val = act
  i = psid_len - 1
  while i:
    val = val << 8
    val = val | (pkt[index] & 0xff)
    index += 1
    i -= 1
  
  # masks and what not
  psid = 0
  if psid_len == 1:
    psid = val;
  elif psid_len == 2:
    psid = (val & ~0x8000) + 0x80
  elif psid_len == 3:
    psid = (val & ~0xc00000) + 0x4080
  elif psid_len == 4:
    psid = (val & ~0xe0000000) + 0x204080
  
  return (psid, psid_len)

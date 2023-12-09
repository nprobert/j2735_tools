#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  6 08:40:03 2021

@author: neal
"""

def oer_parse_length(pkt):
  val = pkt[0]
  leng = 1
  if val & 0x80:
    n = val & 0x7f
    val = 0
    while n:
      val = val << 8
      val = val | (pkt[leng] & 0xff)
      leng += 1
      n -= 1

  return (val, leng)

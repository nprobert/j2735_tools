#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 21 07:31:23 2021

@author: neal
"""

#from math import *
from datetime import datetime
#from time import time, strftime

import json
import pandas as pd

from j2735_mf import *

csv_fields = ['Timestamp', 'Direction', 'Message_id', 'P1609dot2_flag', 'Message_JSON']

class j2735_file:
  def __init__(self):
    self.df = 0

  def timestamp_to_datetime(self):
    # convert timestamp into datetime
    if 'Timestamp' in self.df:
      self.df['Datetime'] = pd.to_datetime(self.df['Timestamp'], unit='ms')
 
  def open_json(self, json_file):
    self.df = pd.read_json(json_file, lines=True)

    # done
    return self.df
  
  def open_jv2x(self, csv_file):
    self.df = pd.read_csv(csv_file, sep=",", quotechar="'",
                          skipinitialspace=True, parse_dates=False,
                          converters={'Message_JSON':json.loads},
                          dtype={'Timestamp':'UInt64', 'Direction':'string', 'Message_id':'Int8', 'P1609dot2':'Int8'})

    self.df.rename(columns = {'Message_JSON':'Message'}, inplace = True)

    self.timestamp_to_datetime()
   
    # done
    return self.df

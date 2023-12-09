
from enum import Enum
import json
import math
from time import time

#
# generic message base class
#
class j2735_msg:
  def __init__(self):
    self.data = {}
    self.timestamp = 0    # msec

  def get_data(self):
    return self.data

  def set_data(self, dat):
    # message data in python
    self.data = dat
    return self.data
  
  def get_time(self, ts):
    return self.timestamp

  def set_time(self, ts):
    self.timestamp = ts
  
  def decode_json(self, js):
    self.data = json.load(js)
    return self.data

  def encode_json(self):
    kap = json.dumps(self.data, indent=None, separators=('.', '='))
    return ''.join(kap.split())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  1 14:28:09 2021

@author: neal
"""

from struct import unpack
import json

#
# DVI Message (see DVI_Packet.h)
#
class DVI:
  def __init__(self):
    # DVI data (do not access directly)
    self.msg = 0
    self.app = 0
    self.sub = 0  # V2I only
    self.thr = 0
    self.lvl = 0
    self.tid = 0
    self.rng = 0
    self.rngr = 0
    self.ttc = 0
    # roy codes
    self.pos = 0
    self.hv = 0
    self.rv = 0
    self.ind = 0
    # other
    self.speed = 0
    self.dist = 0
    self.dire = 0
    self.phase = 0
    self.lane = 0
    self.nlanes = 0
    self.length = 0
    self.closed = 0

  def load_data(self, data): 
    self.msg = data['msg_id']
    self.app = data['app_id']
    self.sub = data['sub_id']
#    self.thr = data['threat_class']
    self.lvl = data['threat_level']
    self.tid = data['threat_id']
    self.rng = data['range']
    self.rngr = data['range_rate']
    self.ttc = data['time2collision']
    self.pos = data['roy_code_pos']
    self.hv = data['roy_code_hv']
    self.rv = data['roy_code_rv']
    self.ind = data['roy_code_ind']

  # for new apps, convert to python object
  def dump_data(self):
    # convert to python object
    data = {}
    # V2V
    data['msg_id'] = self.msg
    data['app_id'] = self.app
    data['sub_id'] = self.sub
#    data['threat_class'] = self.cls
    data['threat_level'] = self.lvl
    data['threat_id'] = self.tid
    data['range'] = self.rng
    data['range_rate'] = self.rngr
    data['time2collision'] = self.ttc
    data['roy_code_pos'] = self.pos
    data['roy_code_hv'] = self.hv
    data['roy_code_rv'] = self.rv
    data['roy_code_ind'] = self.ind
    return data

  # decode to python object from json
  def decode_json(self, js):
    data = json.loads(js)
    if data:
      self.load_data(data)
    return data
  
  # encode to json
  def encode_json(self):
    return json.dumps(self.dump_data())
    
  def decode_old(self, data):
    # DENSO WSU DVI CAN message over UDP
    if len(data) == 8:
      # common
      self.msg = 2
      self.sub = 0
      self.app = data[0]
      self.dist = (data[1] << 8 | data[2]) * 1.0  # meters
      self.lvl = (data[3] >> 6) & 3
      # V2I-SA apps
      if self.app==1:      # RLVW
        self.dire = (data[3] >> 3) & 7
        self.phase = data[3] & 3
        self.lane = (data[5] >> 4) & 15
        # skip attrs
        self.flash = (data[5] >> 3) & 1
        self.time = data[6] & 0x3f
      elif self.app==2:    # CSW-L, CSW-R
        self.sub = ((data[3] >> 5) & 1) + 1
        cause = (data[4] >> 6) & 3
        if cause == 1:      # slippery
          self.sub = 3
        elif cause == 2:    # blockage (stop)
          self.sub = 5
        elif cause == 3:    # visibility (fog)
          self.sub = 4
      elif self.app==3:    # RSZW
        # needs to be updated (CAN output v1.2)
        lvl2 = (data[3] >> 4) & 3
        self.lane = (data[4] >> 4) & 15
        self.nlanes = data[4] & 15
        self.length = data[5] * 10.0
        self.closed = data[6]
        self.speed = data[7]
        if self.lvl or lvl2:
          # default reduce speed
          self.sub = 1
          if self.lvl2 and self.closed:
            # lane closing
            self.lvl = lvl2
            self.sub = 4
          elif self.lvl:
            # work or school zone?
            self.zone = (data[3] >> 3) & 1
            self.sub = 2 + self.zone
          else:
            self.app = 0
            self.lvl = 0
      elif self.app==4:     # SSGA
        # 2 way or 4 way?
        self.sub = 0
      else:
        self.app = 0
        self.lvl = 0
        # bump to new levels used by DVI
        if self.app and self.lvl:
          if self.lvl==2:
            self.lvl = 3
            self.lvl = self.lvl + 1
          else:
            self.lvl = 0
    elif len(data) == 22:
      # old DVI Message
      self.msg, self.app, self.thr, self.lvl, self.tid, self.rng, self.rngr, self.ttc, self.pos, self.hv = unpack('!BBBBLfffBB', data[0:22])
    elif len(data) >= 24:
      # new DVI Message
      self.msg, self.app, self.thr, self.lvl, self.tid, self.rng, self.rngr, self.ttc, self.pos, self.hv, self.rv, self.ind = unpack('!BBBBLfffBBBB', data[0:24])
    else:
      pass
    return (self.msg, self.app, self.thr, self.lvl, self.tid, self.rng, self.rngr, self.ttc, self.pos, self.hv, self.rv, self.ind)
  
  # for old apps only
  def values(self):
    return (self.msg, self.app, self.thr, self.lvl, self.tid, self.rng, self.rngr, self.ttc, self.pos, self.hv, self.rv, self.ind)



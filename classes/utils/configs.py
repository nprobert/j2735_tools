#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 10:26:56 2021

@author: neal
"""

import os
import yaml

class ConfigurationFile():
  def __init__(self, app_path):
    self.app_file = app_path
    self.cfg_path = os.path.dirname(os.path.realpath(app_path))
    (base, ext) = os.path.splitext(os.path.basename(app_path))
    self.app_name = base
    self.cfg_file = self.app_name + ".yaml"    
    self.use_path = self.cfg_file
    self.config = []
    self.paths = []
    self.paths.append(".")             # local first
    # grab from env
    if 'NTCNA_PYVEHICLE_PATH' in os.environ:
      self.paths.append(os.environ['NTCNA_PYVEHICLE_CFGPATH'].split(':'))
    self.paths.append(self.cfg_path)  # program location

  def find_config(self):
    for path in self.paths:
      cfg = path + "/" + self.cfg_file
      if os.path.isfile(cfg):
        self.use_path = cfg
        return 1
    print("Config file not found:", self.cfg_file)
    return 0

  def read_config(self):
    if self.find_config():
#      print(self.app_file, " using configuration file: ", self.use_path)
      with open(self.use_path) as f:
        self.config = yaml.load(f, Loader=yaml.FullLoader)
        f.close()
    else:
      self.config = []
    return self.config

  def write_config(self, config):
    self.config = config
    with open(self.use_path, 'w') as f:
      f.write(yaml.dump(config))
      f.close()
  
  def get_config(self, name):
    if name in self.config:
      return self.config[name]
    return ""

  def set_config(self, name, val):
    self.config[name] = val

  def path_append(self, path):
    if os.path.exists(path):
      self.paths.append(path)
    else:
      print("Path not found: ", path)

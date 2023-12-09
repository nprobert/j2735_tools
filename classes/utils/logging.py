import sys
from time import strftime, time
import csv
import json

def log_genname(dire="", basename="log-", ext="log"):
  dirname = ""
  if dire != "":
    dirname = dire + "/"
  return dirname + basename + strftime("%Y%m%d-%H%M%S.") + ext
#
# Text logging
#
class LOGlog():
  def __init__(self):
    self.filename = ""
    self.handle = 0
    self.lineno = 0
 
  def make(self, dire="", basename="log-", ext="log"):
    if self.handle:
      self.handle.close()
    self.lineno = 0
    self.filename = log_genname(dire, basename, ext)
    self.handle = open(self.filename, 'a')
    return self.filename

  def create(self, file):
    if self.handle:
      self.handle.close()
    self.lineno = 0
    self.filename = file
    self.handle = open(self.filename, 'a')
    return self.filename

  def open(self, filename):
    if self.handle:
      self.handle.close()
    self.filename = filename
    self.handle = open(filename, 'r')

  def header(self, str):
    self.handle.write(str)
    
  def write(self, str):
    self.lineno = self.lineno + 1
    self.handle.write(str + "\n")
  
  def read(self):
    self.lineno = self.lineno + 1
    return self.handle.read()
    
  def close(self):
    self.handle.close()
  
  def lines(self):
    return self.lineno

#
# CSV logging
#
class CSVlog(LOGlog):
  def __init__(self):
    super().__init__()
    self.header = ""
    
  def make(self, dire="", basename="log-"):
    return super().make(dire, basename, "csv")

  def open(self, filename):
    self.reader = csv.reader(super().filename)
    super().open(filename)
  
  def read(self):
    return self.reader.next(super().handle)
  
  def readall(self, csvfile):
    data = csv.reader(csvfile)
    csv.close()
    return list(data)

#
# JSON logging
#
class JSONlog(LOGlog):
  def __init__(self, quoted=0):
    super().__init__()
    self.quoted = quoted
  
  def make(self, dire="", basename="log-", ext="json"):
    return super().make(dire, basename, ext)
  
  def open(self, filename):
    super().open(filename)

  def header(self, str):
    super().header(str)
  
  def write(self, data):
    if self.quoted:
      super().write("'" + json.dumps(data, separators=(',', ':')) + "'")
    else:
      super().write(json.dumps(data, separators=(',', ':')))
  
  def read(self, ):
    return json.loads(super().read())

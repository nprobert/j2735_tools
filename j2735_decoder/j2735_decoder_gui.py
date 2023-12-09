#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 19 08:08:26 2021

@author: neal
"""

import os
import sys
import time
import yaml
from scapy.all import *

from PySide6 import QtCore, QtGui, QtWidgets

from MainWindow import Ui_MainWindow

import re

class_path = os.path.dirname(os.path.abspath(__file__)) + '/classes'
if os.path.isdir(class_path):
  sys.path.append(class_path)
  sys.path.append(class_path + '/j2735')

from utils.configs import *
from j2735_logcore import J2735_TOOL_VERSION
from j2735_decode import j2735_decode

# keep the decoder warnings quiet (usually unknown exceptions)
from pycrate_asn1rt import asnobj
asnobj.ASN1Obj._SILENT = True

cfg = ConfigurationFile(__file__)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
  def __init__(self, *args, obj=None, **kwargs):
    super(MainWindow, self).__init__(*args, **kwargs)
    self.setupUi(self)

class ConvertWindow(MainWindow):
  def __init__(self, *args, obj=None, **kwargs):
    super(ConvertWindow, self).__init__(*args, **kwargs)

    # titles with version#
    self.setWindowTitle("NTCNA V2X: J2735 Decoder V" + J2735_TOOL_VERSION)
    self.lblTitle.setText(self.lblTitle.text() + "V" + J2735_TOOL_VERSION)

    # button connections
    self.exitButton.clicked.connect(self.exit_button)
    self.btnFile.clicked.connect(self.file_dialog)
    self.btnDir.clicked.connect(self.dir_dialog)
    self.convertFile.clicked.connect(self.file_convert)
    self.chkSplitMaps.clicked.connect(self.chk_map_split)
    self.chkSeparateMaps.clicked.connect(self.chk_map_separate)
    self.chkSplitBsms.clicked.connect(self.chk_bsm_split)
    self.chkConvertData.clicked.connect(self.chk_bsm_convert)
    self.progressBar.setValue(0)

    # text
    self.filename = ""
    self.filenames = []
    self.dirname = ""
    self.outputDir.setText(self.dirname)
    
  def closeEvent(self, event):
    event.accept()
    sys.exit(0)

  def chk_map_split(self):
    self.chkSeparateMaps.setChecked(0)

  def chk_map_separate(self):
    if not self.chkSplitMaps.isChecked():
      self.chkSeparateMaps.setChecked(0)
    
  def chk_bsm_split(self):
    self.chkConvertData.setChecked(0)
  
  def chk_bsm_convert(self):
    if not self.chkSplitBsms.isChecked():
      self.chkConvertData.setChecked(0)
  
  def file_dialog(self):
    filedialog = QtWidgets.QFileDialog(self)
    filedialog.setDirectory(QtCore.QDir.currentPath())
    filedialog.setDefaultSuffix("pcap")
    filedialog.setNameFilter("PCAP (*.pcap);; PCAPNG (*.pcapng);; Kapsch (*.log);; Hex (*.hex);; all (*.*)")
    filedialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
    selected = filedialog.exec()
    if selected:
      filenames = filedialog.selectedFiles()
      files = []
      for file in filenames:
        file = os.path.basename(file)
        files.append(file)
      self.inputFile.setText(', '.join(files))
      self.filename = filenames[0]
      self.filenames = filenames
  
  def dir_dialog(self):
    dirdialog = QtWidgets.QFileDialog(self)
    dirdialog.setDirectory(QtCore.QDir.currentPath())
    dirdialog.setDefaultSuffix("pcap")
    dirdialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dirdialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
    selected = dirdialog.exec()
    if selected:
      dirname = dirdialog.selectedFiles()[0]
      self.outputDir.setText(dirname)
      self.dirname = dirname

  def parse_pcap_file_gui(self, decode, file): 
    decode.log_write("PCAP Input: " + file)
    decode.log_debug("Parsing PCAP File: " + file)
    decode.count = 0
    self.progressBar.setValue(0)

    # actually count the packets
    packet_count = 0
    for (pkt_data, pkt_metadata,) in RawPcapNgReader(file):
      packet_count += 1
    if packet_count == 0:
      packet_count = size // 168 # hack which uses 156 for est. packet size
    size = os.stat(file).st_size
    
    # parse all the packets
    for (pkt_data, pkt_metadata, ) in RawPcapNgReader(file):
      # timestamp
      decode.parse_pcap_time(pkt_metadata)

      # PCAP data
      decode.parse_pcap_packet(pkt_data)
      self.progressBar.setValue(int(float(decode.count)/float(packet_count) * 100.0))
    
    decode.log_write("\tcontained %u useful/%u total packets (%u bytes average)" % (decode.count, packet_count, size/packet_count))

  def file_convert(self):
    dialog = QtWidgets.QMessageBox()
    dialog.setIcon(QtWidgets.QMessageBox.Information)
    dialog.setWindowTitle("Converting Data File(s)")
    dialog.setText("File conversions in progress")
    
    for file in self.filenames:
      self.filename = file
      
      # allocate
      decode = j2735_decode()

      # create log
      decode.logdir = self.dirname
    
      # options
      if self.chkDebugLog.isChecked():
        decode.debug_on = 1
      if self.chkSplitBsms.isChecked():
        decode.splitbsms = 1
      if self.chkConvertData.isChecked():
        decode.convert = 1
      if self.chkBinMaps.isChecked():
        decode.bin_maps = 1
      if self.chkSplitMaps.isChecked():
        decode.splitmapspat = 1
      if self.chkSeparateMaps.isChecked():
        decode.splitmapspat = 2

      decode.log_make(self.filename)
      self.outputFile.setText(os.path.basename(decode.logfile))
      self.convertFile.hide()
      self.repaint()

      if re.search('.json$', self.filename, re.IGNORECASE):
        decode.parse_json_file(self.filename)
      elif re.search('.log$', self.filename, re.IGNORECASE):
        decode.parse_json_file(self.filename)
      elif re.search('.pcap$', self.filename, re.IGNORECASE):
        self.parse_pcap_file_gui(decode, self.filename)
      elif re.search('.pcapng$', self.filename, re.IGNORECASE):
        self.parse_pcap_file_gui(decode, self.filename)
      elif re.search('.bin$', self.filename, re.IGNORECASE):
        decode.parse_binfile(self.filename)
      elif re.search('.uper$', self.filename, re.IGNORECASE):
        decode.parse_binfile(self.filename)
      elif re.search('.hex$', self.filename, re.IGNORECASE):
        decode.parse_hexfile(self.filename)
      else:
        dialog.setWindowTitle("File Unrecognized")
        dialog.setText("Cannot parse this file; " + self.filename)
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
        dialog.setDefaultButton(QtWidgets.QMessageBox.Yes)
        dialog.exec()
        continue

      if decode.bsmp_tx_count or decode.bsmp_rx_count:
        self.msgBSMrx.setText(str(decode.bsmp_rx_count))
        self.msgBSMtx.setText(str(decode.bsmp_tx_count))
      else:
        self.msgBSMrx.setText(str(decode.bsm_rx_count))
        self.msgBSMtx.setText(str(decode.bsm_tx_count))
      self.msgMAPrx.setText(str(decode.map_rx_count))
      self.msgSPATrx.setText(str(decode.spat_rx_count))
      self.msgRTCMrx.setText(str(decode.rx_counts[28]))
      self.msgOtherRx.setText(str(decode.other_rx_count))
      self.msgErrorCnt.setText(str(decode.error_count))
      self.msgTotalRx.setText(str(decode.rx_count))
      self.msgTotalTx.setText(str(decode.tx_count))
      self.repaint()

      decode.print_report()

    dialog.setText("Done with file conversions: %u useful packets" % (decode.count))
    dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dialog.setDefaultButton(QtWidgets.QMessageBox.Yes)
    dialog.exec()

    self.convertFile.show()

  def save_config(self):    
    config = {}
    config['input_dir'] = os.getcwd()
    config['output_dir'] = self.dirname
    if self.chkSplitBsms.isChecked():
      config['splitbsms'] = 1
    if self.chkConvertData.isChecked():
      config['convertbsms'] = 1
    if self.chkBinMaps.isChecked():
      config['binarymaps'] = 1
    if self.chkSplitMaps.isChecked():
      config['splitmapspat'] = 1
    if self.chkSeparateMaps.isChecked():
      config['splitmapspat'] = 2
    cfg.write_config(config)

  def exit_button(self):
    self.save_config()
    sys.exit(0)

if __name__ == '__main__':
  app = QtWidgets.QApplication(sys.argv)

  window = ConvertWindow()
  window.show()

  
  config = cfg.read_config()
  if 'output_dir' in config:
     window.dirname = config['output_dir']
     window.outputDir.setText(window.dirname)
  if 'splitbsms' in config:
   if int(config['splitbsms']):
     window.chkSplitBsms.setChecked(1)
  if 'convertbsms' in config:
    if int(config['convertbsms']):
      window.chkConvertData.setChecked(1)
  if 'splitmapspat' in config:
    splitms = int(config['splitmapspat'])
    if splitms == 1:
      window.chkSplitMaps.setChecked(1)
    elif splitms == 2:
      window.chkSplitMaps.setChecked(1)
      window.chkSeparateMaps.setChecked(1)

  ret = app.exec()
  sys.exit(ret)

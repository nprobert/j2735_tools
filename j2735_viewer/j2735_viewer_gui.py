#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 19 08:08:26 2021

@author: neal
"""

import os
import sys
import csv
import yaml
import pprint
import binascii
import subprocess
from struct import unpack
from datetime import datetime
import pynmea2
from pyrtcm import RTCMReader

from PySide6.QtGui import *
from PySide6 import QtCore, QtWidgets

from MainWindow import Ui_MainWindow

import re

class_path = os.path.dirname(os.path.abspath(__file__)) + '/classes'
if os.path.isdir(class_path):
  sys.path.append(class_path)
  sys.path.append(class_path + '/j2735')

from j2735_logcore import J2735_TOOL_VERSION
from j2735_decode import j2735_decode
#from j2735_file import j2735_file
from j2735_mf import *

from utils.configs import *

j2735_names = ['MAP', 'SPAT', 'BSM', 'CSR', 'EVA', 'ICA', 'NMEA', 'PDM', 'PVD',
               'RSA', 'RTCM', 'SRM', 'SSM', 'TIM', 'PSM']
j2735_min = 18
j2735_max = 18 + len(j2735_names)

v2x_names = ['None', 'V2V', 'V2I', '???']
v2v_names = ['None', 'EEBL', 'FCW', 'BSW-L', 'BSW-R',
             'IMA-L', 'LTA', 'IMA-R', 'DNPW', 'CLW',
             'RCTA-L', 'RCTA-B', 'RCTA-R']
v2i_names = ['None', 'RLVW', 'CSW', 'RSZW', 'SSGA', 'SWIW']
lvl_names = ['None','Guidance','Inform','Advisory','Warning','Violation']

cfg = ConfigurationFile(__file__)

##############################################################################
# GUI
##############################################################################

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
  def __init__(self, *args, obj=None, **kwargs):
    super(MainWindow, self).__init__(*args, **kwargs)
    self.setupUi(self)

class ViewerWindow(MainWindow):
  def __init__(self, *args, obj=None, **kwargs):
    super(ViewerWindow, self).__init__(*args, **kwargs)

    # titles with version#
    self.setWindowTitle("NTCNA V2X: J2735 Viewer V" + J2735_TOOL_VERSION)
    self.lblTitle.setText(self.lblTitle.text() + " V" + J2735_TOOL_VERSION)

    # button connections
    self.exitButton.clicked.connect(self.exit_button)
    self.btnFile.clicked.connect(self.file_dialog)
    self.chkBSM.toggled.connect(self.show_records)
    self.chkTX.toggled.connect(self.show_records)
    self.chkRX.toggled.connect(self.show_records)
    self.chkMAP.toggled.connect(self.show_records)
    self.chkSPAT.toggled.connect(self.show_records)
    self.chkRTCM.toggled.connect(self.show_records)
    self.chkPDMPVD.toggled.connect(self.show_records)
    self.chkSRMSSM.toggled.connect(self.show_records)
    self.chkTIM.toggled.connect(self.show_records)
    self.chkPSM.toggled.connect(self.show_records)
    self.chkCCM.toggled.connect(self.show_records)
    self.chkRGA.toggled.connect(self.show_records)
    self.chkSDSM.toggled.connect(self.show_records)
    self.chkCustom.toggled.connect(self.show_records)
    self.setStart.clicked.connect(self.set_start)
    self.setEnd.clicked.connect(self.set_end)
    self.clearTimes.clicked.connect(self.clear_times)
    self.comboMapID.currentIndexChanged.connect(self.show_records)
    self.comboBsmID.currentIndexChanged.connect(self.show_records)
    self.listWidget.currentRowChanged.connect(self.show_message)
    self.graphicsView.hide()
    self.treeView.hide()

    # menu    
    self.comboViewMode.addItem("Info")
    self.comboViewMode.addItem("Map")
    self.comboViewMode.addItem("JSON")
    self.comboViewMode.addItem("Python")
    self.comboViewMode.currentIndexChanged.connect(self.show_message)

    self.textMessage.setReadOnly(True)
    self.black = QColor(0,0,0)
    self.gray = QColor(128,128,128)
    self.red = QColor(255,0,0)
    self.orange = QColor(255,80,0)
    self.yellow = QColor(255,211,0)
    self.green = QColor(0,255,0)
    self.blue = QColor(0,0,255)
     
    # text
    self.filename = ""
    self.jsondata = []
    self.indexes = []
    self.loading = 0
    self.numloaded = 0

    # stats
    self.mapcount = {}
    self.spatcount = {}
    self.bsmcount = {}

    
  def closeEvent(self, event):
    event.accept()
    sys.exit(0)
  
  def set_start(self):
    item = self.listWidget.currentRow()
    item = self.indexes[item]   # because of filter, map list item to data index
    row = self.jsondata[item]
    start = str(row['Timestamp'])
    self.timeStart.setText(start)
    self.show_records()

  def set_end(self):
    item = self.listWidget.currentRow()
    item = self.indexes[item]   # because of filter, map list item to data index
    row = self.jsondata[item]
    start = str(row['Timestamp'])
    self.timeEnd.setText(start)
    self.show_records()

  def clear_times(self):
    self.timeStart.setText("")
    self.timeEnd.setText("")
  
  def msg_walk(self, ind, obj):
    spc = (' ' * ind)
    txt = ""
    for key, val in obj.items():
      if type(val)==dict:
        txt += spc + "%s:\n" % (key)
        txt += self.msg_walk(ind+2, val)
      else:
        txt += spc + "%s = %s\n" % (key, str(val))
    return txt

  def raw_message(self, row):
    msg_id = int(row['Message_id'])
    if msg_id >= j2735_min and msg_id < j2735_max:
      msg_str = j2735_names[msg_id-j2735_min]
    else:
      msg_str = str(msg_id)
    self.textMessage.setPlainText("J2735 %s: not implemented!" % (msg_str))

  def normal_text(self, txt):
    self.textMessage.setTextColor(self.black)
    self.textMessage.append(txt)

  def error_text(self, txt):
    self.textMessage.setTextColor(self.red)
    self.textMessage.append(txt)

#
# MAP/SPAT
#
  def get_mapid(self, msg):
    try:
      reg = msg['value']['intersections'][0]['id']['reg']
    except:
      reg = 0
    id = msg['value']['intersections'][0]['id']['id']
    id = str(reg) + "-" + str(id)
    return id

  def map_message(self, row):
    self.normal_text("Map Data Message (MAP)")
    self.normal_text("SAE Connection Intersection (CI) MAP Verification of elements")
    msg = row['Message']
    self.normal_text("Timestamp = " + str(datetime.fromtimestamp(row['Timestamp']/1000.0)))
    fail = 0
    if 1:
#    try:
      id = self.get_mapid(msg)
      rev = -1
      if 'msgIssueRevision' in msg['value']:
        rev = int(msg['value']['msgIssueRevision'])
      self.normal_text("MAP ID = %s, msgIssueRevision=%d" % (id, rev))
      if rev <= 0:
        self.error_text(" Bad or missing msgIssueRevision!")

      if id in self.mapcount and id in self.spatcount:
        self.normal_text(" with %u SPATs seen" % (self.spatcount[id]))
      else:
        self.normal_text(" with no SPATs seen")
      if 'timeStamp' in msg['value']:
        if msg['value']['timeStamp']:
          self.normal_text("  timeStamp (MinuteOfTheYear) = %d" % (msg['value']['timeStamp']))
        else:
          self.error_text("  Invalid timeStamp (MinuteOfTheYear)!")
      else:
        self.error_text(" Missing timeStamp (MinuteOfTheYear)!")
      numinter = 0
      
      for inter in msg['value']['intersections']:
        numinter += 1
        if inter['revision'] == 0:
          self.error_text("  Invalid message revision!")
          fail += 1
        if 'reg' not in inter['id']:
          self.error_text("  Missing Road Regulator ID!")
          fail += 1
        if int(inter['id']['id']) == 0:
          self.error_text("  Invalid intersection id")
          fail += 1

        self.normal_text("  Intersection id %u (%d lanes) revision=%s" % (int(inter['id']['id']), len(inter['laneSet']), inter['revision']))
        lat = int(inter['refPoint']['lat']) / 10e6
        lon = int(inter['refPoint']['long']) / 10e6
        if 'elevation' in inter['refPoint']:
          ele = str(int(inter['refPoint']['elevation']) * 0.1 - 409.6)
          self.normal_text("    Position: %f, %f, %s" % (lat, lon, ele))
        else:          
          self.error_text("    Position: %f, %f, MISSING" % (lat, lon, ele))
          fail += 1
        if 'laneWidth' in inter:
          self.normal_text("    Lane Width = %f cm" % (inter['laneWidth']))
        else:
          self.normal_text("    Lane Width = MISSING!")
          fail += 1
        if 'speedLimits' in inter:
          txt = "    Speed Limits = ["
          for spd in inter['speedLimits']:
            txt += str(spd['speed']) + ","
          txt += "]"
          self.normal_text(txt)
        else:
          self.error_text("    Missing Speed Limits!")
          fail += 1
        
        self.normal_text("    Lanes:")
        for lane in inter['laneSet']:
          txt = "      laneID %u (%u nodes) " % (int(lane['laneID']), len(lane['nodeList']['nodes']))
          miss = 0
          if 'ingressApproach' in lane:
            txt += "ingressApproach"
          elif 'egressApproach' in lane:
            txt += "egressApproach"
          else:
            txt += "approachType=MISSING"
            fail += 1
            miss = 1
          maneuver = "MISSING"
          if 'maneuvers' in lane:
            maneuver = lane['maneuvers']
          else:
            fail += 1
            miss = 1
          txt += ", maneuver=%s" % (maneuver)
          if miss:
            self.error_text(txt)
          else:
            self.normal_text(txt)
          
          # attributes
          gress = "UNKNOWN"
          if 'laneAttributes' in lane:
            attr = lane['laneAttributes']
            dir = int(attr['directionalUse'], 16)
            if dir == 0:
              gress = "Blocked"
            elif dir == 3:
              gress = "Allowed"
            elif dir & 1:
              gress = "Ingress"
            elif dir & 2:
              gress = "Egress"
            shwidth = "MISSING"
            if 'sharedWidth' in attr:
              shwidth = attr['sharedWidth']
            else:
              fail += 1
            lanetype = "MISSING"
            for i in ('vehicle', 'crosswalk','bikeLane','sidewalk','striping','trackedVehicle','parking'):
              if i in attr['laneType']:
                lanetype = i + "=" + attr['laneType'][i]
                break
            if gress=="MISSING" or gress=="UNKNOWN" or shwidth=="MISSING":
              self.error_text("        laneAttributes: directionalUse=%s, laneType.%s, sharedWidth=%s" % (gress, lanetype, shwidth))
            else:
              self.normal_text("        laneAttributes: directionalUse=%s, laneType.%s, sharedWidth=%s" % (gress, lanetype, shwidth))
          else:
            self.error_text("        laneAttributes: MISSING!")
            fail += 1
            
          if 'connectsTo' in lane:
            for conn in lane['connectsTo']:
              self.normal_text("        connectingLane=%u, maneuver=%u, signalGroup=%u" % (int(conn['connectingLane']['lane']), int(conn['connectingLane']['maneuver']), int(conn['signalGroup'])))
#    except Exception as e:
#      print(e)
#      txt += "Message does not look like a MAP message!\n"

    if fail:
      self.error_text("MAP Message V&V: FAILED!")
    else:
      self.normal_text("MAP Message V&V: Passed")

  def spat_message(self, row):
    self.normal_text("Signal Phase and Timing Message (SPaT)")
    self.normal_text("SAE Connected Intersection (CI) SPaT Verification of elements")
    msg = row['Message']
    self.normal_text("Timestamp = " + str(datetime.fromtimestamp(row['Timestamp']/1000.0)))
    fail = 0
    try:
      id = self.get_mapid(msg)
      if id in self.spatcount:
        self.normal_text("SPAT ID = %s (%u)" % (id, self.spatcount[id]))
      if id in self.mapcount:
        self.normal_text(" with %u MAPs seen" % (self.mapcount[id]))
      else:
        self.normal_text(" with no MAPs seen!")
      if 'timeStamp' in msg['value']:
        if msg['value']['timeStamp']:
          self.normal_text(" timeStamp (MinuteOfTheYear) = %d" % (msg['value']['timeStamp']))
        else:
          self.error_text(" Invalid timeStamp (MinuteOfTheYear)!")
      else:
        self.error_text(" Missing timeStamp (MinuteOfTheYear)!")
      numinter = 0
      
      for inter in msg['value']['intersections']:
        numinter += 1
        if inter['revision'] == 0:
          self.error_text("  Invalid message revision (msgCount)")
          fail += 1
        if 'timeStamp' in inter:
          if inter['timeStamp']:
            self.normal_text("  timeStamp (DSecond) = %d" % (inter['timeStamp']))
          else:
            self.error_text("  Invalid timestamp (DSecond)!")
            fail += 1
        else:
          self.error_text("  Missing timestamp (DSecond)!")
          fail += 1
        if 'reg' not in inter['id']:
          self.error_text("  Missing Road Regulator ID!")
          fail += 1
        if int(inter['id']['id']) == 0:
          self.error_text("  Invalid intersection id!")
          fail += 1
        numstates = 0

        self.normal_text("  Intersection %u (%d states) revision=%s, status=%s" % (int(inter['id']['id']), len(inter['states']), inter['revision'], inter['status']))
        for state in inter['states']:
          numstates += 1
          if 'signalGroup' in state:
            if int(state['signalGroup']):
              self.normal_text("    Movement signalGroup %u" % (int(state['signalGroup'])))
              # TBD check if signal group is in MAP
            else:
              self.error_text("    signalGroup is invalid!")
              fail += 1
          else:
            self.error_text("    signalGroup is missing!")
            fail += 1
          numevents = 0

          if 'maneuverAssistList' in state:
            numevents += 1
            for assist in state['maneuverAssistList']:
              self.normal_text("      ConnectionID=%d" % (int(assist['connectionID'])))
              # TOSCo GreenWindow
              if 'regional' in assist:
                for reg in assist['regional']:
                  if reg['regionId'] == 130:
                    ext = str(reg['regExtValue'])
                    gwmin = int(ext[0:4], 16)
                    gwmax = int(ext[4:8], 16)
                    self.normal_text("      GreenWindow = %d, %d" % (gwmin, gwmax))
          for sts in state['state-time-speed']:
            numevents += 1
            if 'eventState' in sts:
              if sts['eventState'] == "":
               self.error_text("      Invalid eventState (MovementPhaseState)!")
               fail += 1                
            else:
              self.error_text("      eventState (MovementPhaseState) is missing!")
              fail += 1
            if 'timing' not in sts:
              self.error_text("      timing (TimeChangeDetails) is missing!")
              fail += 1
              break
            timing = sts['timing']
            starttime = "MISSING"
            nexttime = "MISSING"
            mintime = "MISSING"
            maxtime = "MISSING"
            if 'startTime' in timing:
              starttime = str(int(timing['startTime']))
            if 'minEndTime' in timing:
              minval = str(int(timing['minEndTime']))
            if 'maxEndTime' in timing:
              maxval = str(int(sts['timing']['maxEndTime']))
            if 'nextTime' in timing:
              starttime = str(int(timing['nextTime']))
            if starttime=="MISSING" or nexttime=="MISSING" or mintime=="MISSING" or maxtime=="MISSING":
              self.error_text("      eventState=%s, startTime=%s\n      minEndTime=%s, maxEndTime=%s, nextTime=%s" % (sts['eventState'], starttime, mintime, maxtime, nexttime))
              fail += 1
            else:
              self.normal_text("      eventState=%s, startTime=%s\n      minEndTime=%s, maxEndTime=%s, nextTime=%s" % (sts['eventState'], starttime, mintime, maxtime, nexttime))
          if numevents == 0:
            self.error_text("    Movement events (state-time-speed) are missing!")
            fail += 1
        if numstates == 0:
          self.error_text("    Movement states (MovementList) are missing!")
          fail ++ 1
      if numinter == 0:
        self.error_text("No intersections!")
        fail ++ 1
    except Exception as e:
      print(e)
      self.error_text("Message does not look like a SPaT message!")

    if fail:
      self.error_text("SPaT Message V&V: FAILED!")
    else:
      self.normal_text("SPaT Message V&V: Passed")

#
# BSM
#
  def get_bsmid(self, msg):
    try:
      id = int(msg['value']['coreData']['id'], 16) & 0xffff
    except:
      id = msg['value']['coreData']['id'] & 0xffff
    return str(id)
 
  def bsm_message(self, row):
    self.normal_text("Basic Safety Message (BSM)")
    self.normal_text("SAE J2945/1 BSM Verification of required frames and elements (6.1.6)")
    msg = row['Message']
    self.normal_text("Timestamp = " + str(datetime.fromtimestamp(row['Timestamp']/1000.0)))
    fail = 0
    try:
      bsm = msg['value']
      # Part I
      if 'coreData' in bsm:
        self.normal_text(" Part I coreData:")
        self.normal_text(self.msg_walk(2, bsm['coreData']))
        id = self.get_bsmid(msg)
        if id == "0":
          self.error_text("Invalid BSM ID (id)!")
          fail += 1
      else:
        self.error_text(" coreData: MISSING!")
        fail += 1

      # Part II
      if "partII" in bsm:
        self.normal_text("Part II Extensions:")
        for part in bsm['partII']:
          part_id = part['partII-Id']

          # VehicleSafetyExtensions (checks)
          if part_id == 0:
            part_val = part['partII-Value']
            if 'pathHistory' in part_val:
              pass
            else:
              self.error_text("  pathHistory: NOT FOUND!")
              fail += 1
            if 'pathPrediction' in part_val:
              pass
            else:
              self.error_text("  pathPrediction: NOT FOUND!")
              fail += 1

          # VehicleSafetyExtensions (values)
          txt = ""
          if part_id == 0:
            txt += " VehicleSafetyExtensions:\n"
            txt += self.msg_walk(2, part['partII-Value'])
          elif part_id == 1:
            txt += " SpecialVehicleExtensions:\n"
            txt += self.msg_walk(2, part['partII-Value'])
          elif part_id == 2:
            txt += " SupplementalVehicleExtensions:\n"
            txt += self.msg_walk(2, part['partII-Value'])
          else:
            txt += " New/Unknown Extensions:\n"
            txt += self.msg_walk(2, part['partII-Value'])
          self.normal_text(txt)
      else:
        self.error_text("PartII: NOT FOUND")
        fail += 1
    except Exception as e:
      print(e)
      self.error_text("Message does not look like a BSM message!")
      fail += 1

    if fail:
      self.error_text("BSM Message V&V: FAILED!")
    else:
      self.normal_text("BSM Message V&V: Passed")

    # set the cursor position to 0
    cursor = QTextCursor(self.textMessage.document())
    cursor.setPosition(0)
    self.textMessage.setTextCursor(cursor)
#
# Corrections
#
  def nmea_message(self, row):
    txt = "NMEA Corrections Message (NMEA)\n"
    msg = row['Message']
    if 'value' in msg and 'NMEA-Payload' in msg['value']:
      nmea = msg['value']['NMEA-Payload']
      txt = msg['NMEA-Payload'] + "\n"
      txt += pynmea2.parse(msg['NMEA-Payload'])
    else:
      txt += "Message does not look like an NMEA message!\n"
    self.textMessage.setPlainText(txt)

  def rtcm_message(self, row):
    txt = "RTCM Corrections Message (RTCM)\n"
    msg = row['Message']
    win = 0
    if sys.platform == "win32" or sys.platform == "win64" or sys.platform == "cygwin":
      win = 1

    if 'value' in msg and 'msgs' in msg['value']:
      numrec = 0
      for rec in msg['value']['msgs']:
        numrec += 1
        inp = binascii.unhexlify(rec)
        hdr = "==============\nRTCM Record #" + str(numrec) + "\n"
        hdr += "--- hex data ---\n" + rec + "\n"

        msg = RTCMReader.parse(inp)
        out = "--- RTCM decode ---\n" + str(msg) + "\n"

        txt = txt + hdr + out
      if numrec == 0:
        txt += "RTCM Message is missing record data!"
    else:
      txt += "Message does not look like an RTCM message!\n"
    self.textMessage.setPlainText(txt)
#
# SRM/SSM
#
  def srm_message(self, row):
    txt = "Signal Request Message (SRM)\n"
    self.textMessage.setPlainText(txt)

  def ssm_message(self, row):
    txt = "Signal Status Message (SSM)\n"
    self.textMessage.setPlainText(txt)
#
# TIM
#
  def tim_message(self, row):
    txt = "Traveler Information Message (TIM)\n"
    self.textMessage.setPlainText(txt)
#
# NTCNA
#
  def ntcna_dvi_info(self, dvi):
    txt = "NTCNA DVI Message: "
    v2x = int(dvi['msg_id'])
    app = int(dvi['app_id'])
    sub = int(dvi['sub_id'])
#    thr = dvi['threat_class']
    lvl = int(dvi['threat_level'])
    tid = int(dvi['threat_id'])
    rng = float(dvi['range'])
    rngr = float(dvi['range_rate'])
    ttc = float(dvi['time2collision'])
    pos = int(dvi['roy_code_pos'])
    hv = int(dvi['roy_code_hv'])
    rv = int(dvi['roy_code_rv'])
    ind = int(dvi['roy_code_ind'])

    txt += "%s\n" % (v2x_names[v2x])
    if v2x==1:
      txt += "V2V Application = %s\n" % (v2v_names[app])
    elif v2x==2:
      txt += "V2I Application = %s %d\n" % (v2i_names[app], sub)
    txt += "Alert Level = %s\n" % (lvl_names[lvl])
    txt += "RV Id = %d\n" % (tid)
    txt += "Range = %f, rate = %f\n" % (rng, rngr)
    txt += "TTC %f\n" % (ttc)
    txt += "Roy: pos=%02x, hv=%02x, rv=%02x, ind=%02x\n" % (pos, hv, rv, ind)
    return txt
#
# Message, right hand side
#
  def show_message(self):
    if self.loading == 1:
      return

    # hide
    self.textMessage.hide()
    self.treeView.hide()
    self.graphicsView.hide()

    item = self.listWidget.currentRow()
    try:
      item = self.indexes[item]   # because of filter, map list item to data index
    except:
      item = 0
    view = self.comboViewMode.currentText()

    self.textMessage.setPlainText("Not implemented")

    try:
      row = self.jsondata[item]
    except:
      return
    msg = row['Message']

    if 'Message_id' in row:
#      msg_id = int(row['Message_id'])
      msg_id = msg['messageId']
      if view == "Info":
        self.textMessage.setPlainText("")
        self.textMessage.setTextColor(self.black)
        self.textMessage.setFontWeight(QFont.Normal)
        if msg_id == MESSAGE_MAP:
          self.map_message(row)
        elif msg_id == MESSAGE_SPAT:
          self.spat_message(row)
        elif msg_id == MESSAGE_BSM:
          self.bsm_message(row)
        elif msg_id == MESSAGE_NMEA:
          self.nmea_message(row)
        elif msg_id == MESSAGE_RTCM:
          self.rtcm_message(row)
        elif msg_id == MESSAGE_SRM:
          self.srm_message(row)
        elif msg_id == MESSAGE_SSM:
          self.ssm_message(row)
        elif msg_id == MESSAGE_TIM:
          self.tim_message(row)
        else:
          self.raw_message(row)
        self.textMessage.show()
      elif view == "Map":
        # Map view
        self.graphicsView.show()
      elif view == "JSON":
        # JSON view (would like to do a collapsible tree widget)
        self.textMessage.setPlainText(json.dumps(self.jsondata[item], indent=2))
        self.textMessage.show()
      elif view == "Python":
        # Python view
        self.textMessage.setPlainText(pprint.pformat(self.jsondata[item], indent=2, compact=True))
        self.textMessage.show()
#      elif view == "YAML":
#        self.textMessage.setPlainText(yaml.safe_dump(self.jsondata[item]))
#        self.textMessage.show()
    elif 'Message_type' in row:
      msg_type = row['Message_type']
      if view == "Info":
        if msg_type == 'DVI':
          txt = self.ntcna_dvi_info(msg)
          self.textMessage.setPlainText(txt)
        self.textMessage.show()
      elif view == "Map":
        # Map view
        self.graphicsView.show()
      elif view == "JSON":
        self.textMessage.setPlainText(json.dumps(self.jsondata[item], indent=2))
        self.textMessage.show()
      elif view == "Python":
        self.textMessage.setPlainText(pprint.pformat(self.jsondata[item], indent=2, compact=True))
        self.textMessage.show()

    # set the cursor position to 0
    cursor = QTextCursor(self.textMessage.document())
    cursor.setPosition(0)
    self.textMessage.setTextCursor(cursor)
#
# Messages, left hand side
#
  def show_records(self):   
    if self.loading == 1:
      return
    self.listWidget.clear()
    self.indexes.clear()

    index = -1
    for row in self.jsondata:
      # filter
      index += 1
      match = 0
      id = ""

      # data
      timestamp = row['Timestamp']
      direction = row['Direction']

      # direction filter
      if direction == "TX":
        if not self.chkTX.isChecked():
          continue
      elif direction == "RX":
        if not self.chkRX.isChecked():
          continue
      else:
        continue

      # time filter
      start = self.timeStart.text()
      end = self.timeEnd.text()
      if start != "":
        start = int(start)
        if row['Timestamp'] < start:
          continue
      if end != "":
        end = int(end)
        if row['Timestamp'] > end:
          continue      

      # message filter
      msg = row['Message']
      if 'Message_id' in row:
        msg_id = row['Message_id']
        if msg_id == MESSAGE_MAP:
          msg_str = "MAP"
          if self.chkMAP.isChecked():
            id = self.get_mapid(msg)
            txt = self.comboMapID.currentText()
            if txt == "All":
              match = 1
            elif txt == id:
              match = 1
        if msg_id == msg_id == MESSAGE_RGA:
          msg_str = "RGA"
          if self.chkRGA.isChecked():
            id = self.get_mapid(msg)
            txt = self.comboMapID.currentText()
            if txt == "All":
              match = 1
            elif txt == id:
              match = 1
        elif msg_id == MESSAGE_SPAT or msg_id == MESSAGE_TSPAT:
          msg_str = "SPAT"
          if self.chkSPAT.isChecked():
            id = self.get_mapid(msg)
            txt = self.comboMapID.currentText()
            if txt == "All" or txt == "*" or txt == "":
              match = 1
            elif txt == id:
              match = 1
        elif msg_id == MESSAGE_BSM:
          msg_str = "BSM"
          if self.chkBSM.isChecked():
            id = self.get_bsmid(msg)
            txt = self.comboBsmID.currentText()
            if txt == "All" or txt == "*" or txt == "":
              match = 1
            elif txt == id:
              match = 1
        elif msg_id == MESSAGE_NMEA or msg_id == MESSAGE_RTCM:
          msg_str = "NMEA"
          if msg_id == MESSAGE_RTCM:
            msg_str = "RTCM"
          if self.chkRTCM.isChecked():
            match = 1
        elif msg_id == MESSAGE_PDM or msg_id == MESSAGE_PVD:
          msg_str = "PDM"
          if msg_id == MESSAGE_PVD:
            msg_str = "PVD"
          if self.chkPDM.isChecked():
            match = 1
        elif msg_id == MESSAGE_SRM or msg_id == MESSAGE_SCPR:
          msg_str = "SRM/SCPR"
          if self.chkSRMSSM.isChecked():
            match = 1
        elif msg_id == MESSAGE_SSM or msg_id == MESSAGE_SCPS:
          msg_str = "SSM/SCPS"
          if self.chkSRMSSM.isChecked():
            match = 1
        elif msg_id == MESSAGE_TIM or msg_id == MESSAGE_RSM or msg_id == MESSAGE_RWM:
          msg_str = "TIM/RSM/RWM"
          if self.chkTIM.isChecked():
            match = 1
        elif msg_id == MESSAGE_PSM or msg_id == MESSAGE_PSM2:
          msg_str = "PSM/PSM2"
          if self.chkPSM.isChecked():
            match = 1
        elif msg_id == MESSAGE_CCM:
          msg_str = "CCM"
          if self.chkCCM.isChecked():
            match = 1
        elif msg_id == MESSAGE_SDSM or msg_id == MESSAGE_MSCM:
          msg_str = "SDSM/MSCM"
          if self.chkSDSM.isChecked():
            match = 1
        else:
          if msg_id >= j2735_min and msg_id < j2735_max:
            msg_str = j2735_names[msg_id-j2735_min]
          else:
            msg_str = str(msg_id)
          # add check for others
  
        # filter
        if match == 0:
          continue
        self.indexes.append(index)
  
        dot2 = int(row['P1609dot2_flag'])
        if dot2 == 0:
          dot2 = "unsigned"
        elif dot2 == 1:
          dot2 = "signed"
        elif dot2 == 1:
          dot2 = "encrypted"
        else:
          dot2 = "error"
  
        line = "%13u %2s %4s %6s %s" %(timestamp, direction, msg_str, id, dot2)
        self.listWidget.addItem(line)
      elif 'Message_type' in row:
        msg_type = row['Message_type']
        if self.chkCustom.isChecked():
          match = 1
        else:
          continue
        self.indexes.append(index)
        line = "%13u %2s %4s %s" % (timestamp, direction, msg_type, lvl_names[int(msg['threat_level'])])
        self.listWidget.addItem(line)


    # show data
    self.listWidget.setCurrentRow(0)
    self.show_message()
#
# loading
#
  def load_data(self):
    self.comboMapID.clear()
    self.comboMapID.addItem("All")
    self.comboBsmID.clear()
    self.comboBsmID.addItem("All")
    maps = []
    bsms = []
    
    # find all unique IDs
    for row in self.jsondata:
      msg = row['Message']
      if 'Message_type' in row:
        continue
      msg_id = row['Message_id']
      if msg_id == MESSAGE_MAP:
        id = self.get_mapid(msg)
        maps.append(id)
        if id in self.mapcount:
          self.mapcount[id] += 1
        else:
          self.mapcount[id] = 1
      elif msg_id == MESSAGE_SPAT:
        id = self.get_mapid(msg)
        if id in self.spatcount:
          self.spatcount[id] += 1
        else:
          self.spatcount[id] = 1
      elif msg_id == MESSAGE_BSM:
        id = self.get_bsmid(msg)
        if id in self.bsmcount:
          self.bsmcount[id] += 1
        else:
          self.bsmcount[id] = 1
        bsms.append(id)

    maps = set(maps)
    maps = list(maps)
    maps.sort()
    self.comboMapID.addItems(maps)

    bsms = set(bsms)
    bsms = list(bsms)
    bsms.sort()
    self.comboBsmID.addItems(bsms)
    
    self.loading = 0
    self.show_records()
  
  def load_csv(self, file):
    self.filename = file
    self.loading = 1
    self.numloaded = 0
    self.jsondata = []
    with open(file) as f:
      for line in f:
        row = line.split(',')
        data = {}
        data['Timestamp'] = int(row[0])
        if row[1] == 'R' or row[1] == 'RX':
          data['Direction'] = 'RX'
        elif row[1] == 'S' or row[1] == 'T' or row[1] == 'TX':
          data['Direction'] = 'TX'
        data['Message_id'] = int(row[2])
        try:
          data['P1609dot2_flag'] = int(row[-1])
        except:
          data['P1609dot2_flag'] = 0
        row = line.split('\'')
        js = str(row[1])
        try:
          data['Message'] = json.loads(js)
          self.jsondata.append(data)
          self.numloaded += 1
        except:
          continue
    self.load_data()

  def load_json(self, file):
    self.filename = file
    self.loading = 1
    self.numloaded = 0
    self.jsondata = []
    with open(file) as f:
      for line in f:
        self.jsondata.append(json.loads(line))
        self.numloaded += 1
    self.load_data()
 
  def load_file(self, file):
    self.load_json(file)

#
# dialogs
#
  def file_dialog(self):
    filedialog = QtWidgets.QFileDialog(self)
    filedialog.setDirectory(QtCore.QDir.currentPath())
    filedialog.setDefaultSuffix("json")
    filedialog.setNameFilter("JSON (*.json);; all (*.*)")
    filedialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    selected = filedialog.exec()
    if selected:
      filename = filedialog.selectedFiles()[0]
      self.inputFile.setText(filename)
      if filename.endswith('.json') or filename.endswith('.JSON'):
        self.load_json(filename)
      elif filename.endswith('.csv') or filename.endswith('.CSV'):
        self.load_csv(filename)
  
  def save_config(self):
    config = {}
    config['input_dir'] = os.getcwd()
    cfg.write_config(config)

  def exit_button(self):
    self.save_config()
    sys.exit(0)

if __name__ == '__main__':
  app = QtWidgets.QApplication(sys.argv)

  window = ViewerWindow()
  window.show()

  config = cfg.read_config()
  if 'input_dir' in config:
    os.chdir(config['input_dir'])

  ret = app.exec()
  sys.exit(ret)

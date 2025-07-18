#!/usr/bin/env python3

import os
import sys
from math import *
from socket import *
from struct import unpack
from time import time, ctime
import binascii
import threading
import json
import shutil

from j2735_mf import *
from j2735_bsm import *
from utils.logging import LOGlog, JSONlog, log_genname

from pykml.factory import KML_ElementMaker as KML
from lxml import etree

J2735_FILE_VERSION = "2024-09-16"
J2735_TOOL_VERSION = "2.0.8"

class j2735_logcore:
  def __init__(self):
    # debug log
    self.debug_on = 0
    self.debug = 0
    self.bin_maps = 0

    # data logging
    self.log = 0
    self.basepath = 1
    self.logdir = ""
    self.logpath = ""
    self.logfile = ""
    self.logext = '.json'
    self.kml = 0
    self.kmlfile = ""
    self.logging = 0
    self.unknowns = 1
    self.convert = 0
    self.bsm_hv_id = 0
    self.splitbsms = 0
    self.splitmapspat = 0

    # meta log
    self.metafile = ""
    self.meta = 0

    # message
    self.msg = {}
    self.msg_id = 0
    self.is_tx = 0
    self.tx_bsm = 0
    self.rx_bsm = 0
    self.rx_map = 0
    self.rx_spat = 0

    # WSMP
    self.wsmp_layer = 0
    self.tx_pwr = 0
    self.chan_no = 0
    self.data_rate = 0
    self.chan_load = 0
    self.psid_actual = 0

    # Dot2
    self.dot2_signed = 0
    self.signed_count = 0

    # statistics
    self.count = 0
    self.timestamp = 0
    self.tx_count = 0
    self.rx_count = 0
    self.rx_counts = [0] * 128
    self.tx_counts = [0] * 128
    self.bsmp_tx_count = 0
    self.bsmp_rx_count = 0
    self.bsm_tx_count = 0
    self.bsm_rx_count = 0
    self.map_tx_count = 0
    self.map_rx_count = 0
    self.spat_tx_count = 0
    self.spat_rx_count = 0
    self.other_tx_count = 0
    self.other_rx_count = 0
    self.unknown_tx_count = 0
    self.unknown_rx_count = 0
    self.error_count = 0
    self.cv_pilot_count = 0
    self.tscbm_count = 0

    # master KML
    self.maplist = {}
#
# log file
#
  def log_open(self, file=""):
    if self.logging:
      return
    self.log = JSONlog()
    self.kml = LOGlog()

    # output director
    if self.logdir != "" and os.path.isdir(self.logdir) != 1:
      os.mkdir(self.logdir)

    # generate uniq name
    if file == "":
      file = log_genname(self.logdir, "v2x-log_", self.logext)

    # keep basename or generate unique
    base = os.path.basename(file)
    base.replace(" ", "_")
    base = os.path.splitext(base)[0]
    self.logpath = self.logdir
    if self.basepath and self.logdir != "":
      self.logpath += "/" + base
    if self.logpath != "/" and self.logpath != "." and self.logpath != ".." and os.path.isdir(self.logpath) == 1:
      shutil.rmtree(self.logpath)
    os.mkdir(self.logpath)
    self.logfile = self.log.create( os.path.join(self.logpath, base + self.logext) )
    self.kmlfile = self.kml.create( os.path.join(self.logpath, base + ".kml") )

    # metadata output
    self.meta = LOGlog()
    self.meta.create(self.logpath + "/" + "metadata.txt")
    if self.meta:
      self.meta.write("J2735 Tool Version: " + J2735_TOOL_VERSION)
      self.meta.write("J2735 File Version: " + J2735_FILE_VERSION)
      self.meta.write(ctime())
      self.meta.write("J2735 Input: " + file)
      self.meta.write("J2735 Output: " + self.logfile)
    self.logging = 1

    # debug output
    if self.debug_on:
      self.debug = LOGlog()
      self.debug.create(self.logpath + "/" + "debug.txt")
      if self.debug:
        self.debug.write("J2735 Tool Version: " + J2735_TOOL_VERSION)
        self.debug.write("J2735 File Version: " + J2735_FILE_VERSION)
        self.debug.write(ctime())
        self.debug.write("J2735 Input: " + file)
        self.debug.write("J2735 Output: " + self.logfile)

  def log_close(self):
    if not self.logging:
      return
    self.logging = 0
    self.meta.write(ctime())
    self.meta.close()

  def log_write(self, string):
    self.meta.write(string)

  def log_debug(self, string):
    if self.debug_on:
      self.debug.write(string)

  def map_bin_output(self, reg, id, raw):
    if not self.bin_maps:
      return
    logfile = os.path.join(self.logpath, "map-" + str(reg) + "-" + str(id) + ".bin")
    if not os.path.isfile(logfile):
      with open(logfile, 'wb') as fp:
        fp.write(raw)
        fp.close()

  def log_write_bsm(self, id, data):
    logfile = os.path.join(self.logpath, "bsm-" + str(id) + self.logext)
    with open(logfile, 'a') as fp:
      fp.write(json.dumps(data, separators=(',', ':')))
      fp.write("\n")
      fp.close()

  def log_write_mapspat(self, reg, id, data):
    logfile = os.path.join(self.logpath, "mapspat-" + str(reg) + "-" + str(id) + self.logext)
    with open(logfile, 'a') as fp:
      fp.write(json.dumps(data, separators=(',', ':')))
      fp.write("\n")
      fp.close()

  def log_write_spat(self, reg, id, data):
    logfile = os.path.join(self.logpath, "spat-" + str(reg) + "-" + str(id) + self.logext)
    with open(logfile, 'a') as fp:
      fp.write(json.dumps(data, separators=(',', ':')))
      fp.write("\n")
      fp.close()

  def log_write_map(self, reg, id, data):
    logfile = os.path.join(self.logpath, "map-" + str(reg) + "-" + str(id) + self.logext)
    with open(logfile, 'a') as fp:
      fp.write(json.dumps(data, separators=(',', ':')))
      fp.write("\n")
      fp.close()

  def kml_write_map(self, reg, id, data):
    kmlfile = os.path.join(self.logpath, "map-" + str(reg) + "-" + str(id) + ".kml")
    if os.path.isfile(kmlfile):
      return

    # intersections
    interfld = KML.Folder(KML.name("intersections"))
    interid = 0
    for inter in data['Message']['value']['intersections']:
      ref = inter['refPoint']
      ref_lat = ref['lat']/10e6
      ref_long = ref['long']/10e6
      interpm = KML.Placemark(
        KML.name("map_0-%s" % (id)),
        KML.styleUrl("#Refpoint"),
        KML.Point(
          KML.coordinates("%.7f,%.7f" % (ref_long,ref_lat))
        )
      )

      # lanes
      lanefld = KML.Folder(KML.name("intersection_%d" % (interid)), interpm)
      for lane in inter['laneSet']:
        laneid = lane['laneID']

        # attributes
        gress = "Unknown"
        if 'laneAttributes' in lane:
          dir = int(lane['laneAttributes']['directionalUse'], 16)
          if dir == 0:
            gress = "Blocked"
          elif dir == 3:
            gress = "Allowed"
          elif dir & 1:
            gress = "Ingress"
          elif dir & 2:
            gress = "Egress"

        mperdeg = 111.13285 * 1000.0 # (nautical mile to km) to meters per degree
        latrad = radians(ref_lat) # to radians
        latlen = mperdeg
        lonlen = cos(latrad) * (mperdeg + 0.373*sin(latrad)*sin(latrad))

        # points
        pointfld = KML.Folder(KML.name("lane_%d" % laneid))
        if 'nodeList' in lane:
          numpt = 0
          pt_lat = ref_lat
          pt_long = ref_long

          for node in lane['nodeList']['nodes']:
            point = node['delta']
            offxy = 1
            # offsets
            if 'node-XY1' in point:
              otype = 'node-XY1'
            elif 'node-XY2' in point:
              otype = 'node-XY2'
            elif 'node-XY3' in point:
              otype = 'node-XY3'
            elif 'node-XY4' in point:
              otype = 'node-XY4'
            elif 'node-XY5' in point:
              otype = 'node-XY5'
            elif 'node-XY6' in point:
              otype = 'node-XY6'
            elif 'node-LatLon' in point:
              pt_lat = point['node-LatLon']['lat'] / 10e6
              pt_long = point['node-LatLon']['lon'] / 10e6
              offxy = 0

            if offxy:
              xoff = point[otype]['x'] / 100.0;
              yoff = point[otype]['y'] / 100.0;
              # add offset to previous node
              pt_lat += (yoff / latlen)
              pt_long += (xoff / lonlen)
            else:
              pt_lat = ref_lat - pt_lat
              pt_long = ref_long - pt_long

            if numpt == 0 and (gress == "Ingress"):
              style = "Stopbar"
            else:
              style = gress
            pm = KML.Placemark(
              KML.name("lane_%d-%d" % (laneid, numpt)),
              KML.styleUrl("#" + style),
              KML.Point(
                KML.coordinates("%.7f,%.7f" % (pt_long, pt_lat))
              )
            )
            numpt += 1
            pointfld.append(pm)
        else:
          # computed lanes
          pass

        lanefld.append(pointfld)
      interfld.append(lanefld)
      interid += 1

    doc = KML.Document(KML.name("Map_%d_%d Description" % (reg, id)),
      KML.Style(
        KML.IconStyle(
          KML.scale(2),
          KML.Icon(
            KML.href("http://www.google.com/mapfiles/traffic.png"),
          )
        ),
        id = "Refpoint"
      ),
      KML.Style(
        KML.IconStyle(
          KML.Icon(
            KML.href("http://maps.google.com/mapfiles/kml/paddle/purple-square-lv.png"),
          )
        ),
        id = "Stopbar"
      ),
      KML.Style(
        KML.IconStyle(
          KML.Icon(
            KML.href("http://maps.google.com/mapfiles/kml/paddle/purple-blank-lv.png"),
          )
        ),
        id = "Ingress"
      ),
      KML.Style(
        KML.IconStyle(
          KML.Icon(
            KML.href("http://maps.google.com/mapfiles/kml/paddle/blu-blank-lv.png"),
          )
        ),
        id = "Egress"
      ),
      KML.Style(
        KML.IconStyle(
          KML.Icon(
            KML.href("http://maps.google.com/mapfiles/kml/paddle/wht-blank-lv.png"),
          )
        ),
        id = "Allowed"
      ),
      KML.Style(
        KML.IconStyle(
          KML.Icon(
            KML.href("http://maps.google.com/mapfiles/kml/paddle/stop-lv.png"),
          )
        ),
        id = "Blocked"
      ),
      interfld
    )
    kml = KML.kml(doc)

    # output
    with open(kmlfile, 'a') as fp:
      xml = etree.tostring(kml, pretty_print=True)
      fp.write(xml.decode())

#
# raw J2735 packets
#
  def raw_tx_packet(self, tx):
    self.count += 1
    self.tx_count += 1
    self.is_tx = 1
    self.timestamp = int(self.timestamp)

    # decode J2735 and log
    try:
      mf = j2735_mf()
      self.msg = mf.decode_raw(tx)
    except Exception as e:
#      self.log_debug(e)
      self.log_debug("\tJ2735 Unknown TX Packet %u unable to decode: %s" % (self.msg_id, str(binascii.hexlify(tx))))
      self.msg_id = -1
      self.unknown_tx_count += 1
      return

    self.msg_id = int(self.msg['messageId'])
    if self.logging:
      data = {'Timestamp': self.timestamp,
              'Direction': 'TX',
              'Message_id': self.msg_id,
              'WSMP_version': self.wsmp_layer,
              'PSID': self.psid_actual,
              'P1609dot2_flag': self.dot2_signed,
              'Message': self.msg}
      if self.tx_count == 1:
        data['Version'] = J2735_FILE_VERSION
      self.log.write(data)

    if self.msg_id == MESSAGE_BSM:
      id = int(self.msg['value']['coreData']['id'], 16) & 0xffff
      self.log_debug("\tJ2735 BSM TX Packet: %u" %(id))
      if self.convert:
        bsm = j2735_bsm()
        bsm.message(self.msg)
        data['Converted'] = 1
      if self.splitbsms:
        self.log_write_bsm(id, data)
      self.tx_bsm = self.msg
      self.bsm_tx_count += 1
    elif self.msg_id == MESSAGE_MAP:
      id = self.msg['value']['intersections'][0]['id']['id']
      self.log_debug("\tJ2735 MAP TX Packet: %u" % (id))
      self.map_tx_count += 1
    elif self.msg_id == MESSAGE_SPAT:
      id = self.msg['value']['intersections'][0]['id']['id']
      self.log_debug("\tJ2735 SPAT TX Packet: %u" % (id))
      self.spat_tx_count += 1
    else:
      self.log_debug("\tJ2735 Other TX Packet %u: %s" % (self.msg_id, str(binascii.hexlify(tx))))
      self.other_tx_count += 1
    self.tx_counts[self.msg_id] += 1

  def raw_rx_packet(self, rx):
    self.count += 1
    self.rx_count += 1
    self.is_tx = 0
    self.timestamp = int(self.timestamp)

    # decode J2735 and log
    try:
      mf = j2735_mf()
      self.msg = mf.decode_raw(rx)
    except Exception as e:
      self.log_debug(e)
      self.log_debug("\tJ2735 Unknown RX Packet %u unable to decode: %s" % (self.msg_id, str(binascii.hexlify(rx))))
      self.msg_id = -1
      self.unknown_rx_count += 1
      return

    self.msg_id = int(self.msg['messageId'])
    if self.logging:
      data = {'Timestamp': self.timestamp, 'Direction': 'RX', 'Message_id': self.msg_id,
              'WSMP_version': self.wsmp_layer, 'PSID': self.psid_actual, 'P1609dot2_flag': self.dot2_signed, 'Message': self.msg}
      if self.rx_count == 1:
        data['Version'] = J2735_FILE_VERSION
      self.log.write(data)

    if self.msg_id == MESSAGE_BSM:
      id = int(self.msg['value']['coreData']['id'], 16) & 0xffff
      self.log_debug("\tJ2735 BSM RX Packet: %u" %(id))
      if self.bsm_hv_id and self.bsm_hv_id == id:
        data['Direction'] = 'TX'
      if self.convert:
        bsm = j2735_bsm()
        bsm.message(self.msg)
        data['Converted'] = 1
      if self.splitbsms:
        self.log_write_bsm(id, data)
      self.rx_bsm = self.msg
      self.bsm_rx_count += 1
    elif self.msg_id == MESSAGE_MAP:
      try:
        reg = self.msg['value']['intersections'][0]['id']['reg']
      except:
        reg = 0
      id = self.msg['value']['intersections'][0]['id']['id']
      if self.splitmapspat == 1:
        self.log_write_mapspat(reg, id, data)
        self.kml_write_map(reg, id, data)
      elif self.splitmapspat == 2:
        self.log_write_map(reg, id, data)
        self.kml_write_map(reg, id, data)
      self.log_debug("\tJ2735 MAP RX Packet: %u" % (id))
      self.map_bin_output(reg, id, rx)
      self.rx_map = self.msg
      self.map_rx_count += 1
      self.maplist[id] = self.msg['value']['intersections'][0]
      # TBD: Convert absolute lat/long nodes to offsets???
    elif self.msg_id == MESSAGE_SPAT:
      try:
        reg = self.msg['value']['intersections'][0]['id']['reg']
      except:
        reg = 0
      id = self.msg['value']['intersections'][0]['id']['id']
      if self.splitmapspat == 1:
        self.log_write_mapspat(reg, id, data)
      elif self.splitmapspat == 2:
        self.log_write_spat(reg, id, data)
      self.log_debug("\tJ2735 SPAT RX Packet: %u" % (id))
      self.rx_spat = self.msg
      self.spat_rx_count += 1
    elif self.msg_id > MESSAGE_SPAT and self.msg_id < MESSAGE_LAST:
      self.log_debug("\tJ2735 %s (%d) RX Packet" % (msg_names[self.msg_id], self.msg_id))
      self.other_rx_count += 1
    else:
      self.log_debug("\tJ2735 Unknown RX Packet %u: %s" % (self.msg_id, str(binascii.hexlify(rx))))
      self.unknown_rx_count += 1
    self.rx_counts[self.msg_id] += 1

#
# J2735 packets with header
#
  def hdr_packet(self, rx):
    # J2735 with 16 byte header
    if rx[13] == 0 and rx[14] == 0 and rx[15] == 0:
      ts, rxtx, chan, psid, obe, p0, p1, p2 = unpack("!QBBHBBBB", rx[0:15]) # ficosa
    else:
      rxtx, chan, psid, obe, p0, p1, p2, ts = unpack("!BBHBBBBQ", rx[0:15])
    self.timestamp = ts

    if rxtx==1:
      self.raw_tx_packet(rx[16:])
    elif rxtx==2:
      self.raw_rx_packet(rx[16:])

#
# BSMP packets (DENSO, CAMP and NTCNA only)
#
  def bsmp_tx_packet(self, txe):
    self.count += 1
    self.tx_count += 1
    self.bsmp_tx_count += 1
    self.is_tx = 1
    self.msg_id = MESSAGE_BSM

    # unpack TXE header and BSM
    bsmp = BSMP()
    bsmp.convert = self.convert
    bsmp.decode_txe(txe[0:4])
    bsmp.decode_bsmp(txe[4:])
    self.timestamp =  int(bsmp.get_ts())

    # encode for logging
    data = bsmp.encode_bsm()
    self.msg = {'messageId': 20, 'value': data}
    data = {'Timestamp': self.timestamp, 'Direction': 'RX', 'Message_id': MESSAGE_BSM,
            'P1609dot2_flag': self.dot2_signed, 'Version': J2735_FILE_VERSION, 'Message': self.msg}
    self.tx_bsm = self.msg
    self.log.write(data)

  def bsmp_rx_packet(self, rx):
    self.count += 1
    self.rx_count += 1
    self.bsmp_rx_count += 1
    self.is_tx = 0
    self.msg_id = MESSAGE_BSM

    # unpack SIB header and BSM
    bsmp = BSMP()
    bsmp.convert = self.convert
    bsmp.decode_sib(rx[0:32])
    bsmp.decode_bsmp(rx[32:])
    self.timestamp =  int(bsmp.get_ts())

    # encode for logging
    data = bsmp.encode_bsm()
    self.msg = {'messageId': 20, 'value': data}
    data = {'Timestamp': self.timestamp, 'Direction': 'RX', 'Message_id': MESSAGE_BSM,
            'P1609dot2_flag': self.dot2_signed, 'Version': J2735_FILE_VERSION, 'Message': self.msg}
    self.rx_bsm = self.msg
    self.log.write(data)

  def ntcna_dvi_packet(self, data):
    data = bytearray(data)
    dvi = DVI()
    if data[0] >= 32:
      # new JSON format
      msg = dvi.decode_json(data)
    else:
      dvi.decode_old(bytearray(data))
      msg = dvi.dump_data()
    data = {'Timestamp': self.timestamp, 'Direction': 'RX', 'Message_type': 'DVI', 'Message': self.msg}
    data['Message'] = msg
    self.log.write(data)

#
# reports and stats
#
  def print_report(self):
    self.meta.write("J2735 Packet Summary")
    self.meta.write("=========================================")
    if self.bsmp_tx_count or self.bsmp_rx_count:
      self.meta.write("BSMP   RX, TX packets = %7u, %7u" % (self.bsmp_rx_count, self.bsmp_tx_count))
    if self.bsm_tx_count or self.bsm_rx_count:
      self.meta.write("BSM    RX, TX packets = %7u, %7u" % (self.bsm_rx_count, self.bsm_tx_count))
      print("\tBSM RX, TX packets = %7u, %7u" % (self.bsm_rx_count, self.bsm_tx_count))
    for i in range(MESSAGE_MAP, MESSAGE_LAST):
      if self.rx_counts[i] or self.tx_counts[i]:
        self.meta.write("%6s RX, TX packets     = %7u, %7u" % (msg_names[i], self.rx_counts[i], self.tx_counts[i]))
        print("\t%6s RX, TX packets     = %7u, %7u" % (msg_names[i], self.rx_counts[i], self.tx_counts[i]))
    if self.unknown_tx_count or self.unknown_rx_count:
      self.meta.write("%6s packets        = %7u, %7u" % ("Unknown", self.unknown_rx_count, self.unknown_tx_count))
    if self.error_count:
      self.meta.write("%6s packets        = %7u" % ("ERROR", self.error_count))
    self.meta.write("=========================================")
    self.meta.write("Total  RX, TX packets = %7u, %7u" % (self.rx_count, self.tx_count))
    if self.signed_count:
      self.meta.write("Total packets signed = %u" % (self.signed_count))
    if self.tscbm_count:
      self.meta.write("TSCBM packets = %u" % (self.tscbm_count))
    self.meta.write("\n")

    # master KML
    fld = KML.Folder()
    for gid, data in self.maplist.items():
      ref = data['refPoint']
      pm = KML.Placemark(
        KML.name("map_0-%d" % (gid)),
        KML.Point(
          KML.coordinates("%.7f,%.7f" % (ref['long']/10e6, ref['lat']/10e6))
        )
      )
      fld.append(pm)
    doc = KML.Document(KML.name("Master Map List"), fld)
    kml = KML.kml(doc)
    xml = etree.tostring(kml, pretty_print=True)
    self.kml.write(xml.decode())

    print("Processed %u/%u useful packets\n" % (self.count, self.total))

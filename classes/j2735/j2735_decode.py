#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  1 14:28:09 2021

@author: neal
"""

import os
import sys
import struct
import json
import binascii
import re
from scapy.all import *
from tqdm import tqdm

from p1609dot2.dot2oer import *
from p1609dot3.p1609dot3 import *
from j2735 import MessageFrame
from j2735_bsm import *
from utils.logging import JSONlog, log_genname
from j2735_logcore import j2735_logcore

from ntcip.test_tscbm import parse_TSCBM

class j2735_decode(j2735_logcore):
  def __init__(self):
    super().__init__()
    # logging
    self.logdir = ""
    self.total = 0
    
    # options
    self.udp_port = 0
    self.offset_bytes = 0
    self.padding_bytes = 0
    self.vehicle_id = 0
  
  def log_make(self, file=""):
    super().log_open(file)

###############################################################################
# J2735
###############################################################################
  
  def parse_j2735(self, pkt):     
    self.log_debug("SAE J2735 Layer (%u):" % (len(pkt)))
    if self.is_tx:
      self.raw_tx_packet(pkt)
    else:
      self.raw_rx_packet(pkt)

###############################################################################
# P1609.2
###############################################################################

  def _parse_p1609(self, pkt):
    #
    # manual OER decoding
    #
    if pkt[0] != 3:
      return
    index = 1
    content = pkt[index]
    index += 1
    
    if content & 0x80:
      content &= 0x07
      if content == 0:
        # unsecured
        (val, leng) = oer_parse_length(pkt[index:])
        self.log_debug("\tUnsecured (%u)" % (leng))
        index += leng
        self.parse_j2735(pkt[index:])
      elif content == 1:
        self.dot2_signed = 1
        self.signed_count += 1
        self.log_debug("\tSigned (secured)")
        index += 2  # skip hash algorithm
        # signed only
        self._parse_p1609(pkt[index:])  # recursive
      elif content == 2:
        # encrypted
        self.log_debug("\tEncrypted (secured)")
        pass

  def parse_p1609(self, pkt):
    self.log_debug("IEEE 1609.2 Layer (%u):" % (len(pkt)))
    self.dot2_signed = 0
    self.signed_count = 0
    self._parse_p1609(pkt)

###############################################################################
# Tazman
###############################################################################

  def parse_tazman(self, pkt):
    ver = pkt[0]
    typ = pkt[1]
    enc = pkt[2] << 8 | pkt[3]
    index = 4
  
    self.log_debug("Tazman Sniffer Protocol (%u): %d, %d, %d" % (len(pkt), ver, typ, enc))
    # ver 1 and 802.11 encapsulation
    if ver != 1 or enc != 18:
      return;

    # parse
    tag = pkt[index]
    index += 1
    while (tag != 1):
      if tag == 0:
        continue;
    
      # get value
      leng = pkt[index]
      index += 1
      val = pkt[index]
      index += 1
      leng -= 1
      while leng:
        val <<= 8
        val |= pkt[index]
        index += 1
        leng -= 1
    
      if tag == 10:
        self.xmit_power = val
      elif tag == 12:
        self.data_rate = val
      elif tag == 13:
        taztime = val
      elif tag == 18:
        self.chan_no = val
      tag = pkt[index]
      index += 1

    self.log_debug("\tTazman: pwr=%d, chan=%d, rate=%d" % (self.xmit_power, self.chan_no, self.data_rate))

    self.parse_802_11(pkt[index:])

###############################################################################
# UDP
###############################################################################

  def parse_udp(self, pkt):
    try:
      port = pkt.dport
    except:
      port = pkt[2] << 8 | pkt[3]
    buff = raw(pkt)
    data = buff[8:]
    leng = len(data)

    self.log_debug("\tParsing UDP Layer port %d (%u):" % (port, len(pkt)))

    #
    # OBU Vendor
    #
    if port == 5560:
      # Panasonic
      self.log_debug("\tPanasonic C-V2X ")
      self.parse_j2735(data)
    elif port == 9000 or port == 9001:
      # Panasonic
      self.log_debug("\tCohda C-V2X")
      if (port == 9000):
        self.is_tx = 0
      else:
        self.is_tx = 1
      self.parse_wsmp(data[1:])
    elif port == 7943:
      # Commsignia UDP
      self.log_debug("\tCommsignia C-DSRC")
      if len(data) >= 60:
        if data[60] == 0x88 and data[61] == 0xDC:
          self.parse_wsmp(data[62:])
    elif port == 37008:
      self.parse_tazman(data)
    elif port == 40021:
      self.log_debug("\tWistron")
      try:
        wsm = re.split(b'\x88\xDC', data)[1]
        self.parse_wsmp(wsm)
      except:
        pass
    #
    # RSU
    #
    elif port == 1516:
      # IFM
      self.log_debug("\tRSU IFM")
      ifm = data.splitlines()
      is_map = 0
      is_spat = 0
      for line in ifm:
        line = line.decode("utf-8")
        if line[:1] == "#":
            continue
        (key,val) = line.split("=")
        if (key == "Type" and val == "MAP"):
          is_map = 1
        elif (key == "Type" and val == "SPAT"):
          is_spat = 1
        elif (key == "Tx Channel"):
          self.chan_no = int(val)
        elif (key == "Payload" and (is_map or is_spat)):
          data = binascii.unhexlify(val)
          self.raw_tx_packet(data)
    #
    # DENSO WSU BSMP/OTAP
    # CAMP TOSCo/CACC ports 4200-4202 (removed), 4300 raw MAP/SPAT
    # NTCNA ports 2734-2738
    #
    elif port == 2734 or port == 2736 or port == 2737:
      # port 2734 is used with DENSO
      # BSMP broadcase WSU -> * (DWMHWsmObe2PcPort2)
      # 2736-2737 broadcast is used with Cohda
      self.log_debug("\tWSU BSMP Broadcast")
      if data[0]==1 and leng==330:  # TXE
        self.bsmp_tx_packet(data)
      elif data[0]==2 and leng==358:  # RX
        self.bsmp_rx_packet(data)
    elif port == 4300:
      # CAMP DENSO WSU OTAP, configured to send raw MAP/SPAT only
      # dotapUDPIPAddress, dotapUDPPortAddress = 4300,
      # dotapUDPMapOutputEnable, dotapUDPSPaTOutputEnable both set to 1
      self.log_debug("\tWSU OTAP Raw MAP, SPAT RX")
      self.raw_rx_packet(data[6:])
    #
    # Other UDP port with RX data
    #
    elif (port == 1034 or port == 6053 or port == self.udp_port) and data[0] == 0xcd:
      # Signal controller dump to Battelle's TSCBM format (for CTIC T&V)
      self.log_debug("\tBattelle TSCBM (%d)" % leng)
      logfile = os.path.join(self.logpath, "tscbm.json")
      with open(logfile, 'a') as fp:
        # JSON
        fp.write(json.dumps(parse_TSCBM('10', data, float(self.timestamp)/1000.0), separators=(',', ':')))
        fp.write("\n")
        fp.close()
        self.count += 1
        self.tscbm_count += 1
        if self.debug_on:
          binfile = os.path.join(self.logpath, "tscbm.bin")
          with open(binfile, 'ab') as fp:
            fp.write(data)
            fp.close()
    #
    # UDP port, offset option
    #
    elif self.udp_port and port == self.udp_port:
      try:
        self.log_debug("\tUDP J2735 Data")
        self.parse_j2735(data[self.offset_bytes:])
      except:
        self.log_debug("\tUDP Data: %s" % (str(binascii.hexlify(data))))
    #
    # fallback
    #
    else:
      self.log_debug("\tUDP: WSMP Search")
      try:
        wsm = re.split(b'\x88\xDC', data)[1]
        self.parse_wsmp(wsm)
      except:
        pass

###############################################################################
# WSMP
###############################################################################

  #
  # WSMP layer
  #
  def parse_wsmp(self, pkt):
    extver = pkt[0]
#    subtype = extver >> 4
    option = (extver & 0b00001000) >> 3
    extver = extver & 0x07

    self.log_debug("WSMP Layer V%d (%u):" % (extver, len(pkt)))

    # WSMP v3 only  
    self.wsmp_layer = extver
    if extver != 3:
      return
    index = 1

    # N-Header
    if option:
      count = pkt[index]
      index += 1

      while count:
        elem = pkt[index] & 0xff
        index += 1

        (elen, leng) = wsmp_parse_length(pkt[index:])
        index += leng

        val = pkt[index] & 0xff
        index += 1
        elen -= 1
        while elen:
          val = val << 8
          val = val | (pkt[index] & 0xff)
          index += 1
          elen -= 1

        if elem == 4:
          self.tx_pwr = val
        elif elem == 15:
          self.chan_no = val
        elif elem == 16:
          self.data_rate = val
        elif elem == 23:
          self.chan_load = val
        count -= 1

      self.log_debug("\tWSMP N-Header: pwr=%d, chan=%d, rate=%d, load=%d" % (self.tx_pwr, self.chan_no, self.data_rate, self.chan_load))

    # WSMP-T-Header
    # tpid
    tpid = pkt[index]
    index += 1
    # psid
    (psid, leng) = wsmp_parse_pcoded(pkt[index:])
    index += leng
    self.log_debug("\tWSMP T-Header TPID=0x%x, PSID=0x%x" % (tpid, psid))
    self.psid_actual = psid
  
    (wsm_len, leng) = wsmp_parse_length(pkt[index:])
    index += leng
    self.log_debug("\tWSMP Payload %u (%u remaining)" % (wsm_len, len(pkt)-index))
  
    # BSMs, MAPs, SPATS and RTCM
    if psid >= PSID_TRAFFIC_SIGNAL and psid <= PSID_ROAD_MAPPING:
      # New in 2023: RGA, SRM, SSM
      self.parse_p1609(pkt[index:])
    elif psid == PSID_VEHICLE or psid == PSID_INTERSECTION:
      # BSM, MAP, SPAT
      self.parse_p1609(pkt[index:])
    elif psid == PSID_CORRECTIONS or psid == (PSID_CORRECTIONS+1):
      # RTCM, NMEA
      self.parse_p1609(pkt[index:])
    elif psid == PSID_TRAVELER:
      self.parse_p1609(pkt[index:])
#      self.log_debug("\tUndecoded PSID: %04x Traveler Information and Roadside Signage" % (psid))
    elif psid == PSID_EMERGENCY:
      self.log_debug("\tUndecoded PSID: %04x Emergency Vehicles" % (psid))
    elif psid == PSID_WAVE_ADVERT:
      self.log_debug("\tUndecoded PSID: %04x WAVE Advertisement" % (psid))
    elif psid >= PSID_CV_PILOT_MIN and psid <= PSID_CV_PILOT_MAX:
      # damn CV Pilot
      self.log_debug("\tCV Pilot PSID %06x" % (psid))
      self.parse_p1609(pkt[index:])      
      self.cv_pilot_count += 1
    else:
      self.log_debug("\tUnrecognized PSID!: %0x04x" % (psid))

###############################################################################
# 802.11
###############################################################################

  def parse_802_11(self, pkt):
    # not sure what the proper way is to walk this
    # fortunately 802.11 layer is constant size (26 bytes)
    self.log_debug("Parsing 802.11 Layer:")
      
    # WAVE (2 byte LLC)
    if pkt[0] == 0x88 and pkt[26] == 0x88 and pkt[27] == 0xdc:
      # check WSMP layer
      self.parse_wsmp(pkt[28:])

  def parse_radiotap(self, pkt):
    self.log_debug("Parsing Radiotap Header:");
    # check
    if pkt[0] or pkt[1]:
      return

    # would be nice to get a full decode to print

    # size    
    leng = pkt[3] << 8 | pkt[2]
    if leng <= 0:
      return

    self.parse_802_11(pkt[leng:])

###############################################################################
# Ethernet
###############################################################################

  def parse_ipv4(self, ip_pkt):
    self.log_debug("IPv4 Layer:")
    if ip_pkt.proto == 0x11:
       udp_pkt = ip_pkt[UDP]
       self.parse_udp(udp_pkt)

  def parse_ipv6(self, ip_pkt):
    self.log_debug("IPv6 Layer:")
    if ip_pkt.proto == 0x11:
      self.parse_udp(ip_pkt[UDP])

  def parse_ethernet(self, pkt):
    self.log_debug("Parsing Ethernet Layer:")
    
    # Ethernet packet
    ether_pkt = Ether(pkt)
    
    # IPv4
    if ether_pkt.type == 0x0800:
      ip_pkt = ether_pkt[IP]
      self.parse_ipv4(ip_pkt)
    
    # IPv6
    elif ether_pkt.type == 0x86dd:
      ip_pkt = ether_pkt[IPv6]     
      self.parse_ipv6(ip_pkt)
  
  def parse_cooked(self, pkt):
    ip = pkt[16:]
    if pkt[14] == 0x08 and pkt[15] == 0x00:      
      self.log_debug("Parsing Linux Cooked:");
      self.log_debug("\tIPv4 Layer:");
      if ip[6] == 0x11:
        self.parse_udp(ip[40:])
      return 1
    elif pkt[14] == 0x86 and pkt[15] == 0xdd:
      self.log_debug("Parsing Linux Cooked:");
      self.log_debug("\tIPv6 Layer:");
      if ip[6] == 0x11:
        self.parse_udp(ip[40:])
      return 1
    return 0
  
###############################################################################
# BIN
###############################################################################

  def parse_binfile(self, file):
    super().log_write("HEX Input: " + file)
    self.log_debug("Parsing BIN File: %s" % (file))
    
    with open(file, 'b') as fp:
      data = fp.read()
      self.raw_rx_packet(data)
      fp.close()

###############################################################################
# HEX
###############################################################################

  def parse_hexfile(self, file):
    super().log_write("HEX Input: " + file)
    self.log_debug("Parsing HEX File: %s" % (file))
    
    with open(file) as fp:
      line = fp.readline()
      while line:
        self.count += 1
        data = binascii.unhexlify(line)
        self.raw_rx_packet(data)
        line = fp.readline()
      fp.close()

    print('{} contains {} packets'.format(file, self.count))

###############################################################################
# JSON
###############################################################################

  # eTrans format
  def parse_json_file(self, file):
#   super().log_write("JSON Input: " + file)
    self.log_debug("Parsing JSON File: " + file)
    self.count = 0
    
    with open(file) as fp:
      line = fp.readline()
      while line:
        data = json.loads(line)
        
        # eTrans format
        if "hexMessage" in data:
          self.log_debug("Packet %u (%u)" % (self.count, len(data)))
          self.timestamp = int(data['timeStamp'])
          direction = data['dir']
          hexdata = data['hexMessage']
          bindata = binascii.unhexlify(hexdata)
          if direction =='S':
            self.raw_tx_packet(bindata)
          else:
            self.raw_rx_packet(bindata)
          self.count += 1
        else:
          print("\tUnrecognized JSON format!")
          break
        line = fp.readline()
      fp.close()

    super().log_write("\tcontained %u packets" % (self.count))
 
###############################################################################
# PCAP
###############################################################################

  def parse_pcap_time(self, pkt_metadata):
    # PCAP timestamp
    try:
      self.timestamp = (pkt_metadata.sec * 1000) + (pkt_metadata.usec // 1000)
    except:
      self.timestamp = ((pkt_metadata.tshigh << 32) | pkt_metadata.tslow) // (pkt_metadata.tsresol/1000)
    self.timestamp = int(self.timestamp)

  def parse_pcap_packet(self, pkt_data):
    # Raw Ethernet
    if pkt_data[0] == 0xff and pkt_data[1] == 0xff and pkt_data[2] == 0xff and pkt_data[3] == 0xff and pkt_data[4] == 0xff and pkt_data[5] == 0xff:
      self.log_debug("\nPacket %u (%u)" % (self.count, len(pkt_data)))
      self.log_debug("\tTimestamp = %u" % self.timestamp)

      # RX or TX?
      if pkt_data[6] == 0xff and pkt_data[7] == 0xff and pkt_data[8] == 0xff and pkt_data[9] == 0xff and pkt_data[10] == 0xff and pkt_data[11] == 0xff:
        self.is_tx = 1
      else:
        self.is_tx = 0

      # DENSO Hercules custom (Savari custom, went out of business)
      if pkt_data[12] == 0x88 and pkt_data[13] == 0xdc:
        self.log_debug("C-V2X Custom:")
        self.parse_wsmp(pkt_data[14:])
        return
      # Cohda custom
      if pkt_data[14] == 0x88 and pkt_data[15] == 0xdc:
        self.log_debug("Cohda Custom:")
        self.parse_wsmp(pkt_data[16:])
        return
   
    # Radiotap
    if pkt_data[0] == 0x00 and pkt_data[1] == 0x00:
      self.log_debug("\nPacket %u (%u)" % (self.count, len(pkt_data)))
      self.log_debug("\tTimestamp = %u" % self.timestamp)
      
      # check for cooked
      if self.parse_cooked(pkt_data):
        return
      
      # check for others
      if pkt_data[12] == 0x08 and pkt_data[13] == 0x00:
        # Commsignia
        self.parse_ethernet(pkt_data)
      elif pkt_data[12] == 0x88 and pkt_data[13] == 0xdc:
        self.log_debug("C-V2X Yunex:")
        self.parse_wsmp(pkt_data[14:])
      else:
        # DENSO (old, should deprecate)
        self.parse_radiotap(pkt_data)
      return
    # Linux cooked
    elif pkt_data[0] == 0x00 and pkt_data[1] == 0x04:
      if self.parse_cooked(pkt_data):
        return
      if pkt_data[12] == 0x88 and pkt_data[13] == 0xdc:
        self.log_debug("C-V2X Unknown:")
        self.parse_wsmp(pkt_data[14:])

    # Ethernet packet
    ether_pkt = Ether(pkt_data)
    if 'type' not in ether_pkt.fields:
      # LLC frames will have 'len' instead of 'type'
      # disregard
      return

    self.log_debug("\nPacket %04x %u (%u)" % (ether_pkt.type, self.count, len(pkt_data)))
    self.log_debug("\tTimestamp = %u" % self.timestamp)
    
    # IPv4 on raw frame (Panasonic/Codha)
    if pkt_data[0] == 0x45 and pkt_data[9] == 0x11:
      self.log_debug("Raw frame with IPv4 + UDP")
      self.parse_udp(pkt_data[20:])

    # ethernet
    elif pkt_data[12] == 0x08 and pkt_data[13] == 0x00:
      # IPv4 UDP
      self.log_debug("Ethernet frame")
      self.parse_ethernet(pkt_data)
    elif pkt_data[0] == 0xff or pkt_data[0] == 0x00:
      # IPv4/6, UDP
      self.log_debug("Ethernet frame")
      self.parse_ethernet(pkt_data)

    # wireless
    elif pkt_data[0] == 0x88:
      self.log_debug("Wireless 802.11 frame")
      self.parse_802_11(pkt_data)

    # fallback    
    else:
      self.log_debug("\tPCAP WSMP Search")
      try:
        wsm = re.split(b'\x88\xDC', pkt_data)[1]
        self.parse_wsmp(wsm)
      except:
        pass
    
  def parse_pcap_file(self, file): 
    super().log_write("PCAP Input: " + file)
    self.log_debug("Parsing PCAP File: " + file)
    self.count = 0

    packet_count = 0
    for (pkt_data, pkt_metadata,) in RawPcapNgReader(file):
      packet_count += 1
    if packet_count == 0:
      packet_count = size // 168 # hack which uses 156 for est. packet size  
    size = os.stat(file).st_size
    
    for (pkt_data, pkt_metadata, ) in tqdm(RawPcapNgReader(file), total=packet_count, unit="Pkt"):
      # timestamp
      self.parse_pcap_time(pkt_metadata)

      # PCAP data
      self.parse_pcap_packet(pkt_data)
      self.total += 1
    
    super().log_write("\tcontained %u useful/%u total packets (%u bytes average)" % (self.count, packet_count, size/packet_count))

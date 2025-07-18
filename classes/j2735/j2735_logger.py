#!/usr/bin/env python3

import os
import sys
from socket import *
from struct import unpack
from time import time
import threading

from j2735_mf import j2735_mf
from utils.logging import JSONlog, log_genname

from j2735_logcore import j2735_logcore

#
# default ports
#
bsm_rx_port = 9000  # All J2735 RX
bsm_tx_port = 9001  # BSM J2735 TX only
dvi_port = 2738

logger_stop_event = threading.Event()

class j2735_logger(j2735_logcore):
  def __init__(self):
    super().__init__()
    
    # logging
    self.obu_flag = 0
    self.wsu_name = "192.168.2.2"
    
    # sockets
    self.udpTX = 0
    self.udpRX = 0
    self.udpDVI = 0
    self.socks = ()
    
    # threads
    self.logging = 0
    self.running = 0
    self.threaded = 0
    self.threadTX = 0
    self.threadRX = 0
    self.threadDVI = 0
    self.threads = ()

#
# start/stop
#
  def start_logging(self, obu_flag=0):
    if obu_flag:
      self.obu_flag = obu_flag
    self.open_logging()
    self.start_children(obu_flag)

  def stop_logging(self):
    self.stop_children()
    self.close_logging()
    self.close_sockets()

#
# log file
#    
  def open_logging(self):
    if self.logging:
      return
    super().log_open()
    # WSU stuff
    if self.obu_flag & 2:
      # 192.168.1.2 wsu in /etc/hosts file
      if gethostbyname('wsu'):
        self.wsu_name = "wsu"
      response = os.system("ping -c 1 -w2 " + self.wsu_name + " > /dev/null 2>&1")
      if response == 0:
        # remove old files
        os.system("ssh root@" + self.wsu_name + ' "rm /mnt/microsd/pktlogs/*"')
        os.system("ssh root@" + self.wsu_name + ' "rm /mnt/microsd/V2V-I/applogs/*"')
        os.system("ssh root@" + self.wsu_name + ' "rm /mnt/microsd/V2V-I/dbglogs/*"')
      else:
        print("WSU is offline!")
        super().log_write("WARNING: WSU is offline")
    self.logging = 1

  def close_logging(self):
    if not self.logging:
      return
    # WSU stuff
    if self.obu_flag & 2:
      response = os.system("ping -c 1 -w2 " + self.wsu_name + " > /dev/null 2>&1")
      if response == 0:
        os.system("scp root@" + self.wsu_name + ":/mnt/microsd/pktlogs/* " + self.logdir)
        os.system("scp root@" + self.wsu_name + ":/mnt/microsd/V2V-I/applogs/* " + self.logdir)
        os.system("scp root@" + self.wsu_name + ":/mnt/microsd/V2V-I/dbglogs/* " + self.logdir)
      else:
        print("WSU is offline!")
        super().log_write("WARNING: WSU was offline")
    super().log_close()
    # clean up empty files
    os.system("find " + self.logdir + " -size 0 -delete")
    self.logging = 0
    
#
# sockets
#
  def open_sockets(self, obu_flag=0):
    #
    # socket and handler
    #
    self.udpTX = socket(AF_INET, SOCK_DGRAM)
    self.udpTX.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    self.udpTX.bind(('', bsm_tx_port))   # J2735 UDP Broadcast TX

    self.udpRX = socket(AF_INET, SOCK_DGRAM)
    self.udpRX.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    self.udpRX.bind(('', bsm_rx_port))   # J2735 UDP Broadcast RX

    self.udpDVI = socket(AF_INET, SOCK_DGRAM)
    self.udpDVI.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    self.udpDVI.bind(('', dvi_port))   # DVI Packet

    self.socks = [self.udpTX, self.udpRX, self.udpDVI]

  def close_sockets(self):
    for i in self.socks:
      i.close()
    self.socks = ()
  
#
# socket threads
#
  def start_children(self, obu_flag=0):
    if self.running:
      return
    self.open_sockets(obu_flag)
    self.running = 1
    
    if not self.threaded:
      self.threadTX = threading.Thread(target=self.bsm_tx_child)
      self.threadRX = threading.Thread(target=self.bsm_rx_child)
      self.threadDVI = threading.Thread(target=self.dvi_child)
      self.threaded = 1
    
    # start all these forever threads
    self.threadTX.start()
    self.threadRX.start()
    self.threadDVI.start()
    self.threads = [self.threadTX, self.threadRX, self.threadDVI]
    
    if os.path.isfile('/dev/can0'):
      self.threadCAN = threading.Thread(target=self.can_child, daemon=True)
      self.threadCAN.start()
      self.threads.append(self.threadCAN)
    self.threadUDP = threading.Thread(target=self.udp_child, daemon=True)
    self.threadUDP.start()
    self.threads.append(self.threadUDP)

  def stop_children(self):
    if not self.running:
      return
    self.running = 0
    if not self.threaded:
      return

    # signal event
    logger_stop_event.set()

    if os.path.isfile('/dev/can0'):
      os.system("killall -9 candump")
    if self.threadUDP.is_alive():
      os.system("sudo killall -9 tcpdump")

    for i in self.threads:
      if i.is_alive():
        i.join()

  def bsm_tx_child(self, stop_event):
    while self.running:
      try:
        self.udpTX.settimeout(0.5)
        data, addr = self.udpTX.recvfrom(2048)
        self.timestamp = int(time() * 1000)
        self.raw_tx_packet(data)
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

  def bsm_rx_child(self):
    while self.running:
      try:
        self.udpRX.settimeout(0.5)
        data, addr = self.udpRX.recvfrom(2048)
        self.timestamp = int(time() * 1000)
        self.raw_rx_packet(data)
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

  def dvi_child(self):
    while self.running:
      # OTAP or J2735 MAP+SPAT+RTCM packet from WSU
      self.udpDVI.settimeout(0.5)
      data, addr = self.udpDVI.recvfrom(2048)
      self.udpDVI.sendto(data,('192.168.1.10', 2738))   # -> MABX

      try:
        self.udpDVI.settimeout(0.5)
        data, addr = self.udpDVI.recvfrom(2048)
        # TBD
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

  def can_child(self):
    # TBD detect CAN device
    file = log_genname("", "candump-", "txt")
    super().log_write("CAN Output: " + file)
    os.system("candump -L any > " + file)

  def udp_child(self):
    file = log_genname("", "udpdump-", "pcap")
    super().log_write("UDP Output: " + file)
    os.system("sudo tcpdump -i eth0 -w " + file + " udp dst portrange 2734-2739")


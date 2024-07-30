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
pcap1_port = 8023
pcap2_port = 8024

logger_stop_event = threading.Event()

class j2735_logger(j2735_logcore):
  def __init__(self):
    super().__init__()
    
    # logging
    self.obu_flag = 0
    self.wsu_name = "192.168.2.2"
    
    # sockets
    self.sock0 = 0
    self.sock1 = 0
    self.sock2 = 0
    self.sock3 = 0
    self.sock4 = 0
    self.sock7 = 0
    self.sock8 = 0
    self.sock23 = 0
    self.sock24 = 0
    self.socks = ()
    
    # threads
    self.logging = 0
    self.running = 0
    self.threaded = 0
    self.thread0 = 0
    self.thread1 = 0
    self.thread2 = 0
    self.thread3 = 0
    self.thread4 = 0
    self.thread7 = 0
    self.thread8 = 0
    self.thread23 = 0
    self.thread24 = 0
    self.thread12 = 0
    self.thread13 = 0
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
    if obu_flag & 1:
      self.sock2 = socket(AF_INET, SOCK_DGRAM)
      self.sock2.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      self.sock2.bind(('', bsm_tx_port))   # J2735 UDP Broadcast TX

      self.sock3 = socket(AF_INET, SOCK_DGRAM)
      self.sock3.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      self.sock3.bind(('', bsm_rx_port))   # J2735 UDP Broadcast RX

      self.sock8 = socket(AF_INET, SOCK_DGRAM)
      self.sock8.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      self.sock8.bind(('', dvi_port))   # DVI Packet

      self.socks = [self.sock2, self.sock3, self.sock8]
    elif obu_flag & 2:
      # DENSO WSU specific
      self.sock23 = socket(AF_INET, SOCK_DGRAM)
      self.sock23.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      self.sock23.bind(('', pcap1_port))   # PCAP Packet

      self.sock24 = socket(AF_INET, SOCK_DGRAM)
      self.sock24.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      self.sock24.bind(('', pcap2_port))   # PCAP Packet

      self.socks = [self.sock4, self.sock7, self.sock23, self.sock24]

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
      self.thread0 = threading.Thread(target=self.raw_child)
      self.thread1 = threading.Thread(target=self.header_child)
      self.thread2 = threading.Thread(target=self.bsm_tx_child)
      self.thread3 = threading.Thread(target=self.bsm_rx_child)
      self.thread8 = threading.Thread(target=self.dvi_child)
      self.thread23 = threading.Thread(target=self.pcap1_child)
      self.thread24 = threading.Thread(target=self.pcap2_child)
      self.threaded = 1
    
    # start all these forever threads
    if obu_flag & 1:
#      self.thread0.start()
#      self.thread1.start()
      self.thread2.start()
      self.thread3.start()
      self.thread8.start()
      self.threads = [self.thread2, self.thread3, self.thread8]
    elif obu_flag & 2:
      self.thread4.start()
      self.thread7.start()
      self.thread23.start()
      self.thread24.start()
      self.threads = [self.thread4, self.thread7, self.thread23, self.thread24]
    
    if os.path.isfile('/dev/can0'):
      self.thread12 = threading.Thread(target=self.can_child, daemon=True)
      self.thread12.start()
      self.threads.append(self.thread12)
    self.thread13 = threading.Thread(target=self.udp_child, daemon=True)
    self.thread13.start()
    self.threads.append(self.thread13)

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
    if self.thread13.is_alive():
      os.system("sudo killall -9 tcpdump")

    for i in self.threads:
      if i.is_alive():
        i.join()

  def raw_child(self):
    while self.running:
      try:
        self.sock0.settimeout(0.5)
        data, addr = self.sock0.recvfrom(2048)
        self.timestamp = int(time() * 1000)
        self.raw_rx_packet(data)
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

  def header_child(self):
    while self.running:
      try:
        self.sock1.settimeout(0.5)
        data, addr = self.sock1.recvfrom(2048)
        self.hdr_packet(data)
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

  def bsm_tx_child(self, stop_event):
    while self.running:
      try:
        self.sock2.settimeout(0.5)
        data, addr = self.sock2.recvfrom(2048)
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
        self.sock3.settimeout(0.5)
        data, addr = self.sock3.recvfrom(2048)
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
      self.sock8.settimeout(0.5)
      data, addr = self.sock8.recvfrom(2048)
      self.sock8.sendto(data,('192.168.1.10', 2738))   # -> MABX

      try:
        self.sock8.settimeout(0.5)
        data, addr = self.sock8.recvfrom(2048)
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
    os.system("sudo tcpdump -i eth0 -w " + file + " udp dst portrange 2730-2739")

  def pcap1_child(self):
    while self.running:
      try:
        self.sock23.settimeout(0.5)
        data, addr = self.sock23.recvfrom(2048)
        self.timestamp = int(time() * 1000)
        
        self.pcap_parsepacket(data, 0)
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

  def pcap2_child(self):
    while self.running:
      try:
        self.sock24.settimeout(0.5)
        data, addr = self.sock24.recvfrom(2048)
        self.timestamp = int(time() * 1000)

        self.pcap_parsepacket(data, 1)
      except socket.timeout:
        pass
      except Exception as e:
        print (e)
        break

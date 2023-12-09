from struct import unpack

from j2735_bsm import j2735_bsm

import datetime, time

#
# BSMP Message (DENSO WSU)
# note that we don't bother with PathHistory as we don't use it
#
class BSMP():
  def __init__(self):
    # time stamp
    self.timestamp = 0
    self.conversion = 1

    # BSMP headers
    self.msg = 0
    self.sib = 0
    self.tcb = 0
    self.toda = 0
    self.roda = 0

    # BSMP data
    self.msgcnt = 0
    self.id = 0
    self.secmark = 0
    self.lat = 0.0
    self.long = 0.0
    self.elev = 0.0
    self.acc = 0.0
    self.heading = 0.0
    self.steering = 0.0
    self.longaccel = 0.0
    self.lataccel = 0.0
    self.vertaccel = 0.0
    self.yawrate = 0.0
    self.brakes = 0
    self.throttle = 0.0
    self.ppradius = 0.0
    self.event = 0
    self.lights = 0
    self.wipers = 0
    # extracted
    self.speed = 0
    self.trans = 0
    self.width = 0
    self.length = 0

  # TX echo message from WSU
  def decode_txe(self, txe):
    # unpack TXE header
    self.msg, self.tcb, self.toda = unpack('!BHB', txe[0:4])
    return (self.msg, self.tcb, self.toda)

  # RX message from WSU
  def decode_sib(self, rx):
    # unpack SIB header
    self.msg, self.sib, year, month, day, hour, minute, second, self.lat, self.long, self.elev, gps, self.heading, dvi, vod, self.roda = unpack('!BBHBBBBHllHLHBLB', rx[0:32])
    tm = datetime.datetime(year, month, day, hour, minute, int(second/1000), int(second%1000))
    self.timestamp = time.mktime(tm.timetuple())
    return (self.msg, self.sib, self.timestamp, self.lat, self.long, self.elev, gps, self.heading, dvi, vod, self.roda)

  def get_ts(self):
    return self.timestamp

  # for OLD apps only, like bsmp_monitor.py
  def decode_bsmp(self, bsm):
    # Part I
    self.msgcnt, self.id, self.secmark, self.lat, self.long, self.elev, self.acc, speedtr, self.heading, self.steering, self.longaccel, self.lataccel, self.vertaccel, self.yawrate, self.brakes, vs1, vs2, vs3, self.event = unpack('!BLHllhLHHbhhbhHBBBH', bsm[0:40])
    # Part II (skip PH)
    self.ppradius, self.ppconf, self.lights, self.throttle, self.wipers = unpack('!hBBBB', bsm[-9:-3])

    # unpack combo
    self.width = (vs1<<2|vs2>>6)
    self.length = ((vs2&0x3f)<<8|(vs3&0xff))

    self.speed = (speedtr & 0x1fff)
    self.trans = (speedtr >> 13) & 0x07

    # convert data
    if self.conversion:
      self.id &= 0xffff
      self.lat /= 10e6
      self.long /= 10e6
      self.elev *= 0.1
      self.heading *= 0.0125
      self.speed *= 0.02
      self.steering *= 1.5
      self.longaccel *= 0.01
      self.lataccel *= 0.01
      self.vertaccel *= 0.02
      self.yawrate *= 0.01
      self.width *= 0.01
      self.length *= 0.01
      self.ppradius *= 0.1

    return self.values()

  # for OLD apps only
  def values(self):
    return (self.msgcnt, self.secmark, self.id, self.lat, self.long, self.elev, self.speed, self.trans, self.heading, self.steering, self.longaccel, self.lataccel, self.yawrate, self.brakes, self.width, self.length, self.event, self.lights, self.throttle, self.wipers, self.ppradius)

  # encode new BSM
  def encode_bsm(self):
    bsm = j2735_bsm()
    coreData = bsm.data['value']['coreData']
    coreData['msgCnt'] = self.msgcnt
    coreData['secMark'] = self.secmark
    coreData['id'] = self.id
    coreData['lat'] = self.lat
    coreData['long'] = self.long
    coreData['elev'] = self.elev
    coreData['heading'] = self.heading
    coreData['speed'] = self.speed
    if coreData['angle'] != 127:  # 127 when it is unavailable
      coreData['angle'] = self.steering
    else:
      coreData['angle'] = 0.0

    coreData['accelSet']['long'] = self.longaccel
    coreData['accelSet']['lat'] = self.lataccel
    coreData['accelSet']['vert'] = self.vertaccel
    coreData['accelSet']['yaw'] = self.yawrate

    # 2 bytes in old 2009 format
    brakes = coreData['brakes']
    brakes['wheelBrakes'] = (self.brakes & 0xf000) >> (12-1)
    brakes['traction'] = (self.brakes >> 8) & 3
    brakes['abs'] = (self.brakes >> 6) & 3
    brakes['scs'] = (self.brakes >> 4) & 3
    brakes['brakeBoost'] = (self.brakes >> 2) & 3
    brakes['auxBrakes'] = self.brakes & 3

    vehSize = coreData['size']
    vehSize['width'] = self.width
    vehSize['length'] = self.length

    # no PH or PP as we (NTCNA) don't use it

    return bsm.data

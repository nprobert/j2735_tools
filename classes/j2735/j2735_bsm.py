
# class
from j2735_mf import *
from j2735_msg import j2735_msg
from j2735 import BasicSafetyMessage
import json

#
# data
#
_init_data_ = {
        'coreData':
            {
                'id': "00000000",
                'msgCnt': 0,
                'secMark': 0,
                'lat': 90.0,
                'long': 180.0,
                'elev': 0.0,
                'accuracy': {'semiMajor': 0, 'semiMinor': 0, 'orientation': 0},
                'transmission': 'unavailable',
                'speed': 0.0,
                'heading': 0.0,
                'angle': 0.0,
                'accelSet': {'lat': 0.0, 'long': 0.0, 'vert': 0.0, 'yaw': 0.0},
                'brakes': {
                  'wheelBrakes': "00",
                  'traction': 'unavailable',
                  'abs': 'unavailable',
                  'scs': 'unavailable',
                  'brakeBoost': 'unavailable',
                  'auxBrakes': 'unavailable'
                  },
                'size': {'length': 5.0, 'width': 2.0},
            }
#        , 'partII': [
#            {'partII-Id': 0, 'partII-Value': {
#                        'pathHistory': {'crumbData': [{
#                          'latOffset':0.0,
#                          'longOffset':0.0,
#                          'elevationOffset':0.0,
#                          'timeOffset':1
#                          }]
#                          },
#                        'pathPrediction': {'confidence': 0, 'radiusOfCurve': 3276.7}
#                        }
#              }
#            ]
    }

#
# class
#
class j2735_bsm(j2735_msg):
  def __init__(self):
    super().__init__()
    self.data['messageId'] = 20
    self.data['value'] = _init_data_

  def message(self, msg):
    # BSM data (from MF)
    if self.data['messageId'] == MESSAGE_BSM:
      self.raw = msg
      self.data = msg.copy()
      self.convert()
      return self.data
    return {}

  def convert(self):
    value = self.data['value']
    coreData = value['coreData']
    coreData['id'] = int(coreData['id'], 16) & 0xffff
    coreData['lat'] /= 10e6
    coreData['long'] /= 10e6
    coreData['elev'] *= 0.1
    coreData['heading'] *= 0.0125
    coreData['speed'] *= 0.02
    if coreData['angle'] != 127:  # 127 when it is unavailable
      coreData['angle'] *= 1.5
    else:
      coreData['angle'] = 0.0
    accelSet = coreData['accelSet']
    accelSet['long'] *= 0.01
    accelSet['lat'] *= 0.01
    accelSet['vert'] *= 0.02
    accelSet['yaw'] *= 0.01
    vehSize = coreData['size']
    vehSize['width'] *= 0.01
    vehSize['length'] *= 0.01
    if 'partII' in value:
      partII = value['partII']
      for part in partII:
        if part['partII-Id'] == 0:
          part_val = part['partII-Value']
          PP = part_val['pathPrediction']
          PP['radiusOfCurve'] *= 0.1
          PH = part_val['pathHistory']
          if 'crumbData' in PH:
            for crumb in PH['crumbData']:
              crumb['latOffset'] /= 10e6
              crumb['longOffset'] /= 10e6
              crumb['elevationOffset'] *= 0.1
              if 'timeOffset' in crumb:
                crumb['timeOffset'] /= 100.0 # seconds
              if 'speed' in crumb:
                crumb['speed'] *= 0.02
              if 'heading' in crumb:
                crumb['heading'] *= 1.5
    return self.data

  def revert(self):
    self.raw = self.data.copy()
    value = self.raw['value']
    coreData = value['coreData']
#    coreData['id'] &= 0xffff
    coreData['lat'] = int(coreData['lat'] * 10e6)
    coreData['long'] = int(coreData['long'] * 10e6)
    coreData['elev'] = int(coreData['elev'] / 0.1)
    coreData['heading'] = int(coreData['heading'] / 0.0125)
    coreData['speed'] = int(coreData['speed'] / 0.02)
    coreData['angle'] = int(coreData['angle'] / 1.5)
    accelSet = coreData['accelSet']
    accelSet['long'] = int(accelSet['long'] / 0.01)
    accelSet['lat'] = int(accelSet['lat'] / 0.01)
    accelSet['vert'] = int(accelSet['vert'] / 0.02)
    accelSet['yaw'] = int(accelSet['yaw'] / 0.01)
    vehSize = coreData['size']
    vehSize['width'] = int(vehSize['width'] / 0.01)
    vehSize['length'] = int(vehSize['length'] / 0.01)
    if 'partII' in value:
      partII = value['partII']
      for part in partII:
        if part['partII-Id'] == 0:
          part_val = part['partII-Value']
          PP = part_val['pathPrediction']
          PP['radiusOfCurve'] = int(PP['radiusOfCurve'] / 0.1)
          PH = part_val['pathHistory']
          if 'crumbData' in PH:
            for crumb in PH['crumbData']:
              crumb['latOffset'] = int(crumb['latOffset'] * 10e6)
              crumb['longOffset'] = int(crumb['longOffset'] * 10e6)
              crumb['elevationOffset'] = int(crumb['elevationOffset'] / 0.1)
              if 'timeOffset' in crumb:
                crumb['timeOffset'] = int(crumb['timeOffset'] * 100.0)
              if 'speed' in crumb:
                crumb['speed'] = int(crumb['speed'] / 0.02)
              if 'heading' in crumb:
                crumb['heading'] = int(crumb['heading'] / 1.5)


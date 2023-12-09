
from enum import Enum
import math

# ROS
from std_msgs.msg import Header
import rospy

# class
from j2735_bsm import j2735_bsm

# Use CARMA version
from j2735_msgs.msg import BSM

class DE_Transmission(Enum):
  eutral = 0
  park = 1
  forward = 2
  reverse = 3
  reserved1 = 4
  reserved2 = 5
  reserved3 = 6
  unavailable = 7

class DE_BrakeAppliedStatus(Enum):
  unavailable = 0
  leftFront = 1
  leftRear = 2
  rightFront = 3
  rightRear = 4

class DE_TractionControlStatus(Enum):
  unavailable = 0
  off = 1
  on = 2
  engaged = 3

class DE_AntiLockBrakeStatus(Enum):
  unavailable = 0
  off = 1
  on = 2
  engaged = 3

class DE_StabilityControlStatus(Enum):
  unavailable = 0
  off = 1
  on = 2
  engaged = 3

class DE_BrakeBoostApplied(Enum):
  unavailable = 0
  off = 1
  on = 2

class DE_AuxiliaryBrakeStatus(Enum):
  unavailable = 0
  off = 1
  on = 2
  reserved = 3
#
# data
#
#
# class
#
class j2735_ROSbsm(j2735_bsm):
  def __init__(self):
    super().__init__()

  def encode_ros(self):
    # ROS msg
    bsm = BSM()
    bsm.status = 0  # ok
    bsm.header = Header()
    bsm.header.stamp = rospy.Time.now()  # TODO should we use secMark?
    bsm.header.frame_id = "bsm-rx"

    data = super().get_data()
    coreData = data['coreData']
    bsm.temp_id = coreData["id"]
    bsm.latitude = coreData["lat"]
    bsm.longitude = coreData["long"]
    bsm.elevation = coreData["elev"]
    bsm.heading = math.radians(coreData["heading"])
    bsm.transmission = DE_Transmission[coreData["transmission"]].value
    bsm.speed = coreData["speed"]
    bsm.steering = math.radians(coreData['angle'])

    coreData_accelSet = coreData["accelSet"]
    bsm.accel_set.accel.x = coreData_accelSet["long"]
    bsm.accel_set.accel.y = coreData_accelSet["lat"]
    bsm.accel_set.accel.z = coreData_accelSet["vert"]
    bsm.accel_set.yaw_rate = coreData_accelSet["yaw"]

    coreData_brakes = coreData["brakes"]
    bsm.brakes.brake_applied_status = int(coreData_brakes["wheelBrakes"], 2)  # it is a bit string
    bsm.brakes.traction_control_status = DE_TractionControlStatus[coreData_brakes["traction"]].value
    bsm.brakes.antilock_brake_status = DE_AntiLockBrakeStatus[coreData_brakes["abs"]].value
    bsm.brakes.stability_control_status = DE_StabilityControlStatus[coreData_brakes["scs"]].value
    bsm.brakes.brake_boost_status = DE_BrakeBoostApplied[coreData_brakes["brakeBoost"]].value
    bsm.brakes.auxiliary_brake_status = DE_AuxiliaryBrakeStatus[coreData_brakes["auxBrakes"]].value

    coreData_size = coreData["size"]
    bsm.vehicle_size.width = coreData_size["width"]
    bsm.vehicle_size.length = coreData_size["length"]

    return bsm

  def publish_ros(self):
    bsm = self.encode_ros()
    rospy.loginfo(bsm)
    rospy.publish(bsm)

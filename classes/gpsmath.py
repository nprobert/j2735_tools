from math import sin, cos, asin, sqrt, radians

earth_flatening = 1.0/298.257223563
earth_radius = 6378137.0

def haversine(lat1, lon1, lat2, lon2):
  """
  Calculate the great circle distance between two points
  on the earth (specified in decimal degrees)
  """
  # convert decimal degrees to radians
  lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

  # haversine formula
  dlon = lon2 - lon1
  dlat = lat2 - lat1
  a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
  c = 2 * asin(sqrt(a))

  # 6367 km is the radius of the Earth
  return earth_radius * c

def roydistance(lat1, lon1, lat2, lon2):
  """
  Calculate the great circle distance between two points
  on the earth (specified in decimal degrees)
  """
  # convert decimal degrees to radians
  lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
  # Roy's method
  f1 = (1.0 - earth_flatening)

  top = (pow((lon2-lon1), 2) * pow(cos(lat1), 2)) + pow(lat2-lat1, 2)
  bot = pow(sin(lat1), 2) + (pow(f1, 2) * pow(cos(lat1), 2))

  return f1 * earth_radius * sqrt(top/bot)

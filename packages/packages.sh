#!/bin/bash

maj=$(python3 -c"import sys; print(sys.version_info.major)")
mjn=$(python3 -c"import sys; print(sys.version_info.minor)")

# Python 3
echo "Python 3 packages:"
# packages needed
sudo apt-get -y --ignore-missing install python3-all python3-dev python3-tk idle3 python3-pip pipx
sudo apt-get -y --ignore-missing install python3-ipython python3-debugpy python3-installer
sudo apt-get -y --ignore-missing install python3-virtualenv python3-virtualenvwrapper
sudo apt-get -y --ignore-missing install python3-pyside2.* python3-tk python3-pil.imagetk
sudo apt-get -y --ignore-missing install python3-tqdm python3-pykml python3-nmea2 python3-yaml
sudo apt-get -y --ignore-missing install python3-protobuf python3-scapy python3-serial
sudo apt-get -y --ignore-missing install canmatrix-utils python3-canmatrix
sudo apt-get -y --ignore-missing install python3-numpy python3-pandas python3-plotly python3-scipy
sudo apt-get -y --ignore-missing install rtklib rtklib-qt libasound2-dev python3-tqdm
sudo apt-get -y --ignore-missing install gpsd libgps-dev python3-gps python3-gpxpy gpsbabel
sudo apt-get -y --ignore-missing install python3-cycler python3-kiwisolver
if [ $mjn -lt 12 ]; then
  sudo apt-get -y remove python3-matplotlib
  python3 -m pip install --upgrade pip
else
  python3 -m pip install --upgrade pip --break-system-packages
fi
echo

# Python addons
echo "Python 3 modules:"

# modules
if [ $mjn -lt 12 ]; then
  p1="devscripts pyinstaller"
  p2="matplotlib simpleaudio"
  p3="maidenhead pykml"
else
  p1="devscripts"
  p2="simpleaudio"
  p3="maidenhead"
fi
p4="pyside6"
p5="pycrate"

for mod in $p1 $p2 $p3 $p4 $p5
do
  echo "Installing: $mod"
  echo "-------------------"
  if [ $mjn -lt 12 ]; then
    python3 -m pip install --upgrade $mod
  else
    python3 -m pip install --upgrade $mod --break-system-packages
  fi
  echo "==================="
  echo
done

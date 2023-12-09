#!/bin/bash

# Python 3
echo "Python 3 packages:"
# packages needed
sudo apt-get -y --ignore-missing install python3-all python3-dev python3-tk idle3 python3-pip python3-can python3-protobuf python3-numpy python3-pil.imagetk python3-pyside2.* python3-scapy pyside2-tools libasound2-dev tigervnc-viewer
sudo apt-get -y --ignore-missing install gpsd gpsbabel libgps-dev rtklib rtklib-qt
sudo apt-get -y remove python3-gps python3-matplotlib

# Python addons
echo "Python 3 modules:"
python3 -m pip install --upgrade pip pyinstaller
python3 -m pip install --upgrade ipython debugpy virtualenv virtualenvwrapper pyyaml tqdm simpleaudio
python3 -m pip install --upgrade pyside6 pyserial numpy numpydoc pandas plotly scipy
python3 -m pip install --upgrade gps gpxpy maidenhead pykml pynmea2 pyyaml tqdm simpleaudio
python3 -m pip install pycrate --upgrade

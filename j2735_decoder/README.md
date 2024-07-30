**Python J2735 Decoder**

**Python3 Package Requirements**
Python packages required: json, pycrate, pyside2, scapy

**Linux Installation**
Might have to use pip3:
1. sudo -H pip install --upgrade pip
2. sudo -H pip install json, numpy, pycrate, pyside2, scapy, virtualenv, virtualenvwrapper

Add classes and classes/j2735 to your PYTHONPATH: export PYTHONPATH=:./classes:./classes/j2735

**Linux Running**

./j2735_decoder.py [-d] file.pcap
./j2735_decoder.py [-d] file.log

Add -d for debugging output

This will create a subdirectory called "post" where the output data will be found.

**Windows Installation**

Using PowerShell Admin:
1. python -m pip install --upgrade pip
2. python -m pip install numpy, pyside2, scapy, virtualenv, virtualenvwrapper

Download and install pycrate:
1. git clone https://github.com/P1sec/pycrate
2. cd pycrate
3. python setup.py install

**Windows Running**
1. Change directoy to j2735_decoder directory
2. Run j2735_decoder.cmd with arguments

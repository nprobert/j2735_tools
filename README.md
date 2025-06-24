# j2735_tools
**Python3 based V2X PCAP Decoder to JSON Converter**

**Python3 Packages**
Python packages required: json, pycrate, pyside6, scapy, ...

**Linux Development/Runtime Installation**:
1. Debian based Linux only (Kali, Ubuntu, ...)
2. Includes QT6
3. ./packages/packages.sh

**Decoder**
1. Linux shell scripts provided
2. Environment setup in shell script for your PYTHONPATH: 'export PYTHONPATH=:../classes:../classes/j2735'

**Viewer (JSON files made by decoder)**
1. Linux shell scripts provided
2. Environment setup in shell script for your PYTHONPATH: 'export PYTHONPATH=:../classes:../classes/j2735'
3. Open .json files, filter by type
4. Can be slow for large JSON files
5. Viewing RTCM messages requires RTILIB, download for Windows here https://rtklib.com/ and unpack under j2735_tools

**Windows Development Installation**
1. Install Python3.12 from here https://www.python.org/downloads/
2. .\packages\packages.cmd
3. Windows, you'll need to download the free version from https://www.qt.io/product/qt6 and install that.

**Windows Building**  (uses PyInstaller for Windows .exe build)
1. WIndows .cmd files provided for testing
2. Invokes PyInstaller to build .exe (all prepacked and wrapped up) in j2735_decoder and j2735_viewer
3. .\win-build.cmd

**Windows Binaries** (Built with PyInstaller)
* https://v2x.probestar.com/j2735_tools/ (User=j2735, password=pcap_decoder)

**Wireshark**
Check out the Wireshark-J2735: https://github.com/nprobert/Wireshark-J2735

**TODO**
* Need to work on venv
* Docker version???
* Need to handle MAP absolute node points (not recommended), convert to relative offsets.

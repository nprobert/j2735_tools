**Python J2735 Decoder**

**Linux Running**
export PYTHONPATH=$PYTHONPATH:../classes:../classes/j2735

```text
Python3 J2735-2023-09-22 PCAP Decoder V1.2.9
j2735_decoder.py bcdhmo:su:v:BO: <input PCAP files>
        -b        Split BSMs to file by ID
        -c        Converting BSM enabled
        -d        Debugging enabled to debug.txt
        -h        Help
        -m        Binary MAP output in J2735 UPER format
        -o <offs> UDP offset to data in bytes
        -s        Split MAPs/SPATs to file by ID in JSON
        -u <port> UDP port
        -v vid    BSMs extracted by vehicle id
        -B        Use PCAP file base name as base path to output directory
        -O <path> Path to output base directory
         Creates JSON and KML (MAP) files with metadata.txt to <path>/<base>
```

**Windows Running**
1. Change directoy to j2735_decoder directory
2. Run j2735_decoder.cmd with arguments

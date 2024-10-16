#!/bin/sh

cat > data.rtcm3

# RTKlib
if [ -x /usr/bin/convbin ]; then
  echo "RTKlib convbin"
  echo "=============="
  mkdir -p logs
  /usr/bin/convbin -d logs data.rtcm3 2> rtcm3.err
  if [ -f logs/data.obs ]; then
    cat logs/data.obs
  fi
  echo "=============="
  rm rtcm3.err
fi

# GPSd
if [ -x /usr/bin/gpsdecode ]; then
  echo "gpsdecode"
  echo "========="
  /usr/bin/gpsdecode < data.rtcm3
  echo "========="
fi

rm data.rtcm3

#!/bin/sh

cat > data.rtcm2

# RTKlib
if [ -x /usr/bin/convbin ]; then
  echo "RTKlib convbin"
  echo "--------------"
  mkdir -p logs
  /usr/bin/convbin -r rtcm2 -d logs data.rtcm2 2> rtcm2.err
  if [ -f logs/data.obs ]; then
    cat logs/data.obs
  fi
  echo "=============="
  rm rtcm2.err
fi

# GPSd
if [ -x /usr/bin/gpsdecode ]; then
  echo "gpsdecode"
  echo "---------"
  /usr/bin/gpsdecode < data.rtcm2
  echo "========="
fi

rm data.rtcm2

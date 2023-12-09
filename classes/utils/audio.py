#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 10:26:56 2021

@author: neal
"""

from os import system
from sys import platform
import simpleaudio as sa

def play_sound(file):
  wave_obj = sa.WaveObject.from_wave_file(file)
  play_obj = wave_obj.play()

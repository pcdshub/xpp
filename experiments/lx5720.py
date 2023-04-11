from subprocess import check_output

import json
import sys
import time
import os
import socket
import logging

import numpy as np
from hutch_python.utils import safe_load
from ophyd import EpicsSignalRO
from ophyd import EpicsSignal
from bluesky import RunEngine
from bluesky.plans import scan
from bluesky.plans import list_scan
from ophyd import Component as Cpt
from ophyd import Device
from pcdsdevices.interface import BaseInterface
from pcdsdevices.areadetector import plugins
from xpp.db import daq
from xpp.db import camviewer
from xpp.db import RE
from xpp.db import at2l0
from xpp.db import seq
from xpp.devices import LaserShutter
from pcdsdevices.device_types import Newport, IMS, DelayNewport
from pcdsdevices.device_types import Trigger


cp = LaserShutter('XPP:USR:ao1:15', name='cp')
lp = LaserShutter('XPP:USR:ao1:14', name='lp')
ep = LaserShutter('XPP:USR:ao1:13', name='ep') 

class MpodChannel(Device):
    voltage = Cpt(EpicsSignal, ':GetVoltageMeasurement', write_pv=':SetVoltage', kind='normal')
    current = Cpt(EpicsSignalRO, ':GetCurrentMeasurement', kind='normal')
    state = Cpt(EpicsSignal, ':GetSwitch', write_pv=':SetSwitch', kind='normal')
    # 0 means no EPICS high limit.
    voltage_highlimit = Cpt(EpicsSignal, ':SetVoltage.DRVH', kind='normal')

class User():
    def __init__(self):
        with safe_load('quater waveplate'):
            self.qwp = DelayNewport('XPP:USR:MMN:25', name='qwp')
    
    def lp_close(self):
        lp('IN')
    def lp_open(self):
        lp('OUT')
    def cp_close(self):
        cp('IN')
    def cp_open(self):
        cp('OUT')
    def ep_open(self):
        ep('OUT')
    def ep_close(self):
        ep('IN')
 

    def THz_800nm_shutter(self, exptime, offsettime,bothofftime):
        i = 0
        self.ep_close()
        self.lp_close()
        while 1:
            # 800 open for offset time
            self.lp_close()
            self.ep_open() # keep lp_close
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([94, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = exptime
            time.sleep(settime)
            seq.stop()
            
            # 800 nm open and both exposure
            self.lp_open() # lp and ep open
            settime = abs(exptime - offsettime)
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([97, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            time.sleep(settime)
            seq.stop()
            
     
            # ep close and only THz
            self.ep_close() # ep close and lp open
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([95, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = exptime
            time.sleep(settime)
            seq.stop()

                   # THz close and 800 nm only for offset time
            self.lp_close() # both lp and ep close and lp open
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([92, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = bothofftime
            time.sleep(settime)
            seq.stop()

        return
    
    def THz_800nm_seq_shutter(self, thzexptime, TiSexptime,bothon,bothofftime):
        i = 0
        self.ep_close()
        self.lp_close()
        while 1:
            # 800 open for offset time
            self.lp_close()
            self.ep_open() # keep lp_close
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([94, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = TiSexptime
            time.sleep(settime)
            seq.stop()
            
            # 800 nm open and both exposure
            self.lp_open() # lp and ep open
            settime = bothon
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([97, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            time.sleep(settime)
            seq.stop()
            
     
            # ep close and only THz
            self.ep_close() # ep close and lp open
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([95, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = thzexptime
            time.sleep(settime)
            seq.stop()

                   # THz close and 800 nm only for offset time
            self.lp_close() # both lp and ep close and lp open
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([92, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = bothofftime
            time.sleep(settime)
            seq.stop()

        return

    def single_800nm_shutter(self, exptime, offsettime,bothofftime):
        i = 0
        self.ep_close()
        self.lp_close()
        while 1:
            # 800 open for offset time
            #self.lp_close()
            self.ep_open() # keep lp_close
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([94, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = exptime
            time.sleep(settime)
            seq.stop()
            
            # THz open and both exposure
            #self.lp_open() # lp and ep open
            #settime = abs(exptime - offsettime)
            #time.sleep(0.03)
            #shot_seq = []
            #shot_seq.append([97, 1, 0, 0])
            #seq.sequence.put_seq(shot_seq)
            #seq.start()
            #time.sleep(settime)
            #seq.stop()
            
     
            # ep close and only THz
            #self.ep_close() # ep close and lp open
            #time.sleep(0.03)
            #shot_seq = []
            #shot_seq.append([95, 1, 0, 0])
            #seq.sequence.put_seq(shot_seq)
            #seq.start()
            #settime = exptime
            #time.sleep(settime)
            #seq.stop()

                   # THz close and 800 nm only for offset time
            self.ep_close() # both lp and ep close and lp open
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([92, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = bothofftime
            time.sleep(settime)
            seq.stop()

        return

    def single_THz_shutter(self, exptime, offsettime,bothofftime):
        i = 0
        self.ep_close()
        self.lp_close()
        while 1:
            # 800 open for offset time
            #self.lp_close()
            self.lp_open() # keep lp_close
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([95, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = exptime
            time.sleep(settime)
            seq.stop()
            
            # THz open and both exposure
            #self.lp_open() # lp and ep open
            #settime = abs(exptime - offsettime)
            #time.sleep(0.03)
            #shot_seq = []
            #shot_seq.append([97, 1, 0, 0])
            #seq.sequence.put_seq(shot_seq)
            #seq.start()
            #time.sleep(settime)
            #seq.stop()
            
     
            # ep close and only THz
            #self.ep_close() # ep close and lp open
            #time.sleep(0.03)
            #shot_seq = []
            #shot_seq.append([95, 1, 0, 0])
            #seq.sequence.put_seq(shot_seq)
            #seq.start()
            #settime = exptime
            #time.sleep(settime)
            #seq.stop()

                   # THz close and 800 nm only for offset time
            self.lp_close() # both lp and ep close and lp open
            time.sleep(0.03)
            shot_seq = []
            shot_seq.append([92, 1, 0, 0])
            seq.sequence.put_seq(shot_seq)
            seq.start()
            settime = bothofftime
            time.sleep(settime)
            seq.stop()

        return
    ###############################################################################################
    #                   Functions from default files
    ###############################################################################################
    def takeRun(self, nEvents, record=None):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    # dscan & ascan kludge for x421 evr delay scan, as the evr object does not have the wm and mv attributes
    def pvascan(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.get()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.put(currPos)

    def pvdscan(self, motor, start, end, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.get()
        RE(scan([daq], motor, currPos + start, currPos + end, nsteps))
        motor.put(currPos)

    def ascan(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.mv(currPos)

    def listscan(self, motor, posList, nEvents, record=None):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(list_scan([daq], motor, posList))
        motor.mv(currPos)

    def dscan(self, motor, start, end, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.wm()
        RE(scan([daq], motor, currPos + start, currPos + end, nsteps))
        motor.mv(currPos)

    def a2scan(self, m1, a1, b1, m2, a2, b2, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[m1, m2])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, nsteps))

    def a3scan(self, m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[m1, m2, m3])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps))


    def set_current_position(self, motor, value):
        motor.set_use_switch.put(1)
        motor.set_use_switch.wait_for_connection()
        motor.user_setpoint.put(value, force=True)
        motor.user_setpoint.wait_for_connection()
        motor.set_use_switch.put(0)



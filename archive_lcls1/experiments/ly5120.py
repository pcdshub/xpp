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
from pcdsdevices.device_types import Newport, IMS, DelayNewport
from pcdsdevices.device_types import Trigger
from pcdsdevices.epics_motor import SmarAct


class MpodChannel(Device):
    voltage = Cpt(EpicsSignal, ':GetVoltageMeasurement', write_pv=':SetVoltage', kind='normal')
    current = Cpt(EpicsSignalRO, ':GetCurrentMeasurement', kind='normal')
    state = Cpt(EpicsSignal, ':GetSwitch', write_pv=':SetSwitch', kind='normal')
    # 0 means no EPICS high limit.
    voltage_highlimit = Cpt(EpicsSignal, ':SetVoltage.DRVH', kind='normal')


class LIB_SmarAct(BaseInterface, Device):
    tab_component_names = True
    mirr_x = Cpt(SmarAct, ':01:m1', kind='normal')
    mirr_y = Cpt(SmarAct, ':01:m2', kind='normal')
    mirr_dy = Cpt(SmarAct, ':01:m3', kind='normal')
    mirr_dx = Cpt(SmarAct, ':01:m4', kind='normal')
    mono_th = Cpt(SmarAct, ':01:m5', kind='normal')
    mono_x = Cpt(SmarAct, ':01:m6', kind='normal')


class User():
    def __init__(self):
        with safe_load('quater waveplate'):
            self.qwp = Newport('XPP:USR:MMN:25', name='qwp')
            self.hwp = Newport('XPP:USR:MMN:30', name='hwp')
            self.col_y = Newport('XPP:USR:MMN:28', name='col_y')
            self.col_x = Newport('XPP:USR:MMN:29', name='col_x')

        with safe_load('LIB SmarAct'):
            self.lib = LIB_SmarAct('XPP:MCS2', name='lib_smaract')
   

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



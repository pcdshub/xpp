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
from time import sleep


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

class Dg_channel(BaseInterface, Device):
    tab_component_names = True
    
    delay = Cpt(EpicsSignal, 'DelayAO', kind='hinted')
    delay_rbk = Cpt(EpicsSignalRO, 'DelaySI', kind='normal')
    reference = Cpt(EpicsSignal, 'ReferenceMO', kind='normal')
    
    tab_whitelist = ['set_reference', 'get_str']

    def get(self):
        return float(self.delay_rbk.get().split("+")[1])

    def get_str(self):
        return self.delay_rbk.get()

    def set(self, new_delay):
        return self.delay.set(new_delay)

    def set_reference(self, new_ref):
        if new_ref.upper() not in ['A','B','C','D','E','F','G','H','T0']:
            raise ValueError('New reference must be one of A, B, C, D, E, F, G, H, T0')
        else:
            return self.reference.set(new_ref)
    

class Dg(BaseInterface, Device):
    tab_component_names = True
    chA = Cpt(Dg_channel, ":a", name="chA")
    chB = Cpt(Dg_channel, ":b", name="chB")
    chC = Cpt(Dg_channel, ":c", name="chC")
    chD = Cpt(Dg_channel, ":d", name="chD")
    chE = Cpt(Dg_channel, ":e", name="chE")
    chF = Cpt(Dg_channel, ":f", name="chF")
    chG = Cpt(Dg_channel, ":g", name="chG")
    chH = Cpt(Dg_channel, ":h", name="chH")
    

class User():
    def __init__(self):
        #with safe_load('LIB SmarAct'):
        #    self.lib = LIB_SmarAct('XPP:MCS2', name='lib_smaract')
        self.t0 = 4.945e-6 # time zero for the delay generator
        with safe_load('Delay Generator'):
            self.dg = Dg('XPP:DDG:02', name='usr_dg')
        return

    
    def cavityFoldA(self, delta):
        self.th1.umv(45+delta)
        self.th2.umv(45+delta*3)
        self.th3.umv(45+delta*5)
        self.th4.umv(45+delta*7)

    def cavityFoldR(self, delta):
        self.th1.umvr(delta)
        self.th2.umvr(delta*3)
        self.th3.umvr(delta*5)
        self.th4.umvr(delta*7)


    
    def set45(self):
        self.th1.set_current_position(45)
        self.th2.set_current_position(45)
        self.th3.set_current_position(45)
        self.th4.set_current_position(45)

    def iStarDelay(self, delay):
        self.dg.chA.delay.set(self.t0+delay)

    def iStarWidth(self, width):
        self.dg.chB.delay.set(width)

    def iStarDelayScan(self, start, end, stepSize, waitTime):
        currentDelay = start
        while(currentDelay <= end):
            self.dg.chA.delay.set(self.t0+currentDelay)
            print('delay time: %.2f ns' % (currentDelay*1e9))
            sleep(waitTime)
            currentDelay = currentDelay+stepSize
        self.dg.chA.delay.set(self.t0+47.25e-9)

    
    def goRT(self, tripNumber):
        self.dg.chA.delay.set(self.t0+tripNumber*47.25e-9)

    def iStarDelayScan2(self, startNum, endNum, waitTimeMin, waitTimeMax):
        counter=startNum
        if startNum > endNum:
            step = -1
        else:
            step = 1
        while(counter != (endNum + step)):
            currentDelay = self.t0+counter*47.25e-9
            self.dg.chA.delay.set(currentDelay-10e-9)
            print('Round Trip: %d' % counter)
            waitTimeH = min([waitTimeMax, max([waitTimeMin, 1.5**counter])])
            sleep(waitTimeH)
            self.dg.chA.delay.set(currentDelay)
            sleep(waitTimeH)
            counter = counter + step
        self.dg.chA.delay.set(self.t0+47.25e-9)
        

###############################################################################################
    #                   Functions from default files ###############################################################################################






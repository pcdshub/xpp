from subprocess import check_output

import json
import sys
import time
import os

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
from pcdsdevices.device_types import Newport, IMS, Trigger
#from pcdsdevices.device_types import Trigger
#move this to beamline with the most typical detectors.
from pcdsdaq.ami import AmiDet


class User():
    def __init__(self):
        try:
            self.t0 = 880000
        except:
            self.t0 = None
        with safe_load('lom_th2'):
            self.lom_th2 = IMS('XPP:MON:MMS:13', name='lom_th2')
        with safe_load('Be_motors'):
            self.crl_x = IMS('XPP:SB2:MMS:13', name='crl_x')
            self.crl_y = IMS('XPP:SB2:MMS:14', name='crl_y')
            self.crl_z = IMS('XPP:SB2:MMS:15', name='crl_z')
        with safe_load('user_newports'):
            self.pr_phi = Newport('XPP:USR:MMN:08', name='pr_phi')
            self.pr_th = Newport('XPP:USR:MMN:05', name='pr_th')
            self.pr_x = Newport('XPP:USR:MMN:06', name='pr_x')
            self.pr_z = Newport('XPP:USR:MMN:07', name='pr_z')
        with safe_load('user_dumb'):
            self.pl_x = IMS('XPP:USR:MMS:23', name='pl_x')
            self.pl_y = IMS('XPP:USR:MMS:24', name='pl_y')
            self.pl_th = IMS('XPP:USR:MMS:28', name='pl_th')
            self.vpl_y = IMS('XPP:USR:MMS:29', name='vpl_y')
            self.vpl_th = IMS('XPP:USR:MMS:30', name='vpl_th')	
        with safe_load('trigger'):
            self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
            self.delay = self.evr_R30E28.ns_delay
        

    def takeRun(self, nEvents, record=True):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    
    def ascan(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.mv(currPos)

    def ascanXCS(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.wm()
        if record is None:
            daq.configure(nEvents, controls=[motor])
        else:
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
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.mv(currPos)

    def a2scan(self, m1, a1, b1, m2, a2, b2, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[m1, m2])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, nsteps))

    def a3scan(self, m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[m1, m2, m3])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps))




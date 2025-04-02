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
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger
#move this to beamline with the most typical detectors.
from pcdsdaq.ami import AmiDet

import sys
sys.path.append('/reg/neh/home/seaberg/Python/lcls_beamline_toolbox/')
from lcls_beamline_toolbox.xrayinteraction import interaction
from lcls_beamline_toolbox.xraybeamline2d import optics

       

class User():
    def __init__(self):
        self.t0 = 890000
        with safe_load('beamline_motors'):
            self.lom_th2 = IMS('XPP:MON:MMS:13', name='lom_th2')
            self.crl_x = IMS('XPP:SB2:MMS:13', name='crl_x')
            self.crl_y = IMS('XPP:SB2:MMS:14', name='crl_y')
            self.crl_z = IMS('XPP:SB2:MMS:15', name='crl_z')
        
        with safe_load('user_newports'):
            self.sam_translation = Newport('XPP:USR:MMN:01', name='sam_translation')
            self.sam_rotation = Newport('XPP:USR:MMN:02', name='sam_rotation')            
            #self.xx = Newport('XPP:USR:MMN:03', name='x')
            #self.xx = Newport('XPP:USR:MMN:04', name='x')
            #self.xx = Newport('XPP:USR:MMN:05', name='x')
            self.tg_theta_x = Newport('XPP:USR:MMN:06', name='tg_theta_x')
            #self.xx = Newport('XPP:USR:MMN:07', name='x')
            #self.xx = Newport('XPP:USR:MMN:08', name='x')
            
        with safe_load('alcove_newports'):
            self.det_x = Newport('XPP:USR:PRT:MMN:03', name='det_x')
            self.op_rot = Newport('XPP:USR:PRT:MMN:04', name='op_rot')
            self.grating_y = Newport('XPP:USR:PRT:MMN:05', name='grating_y')
            self.grating_x = Newport('XPP:USR:PRT:MMN:06', name='grating_x')
            self.op_x = Newport('XPP:USR:PRT:MMN:07', name='op_x')
            self.grating_z = Newport('XPP:USR:PRT:MMN:08', name='grating_z')

        with safe_load('user_smart'):
            #self.xx = IMS('XPP:USR:MMS:01', name='xx')
            #self.xx = IMS('XPP:USR:MMS:02', name='xx')
            #self.xx = IMS('XPP:USR:MMS:03', name='xx')
            #self.xx = IMS('XPP:USR:MMS:04', name='xx')
            #self.xx = IMS('XPP:USR:MMS:05', name='xx')
            #self.xx = IMS('XPP:USR:MMS:06', name='xx')
            #self.xx = IMS('XPP:USR:MMS:07', name='xx')
            self.zyla1y = IMS('XPP:USR:MMS:08', name='zyla1y')
            self.zyla1x = IMS('XPP:USR:MMS:09', name='zyla1x')
            #self.xx = IMS('XPP:USR:MMS:10', name='xx')
            #self.xx = IMS('XPP:USR:MMS:11', name='xx')
            #self.xx = IMS('XPP:USR:MMS:12', name='xx')
            #self.xx = IMS('XPP:USR:MMS:13', name='xx')
            #self.xx = IMS('XPP:USR:MMS:14', name='xx')
            #self.xx = IMS('XPP:USR:MMS:15', name='xx')
            #self.xx = IMS('XPP:USR:MMS:16', name='xx')
        with safe_load('user_dumb'):
            self.sam_y = IMS('XPP:USR:MMS:31', name='sam_y')
            self.tg_theta_y = IMS('XPP:USR:MMS:25', name='tg_theta_y')
            self.tg_x = IMS('XPP:USR:MMS:28', name='tg_x')
            self.tg_theta_z = IMS('XPP:USR:MMS:29', name='tg_theta_z')
            self.tg_y = IMS('XPP:USR:MMS:30', name='tg_y')
        with safe_load('alcove_dumb'):
            self.sam_z = IMS('XPP:USR:PRT:MMS:17', name='sam_z')
            self.sam_x = IMS('XPP:USR:PRT:MMS:20', name='sam_x')
            self.bb_x = IMS('XPP:USR:PRT:MMS:18', name='bb_x')
            self.bb_y = IMS('XPP:USR:PRT:MMS:19', name='bb_y')
            self.lens_x = IMS('XPP:USR:MMS:21', name='lens_x')
            self.lens_y = IMS('XPP:USR:MMS:22', name='lens_y')
            self.lens_theta_x = IMS('XPP:USR:MMS:23', name='lens_theta_x')
            self.lens_theta_y = IMS('XPP:USR:MMS:24', name='lens_theta_y')
            self.ds_ygap = IMS('XPP:USR:PRT:MMS:21', name='ds_ygap')
            self.ds_yoff = IMS('XPP:USR:PRT:MMS:22', name='ds_yoff')
            self.ds_xgap = IMS('XPP:USR:PRT:MMS:23', name='ds_xgap')
            self.ds_xoff = IMS('XPP:USR:PRT:MMS:24', name='ds_xoff')
            #self.xx = IMS('XPP:USR:PRT:MMS:25', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:26', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:27', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:28', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:29', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:30', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:31', name='xx')
            #self.xx = IMS('XPP:USR:PRT:MMS:32', name='xx')
           
        # keeping a record for what Yanwen used for CC test   
        isCC = False
        if isCC:    
            with safe_load('CC1_x'):
                self.CC1_x = IMS('XPP:USR:MMS:07', name='CC1_x')
            with safe_load('CC1_th'):
                self.CC1_th = IMS('XPP:USR:MMS:29', name='CC1_th')
            with safe_load('CC2_x'):
                self.CC2_x = IMS('XPP:USR:MMS:09', name='CC2_x')
            with safe_load('CC2_th'):
                self.CC2_th = IMS('XPP:USR:MMS:20', name='CC2_th')


    def takeRun(self, nEvents, record=True):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    def get_ascan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        return scan([daq], motor, start, end, nsteps)

    def get_dscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record)
        currPos = motor.wm()
        return scan([daq], motor, currPos+start, currPos+end, nsteps)

    def ascan(self, motor, start, end, nsteps, nEvents, record=True):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.mv(currPos)

    def listscan(self, motor, posList, nEvents, record=True):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(list_scan([daq], motor, posList))
        motor.mv(currPos)

    def dscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.wm()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.mv(currPos)

    # dscan & ascan kludge for x421 evr delay scan, as the evr object does not have the wm and mv attributes
    def evrascan(self, motor, start, end, nsteps, nEvents, record=True):
        currPos = motor.get()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.set(currPos)

    def evrdscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.get()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.set(currPos)

    def a2scan(self, m1, a1, b1, m2, a2, b2, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[m1, m2])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, nsteps))

    def a3scan(self, m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[m1, m2, m3])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps))



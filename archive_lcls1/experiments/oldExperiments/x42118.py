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

class MpodChannel(Device):
    voltage = Cpt(EpicsSignal, ':GetVoltageMeasurement', write_pv = ':SetVoltage', kind='normal')
    current = Cpt(EpicsSignalRO, ':GetCurrentMeasurement', kind='normal')
    state = Cpt(EpicsSignal, ':GetSwitch', write_pv = ':SetSwitch', kind='normal')
    #0 means no EPICS high limit.
    voltage_highlimit =  Cpt(EpicsSignal, ':SetVoltage.DRVH', kind='normal')
    





class User():
    def __init__(self):
        self.t0=894756
        
        #with safe_load('crl2_xytheta'):
        #    self.crl2_x = Newport('XPP:USR:MMN:01', name='crl2_x')
        #    self.crl2_y = Newport('XPP:USR:MMN:02', name='crl2_y')
        #    self.crl2_th_x = Newport('XPP:USR:MMN:05', name='crl2_th_x')
        #    self.crl2_th_y = Newport('XPP:USR:MMN:04', name='crl2_th_y')
        #with safe_load('crl3'):
        #    self.crl3_x = Newport('XPP:USR:PRT:MMN:01', name='crl3_x')
        #    self.crl3_y = Newport('XPP:USR:PRT:MMN:02', name='crl3_y')
        #with safe_load('op_x'):
        #    self.op_x = Newport('XPP:USR:PRT:MMN:07', name='op_x')
        #with safe_load('op_rot'):
        #    self.op_rot = Newport('XPP:USR:PRT:MMN:04', name='op_rot')
        #with safe_load('grating_xyz'):
        #    self.grating_x = Newport('XPP:USR:PRT:MMN:06', name='grating_x')
        #    self.grating_y = Newport('XPP:USR:PRT:MMN:05', name='grating_y')
        #    self.grating_z = Newport('XPP:USR:PRT:MMN:08', name='grating_z')
        #with safe_load('lom_th2'):
        #   self.lom_th2 = IMS('XPP:MON:MMS:13', name='lom_th2')
        #with safe_load('crl'):
        #    self.Be_xpos = IMS('XPP:SB2:MMS:13', name='crl_x')
        #    self.Be_ypos = IMS('XPP:SB2:MMS:14', name='crl_y')
        #    self.Be_zpos = IMS('XPP:SB2:MMS:15', name='crl_z')
        #with safe_load('c1'):
            #self.c1_z = IMS('XPP:USR:PRT:MMS:19', name='c1_z')
            #self.c1_y = IMS('XPP:USR:PRT:MMS:20', name='c1_y')
            #self.c1_th = IMS('XPP:USR:PRT:MMS:21', name='c1_th')
        #    self.c1_chi = IMS('XPP:USR:PRT:MMS:22', name='c1_chi')
        #    self.c1_p = IMS('XPP:USR:PRT:MMS:23', name='c1_p')
        #with safe_load('c2'):
        #    self.c2_z = IMS('XPP:USR:PRT:MMS:24', name='c2_z')
        #    self.c2_y = IMS('XPP:USR:PRT:MMS:25', name='c2_y')
            #self.c2_th = IMS('XPP:USR:PRT:MMS:26', name='c2_th')
            #self.c2_chi = IMS('XPP:USR:PRT:MMS:27', name='c2_chi')
	    #self.xtal_th = IMS('XPP:USR:PRT:MMS:27', name='xtal_th')
            #self.c2_p = IMS('XPP:USR:PRT:MMS:28', name='c2_p')
        #with safe_load('xtal'):
        #    self.xtal_p = IMS('XPP:USR:MMS:21', name='xtal_p')
        #    self.det_x = IMS('XPP:USR:PRT:MMS:19', name='det_x')
        #   self.det_y = IMS('XPP:USR:PRT:MMS:20', name='det_y')
        #    self.xtal_th = IMS('XPP:USR:PRT:MMS:21', name='xtal_th')
        #   self.xtal_y = IMS('XPP:USR:PRT:MMS:29', name='xtal_y')
        #    self.xtal_x = IMS('XPP:USR:PRT:MMS:14', name='xtal_x')
        #with safe_load('c3'):
        #    #self.c3_z = IMS('XPP:USR:MMS:21', name='c3_z')
        #    self.c3_y = IMS('XPP:USR:MMS:22', name='c3_y')
        #    self.c3_th = IMS('XPP:USR:MMS:23', name='c3_th')
        #    self.c3_chi = IMS('XPP:USR:MMS:24', name='c3_chi')
        #    self.c3_p = IMS('XPP:USR:MMS:25', name='c3_p')
        #with safe_load('c4'):
        #    self.c4_z = IMS('XPP:USR:MMS:26', name='c4_z')
        #    self.c4_y = IMS('XPP:USR:MMS:27', name='c4_y')
        #    self.c4_th = IMS('XPP:USR:MMS:32', name='c4_th')
        #with safe_load('grating'):
        #    self.tg_x = IMS('XPP:USR:MMS:28', name='tg_x')
        #    self.tg_y = IMS('XPP:USR:MMS:29', name='tg_y')
        #   self.tg_th_x = Newport('XPP:USR:MMN:06', name='tg_th_x')
        #    self.tg_th_z = IMS('XPP:USR:MMS:30', name='tg_th_z')
        #    self.tg_th_y = IMS('XPP:USR:MMS:31', name='tg_th_y')
        #with safe_load('CB'):
        #    self.cb2_x =  Newport('XPP:USR:MMN:03', name='cb2_x')
        #    self.cb1_x =  Newport('XPP:USR:PRT:MMN:03', name='cb1_x')
        #with safe_load('fast_diode'):
        #    self.fpd_y =  IMS('XPP:USR:PRT:MMS:29', name='fpd_y')
        #   self.fpd_x =  IMS('XPP:USR:PRT:MMS:17', name='fpd_x')
        #with safe_load('diagnostic'):
        #    self.dia1_x = Newport('XPP:USR:PRT:MMN:05', name='dia1_x')
        #    self.dia2_x = IMS('XPP:USR:PRT:MMS:31', name='dia2_x')
        #    self.dia_img_u_x = Newport('XPP:USR:MMN:08', name='dia_img_u_x')
        #    self.dia_img_d_x = Newport('XPP:USR:PRT:MMS:32', name='dia_img_d_x')
        #    self.dia2b_x = IMS('XPP:USR:MMS:17', name='dia2b_x')
        #    self.dia3_x = IMS('XPP:USR:MMS:18', name='dia3_x')
        #with safe_load('zyla0'):
        #    self.zyla0_y = IMS('XPP:USR:PRT:MMS:18', name='zyla0_y')
        #    self.zyla0_x = Newport('XPP:USR:PRT:MMN:07', name='zyla0_x')
        #    #self.zyla0_f = IMS('XPP:USR:MMN:17', name='zyla0_f')
        #    #self.dia4_x = Newport('XPP:USR:MMN:03', name='dia4_x')
        #    self.cb2_x = IMS('XPP:USR:MMS:29', name='tg_y')
       

        #with safe_load('bodXY'):
        #    self.bodX = IMS('XPP:USR:MMS:28', name='bodX')
        #    self.bodY = IMS('XPP:USR:MMS:01', name='bodY')
        with safe_load('Triggers'):
            self.gateEVR = Trigger('XPP:USR:EVR:TRIG2', name='evr_USR2')
            self.gateEVR_ticks = EpicsSignal('XPP:USR:EVR:CTRL.DG2D', name='evr_USR2_ticks')
            self.GD = self.gateEVR.ns_delay
        with safe_load('MPOD'):
            self.diode_bias = MpodChannel('XPP:R39:MPD:CH:100', name='diode_bias')

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
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
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
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.mv(currPos)

    def a2scan(self, m1, a1, b1, m2, a2, b2, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[m1, m2])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, nsteps))

    def a3scan(self, m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[m1, m2, m3])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps))

    def ascan_wimagerh5(self, imagerh5, motor, start, end, nsteps, nEvents, record=None):
        plan_duration = nsteps*nEvents/120.+0.3*(nsteps-1)+4
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        #we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)
        imagerh5.write_wait()

    def ascan_wimagerh5_slow(self, imagerh5, motor, start, end, nsteps, nEvents, record=None):
        plan_duration = (nsteps*nEvents/120.+0.3*(nsteps-1)+4)*10
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        #we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)
        
        imagerh5.write_stop()



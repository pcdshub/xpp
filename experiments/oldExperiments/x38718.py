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
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger


class MpodChannel(Device):
    voltage = Cpt(EpicsSignal, ':GetVoltageMeasurement', write_pv=':SetVoltage', kind='normal')
    current = Cpt(EpicsSignalRO, ':GetCurrentMeasurement', kind='normal')
    state = Cpt(EpicsSignal, ':GetSwitch', write_pv=':SetSwitch', kind='normal')
    # 0 means no EPICS high limit.
    voltage_highlimit = Cpt(EpicsSignal, ':SetVoltage.DRVH', kind='normal')


class User():
    def __init__(self):
        self.t0 = 894756
        try:
            self.im1l0_h5 = ImagerHdf5(camviewer.im1l0)
            self.im2l0_h5 = ImagerHdf5(camviewer.im2l0)
            self.im3l0_h5 = ImagerHdf5(camviewer.im3l0)
            self.im4l0_h5 = ImagerHdf5(camviewer.im4l0)
            self.gige13_h5 = ImagerHdf5(camviewer.xpp_gige_13)
            self.im1l0_stats = ImagerStats(camviewer.im1l0)
            self.im2l0_stats = ImagerStats(camviewer.im2l0)
            self.im3l0_stats = ImagerStats(camviewer.im3l0)
            self.im4l0_stats = ImagerStats(camviewer.im4l0)
            self.im1l0_stats3 = ImagerStats3(camviewer.im1l0)
            self.im2l0_stats3 = ImagerStats3(camviewer.im2l0)
            self.im3l0_stats3 = ImagerStats3(camviewer.im3l0)
            self.im4l0_stats3 = ImagerStats3(camviewer.im4l0)
        except:
            self.im1l0_h5 = None
            self.im2l0_h5 = None
            self.im3l0_h5 = None
            self.im4l0_h5 = None
            self.im1l0_stats = None
            self.im2l0_stats = None
            self.im3l0_stats = None
            self.im4l0_stats = None
            self.im1l0_stats3 = None
            self.im3l0_stats3 = None
            self.im4l0_stats3 = None
        with safe_load('crl2_xytheta'):
            self.crl2_x = IMS('XPP:USR:PRT:MMS:20', name='crl2_x')
            self.crl2_y = IMS('XPP:USR:PRT:MMS:22', name='crl2_y')
            self.crl2_z = IMS('XPP:USR:PRT:MMS:23', name='crl2_z')
            self.crl2_th_x = Newport('XPP:USR:MMN:05', name='crl2_th_x')
            self.crl2_th_y = Newport('XPP:USR:MMN:04', name='crl2_th_y')

        #########################################################################
        #            Add the axes
        #########################################################################
        with safe_load("grating_1"):
            pass

        with safe_load("CC1"):
            self.t1_x = IMS('XPP:USR:MMS:18', name='t1_x')
            self.t1_y = IMS('XPP:USR:MMS:22', name='t1_y')
            self.t1_th = IMS('XPP:USR:MMS:29', name='t1_th')

        with safe_load("CC2"):
            self.t2_th = IMS('XPP:USR:MMS:23', name='t2_th')

        with safe_load("CC3"):
            self.t3_th = IMS('XPP:USR:MMS:32', name='t3_th')

        with safe_load("CC4"):
            self.t4_x = IMS('XPP:USR:MMS:25', name='t4_x')
            self.t4_th = IMS('XPP:USR:MMS:30', name='t4_th')

        with safe_load("CC5"):
            self.t5_x = IMS('XPP:USR:MMS:21', name='t5_x')
            self.t5_th = IMS('XPP:USR:PRT:MMS:25', name='t5_th')

        with safe_load("CC6"):
            self.t6_x = IMS('XPP:USR:PRT:MMS:24', name='t6_x')
            self.t6_y = IMS('XPP:USR:PRT:MMS:29', name='t6_y')
            self.t6_th = IMS('XPP:USR:PRT:MMS:21', name='t6_th')

        with safe_load("Diagnosis"):
            self.d1_x = IMS('XPP:USR:MMS:17', name='d1_x')
            self.sydor_x = IMS('XPP:USR:MMS:19', name='sydor_x')
            self.sydor_y = IMS('XPP:USR:MMS:20', name='sydor_y')
            self.d2_x = IMS('XPP:USR:MMS:24', name='d2_x')
            self.d3_x = IMS('XPP:USR:MMS:31', name='d3_x')
            self.d4_x = IMS('XPP:USR:MMS:26', name='d4_x')
            self.d5_x = IMS('XPP:USR:PRT:MMS:32', name='d5_x')
            self.yag_x = IMS('XPP:USR:PRT:MMS:19', name='yag_x')

        # with safe_load('zyla0'):
        #    self.zyla0_y = IMS('XPP:USR:PRT:MMS:18', name='zyla0_y')
        #    self.zyla0_x = Newport('XPP:USR:PRT:MMN:07', name='zyla0_x')
        # with safe_load('Triggers'):
        #    self.evr_R30E26 = Trigger('XPP:R30:EVR:26:TRIGB', name='evr_R30E26')
        #    self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
        #    self.evr_R30E26_ticks = EpicsSignal('XPP:R30:EVR:26:CTRL.DGBD', name='evr_R30E26_ticks')
        #    self.evr_R30E28_ticks = EpicsSignal('XPP:R30:EVR:28:CTRL.DGBD', name='evr_R30E28_ticks')
        #    self.GD = self.evr_R30E28.ns_delay

        with safe_load('MPOD'):
            self.diode_bias = MpodChannel('XPP:R39:MPD:CH:100', name='diode_bias')

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
        try:
            motor.put(currPos)
        except:
            print('failed to move back to original value ',currPos)

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

    def ascan_wimagerh5(self, imagerh5, motor, start, end, nsteps, nEvents, record=None):
        plan_duration = nsteps * nEvents / 120. + 0.3 * (nsteps - 1) + 4
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        # we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)
        imagerh5.write_wait()

    def ascan_wimagerh5_slow(self, imagerh5, motor, start, end, nsteps, nEvents, record=None):
        plan_duration = (nsteps * nEvents / 120. + 0.3 * (nsteps - 1) + 4) * 10
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        # we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)

        imagerh5.write_stop()


# This is the premission test of Haoyuan

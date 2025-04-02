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
from xpp.db import lxt_fast
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger



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

        #########################################################################
        #            Add the axes
        #########################################################################
        
        with safe_load('Liquid Jet'):
            from pcdsdevices.jet import BeckhoffJet
            self.ljh = BeckhoffJet('XCS:LJH', name='ljh')
        
        with safe_load('LIB'):
            self.lib_diag = IMS('XPP:USR:MMS:32', name='lib_diag')

        with safe_load('sam'):
            self.sam_x = IMS('XPP:USR:MMS:01', name='sam_x')
            self.sam_y = IMS('XPP:USR:MMS:17', name='sam_y')




    ###############################################################################################
    #                   Functions from default files
    ###############################################################################################

    def takeRun(self, nEvents, record=None):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

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

    def set_current_position(self, motor, value):
        motor.set_use_switch.put(1)
        motor.set_use_switch.wait_for_connection()
        motor.user_setpoint.put(value, force=True)
        motor.user_setpoint.wait_for_connection()
        motor.set_use_switch.put(0)

    def empty_delay_scan(self, start, end, sweep_time, record=None,
                         use_l3t=False, duration=None):
        """Delay scan without the daq."""
        self.cleanup_RE()
        #daq.configure(events=None, duration=None, record=record,
        #              use_l3t=use_l3t, controls=[lxt_fast])
        try:
            RE(delay_scan([], lxt_fast, [start, end], sweep_time,
                          duration=duration))
        except Exception:
            #logger.debug('RE Exit', exc_info=True)

            print("sorry")
        finally:
            self.cleanup_RE()

    def cleanup_RE(self):
        if not RE.state.is_idle:
            print('Cleaning up RunEngine')
            print('Stopping previous run')
            try:
                RE.stop()
            except Exception:
                pass

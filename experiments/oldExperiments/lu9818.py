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
from subprocess import*





class User():
    def __init__(self):
        with safe_load('collimator'):
            self.col_h=Newport('XPP:USR:MMN:02', name='col_h')
            self.col_v=Newport('XPP:USR:MMN:01', name='col_v')
            self.col_r=Newport('XPP:USR:MMN:05', name='col_r')
    

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

    def tt_rough_FB(self, ttamp_th = 0.05, ipm2_th = 3000, tt_window = 0.1):
        fbvalue = 0 # for drift record
        while(1):
            tenshots_tt = np.zeros([1,])
            dlen = 0
            while(dlen < 61):
                ttcomm = Popen("caget XPP:TIMETOOL:TTALL",shell = True, stdout=PIPE)
                ttdata = (ttcomm.communicate()[0]).decode()
                current_tt = float((ttdata.split(" "))[3])
                ttamp = float((ttdata.split(" "))[4])
                ipm2val = float((ttdata.split(" "))[5])
                ttfwhm = float((ttdata.split(" "))[7])
                if(dlen%10 == 0):
                    print("tt_value",current_tt,"ttamp",ttamp,"ipm2",ipm2val)
                if (ttamp > ttamp_th)and(ipm2val > ipm2_th)and(ttfwhm < 130)and(ttfwhm >  70)and(current_tt != tenshots_tt[-1,]):# for filtering the last one is for when DAQ is stopping
                    tenshots_tt = np.insert(tenshots_tt,dlen,current_tt)
                    dlen = np.shape(tenshots_tt)[0]
                time.sleep(0.1)
            tenshots_tt = np.delete(tenshots_tt,0)
            ave_tt = np.mean(tenshots_tt)
            print("Moving average of timetool value:", ave_tt)
    
            if np.abs(ave_tt) > tt_window:
                ave_tt_second=-(ave_tt*1e-12)
                m.lxt.mvr(ave_tt_second)
                print("feedback %f ps"%ave_tt)
                fbvalue = ave_tt + fbvalue
                drift_log(str(fbvalue))
        return


def drift_log(idata):
    savefilename = "/cds/home/opr/xppopr/experiments/xpplu9818/drift_log_Dec11.txt"
    currenttime = time.ctime()
    out_f = open(savefilename,'a')
    out_f.write(str(idata)+ "," + currenttime.split(" ")[3] +"\n")
    out_f.close()


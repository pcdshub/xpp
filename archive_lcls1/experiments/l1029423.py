import numpy as np
import logging
import time

from ophyd import EpicsSignal, EpicsSignalRO

from pcdsdevices.sim import FastMotor, SlowMotor
from pcdsdevices.device_types import Trigger
from pcdsdevices.device_types import IMS, Newport
from pcdsdevices.targets import XYGridStage

from xpp.db import RE, bpp, bps, seq
from xpp.db import daq
from xpp.db import xpp_pulsepicker as pp
import time

azi = EpicsSignal('XPP:ROB:POS:AZI')
       
class User():
    def __init__(self):
        pass

    def fakea2scan(self,motorname,m1list,robolist,numevents):
        orgpos = motorname.wm()
        daq.connect()
        daq.begin(record = True)
        time.sleep(0.2)
        for i in range(np.shape(m1list)[0]):
            motorname.umv(m1list[i])
            robo.move_azi(robolist[i])
            #while(round(azi.get(),4) != round(robolist[i],4)):
            while(round(azi.get(),4) != round(robolist[i],4)):
                time.sleep(0.1)
            pp.open()
            time.sleep(numevents/120)            
            pp.close()
        daq.end_run()
        return

    def robo_tth_scan(self,robolist,numevents):
        daq.connect()
        daq.begin(record = True)
        time.sleep(0.2)
        for i in range(np.shape(robolist)[0]):
            robo.move_azi(robolist[i])
            #while(round(azi.get(),4) != round(robolist[i],4)):
            while(round(azi.get(),4) != round(robolist[i],4)):
                time.sleep(0.1)
            pp.open()
            time.sleep(numevents/120)            
            pp.close()
        daq.end_run()

    def th_scan(self,motorname,steplist,numevents):
        daq.connect()
        daq.begin(record = True)
        time.sleep(0.2)
        for i in range(np.shape(steplist)[0]):
            motorname.umv(steplist[i])
            pp.open()
            time.sleep(numevents/120)            
            pp.close()
        daq.end_run()
     
class robo():#get robot positions
    def get_positions():
        ele = EpicsSignal('XPP:ROB:POS:ELE')
        ele_pos = ele.get()
        azi = EpicsSignal('XPP:ROB:POS:AZI')
        azi_pos = azi.get()
        ra = EpicsSignal('XPP:ROB:POS:RAD')
        ra_pos = ra.get()

        print("{}".format("EL: " + str(ele_pos) + " AZ: "+ str(azi_pos) + " RA: " + str(ra_pos)))
        return ele_pos,azi_pos,ra_pos

    def move_azi(azi_angle):
        robo_azi = EpicsSignal('XPP:ROB:MOV:AZI')
        robo_azi.put(azi_angle)
        return
        fake_a2scan(motorname)


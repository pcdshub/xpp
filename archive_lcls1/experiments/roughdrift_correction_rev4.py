from subprocess import*
import numpy as np
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

 def tt_rough_FB(self, ttamp_th = 0.04, ipm2_th = 2000, tt_window = 0.1,kp = 1.2,ki = 0.0001,kd = 1):
        fbvalue = 0 # for drift record
        ave_tt = np.zeros([2,])
        while(1):
            tenshots_tt = np.zeros([1,])
            dlen = 0
            pt = 0
            while(dlen < 121):
                ttcomm = Popen("caget XPP:TIMETOOL:TTALL",shell = True, stdout=PIPE)
                ttdata = (ttcomm.communicate()[0]).decode()
                current_tt = float((ttdata.split(" "))[3])
                ttamp = float((ttdata.split(" "))[4])
                ipm2val = float((ttdata.split(" "))[5])
                ttfwhm = float((ttdata.split(" "))[7])
                if(dlen%60 == 0):
                    print("tt_value",current_tt,"ttamp",ttamp,"ipm2",ipm2val)
                if (ttamp > ttamp_th)and(ipm2val > ipm2_th)and(ttfwhm < 130)and(ttfwhm >  70)and(current_tt != tenshots_tt[-1,])and(m.txt.moving == False):# for filtering the last one is for when DAQ is stopping
                    tenshots_tt = np.insert(tenshots_tt,dlen,current_tt)
                    dlen = np.shape(tenshots_tt)[0]
                pt = pt + 1 
                time.sleep(0.01)
            tenshots_tt = np.delete(tenshots_tt,0)
            ave_tt[1,] = ave_tt[0,]
            ave_tt[0,] = np.mean(tenshots_tt)
            print("Moving average of timetool value:", ave_tt)
            fb_val = pid_control(kp,ki,kd,ave_tt,pt)
            #if (np.abs(ave_tt-0.3) > tt_window) and (m.txt.moving = False):
            if(round(m.lxt(),14)==round(m.txt(),14) and (m.txt.moving == False)):
               ave_tt_second=-((fb_val-0.3)*1e-12)
               m.lxt.mvr(ave_tt_second)
            #m.lxt.set_current_position(-(m.txt.wm()))
               print("feedback %f ps"%ave_tt[0,])
            fbvalue = ave_tt + fbvalue
            drift_log(str(fbvalue))
        return


def drift_log(idata):
    savefilename = "/cds/home/opr/xppopr/experiments/xpplu9818/drift_log_Mar16.txt"
    currenttime = time.ctime()
    out_f = open(savefilename,'a')
    out_f.write(str(idata)+ "," + currenttime.split(" ")[3] +"\n")
    out_f.close()

def pid_control(kp,ki,kd,ave_data,faketime):
    fd_value = kp*ave_data[0] + ki(np.sum(ave_data))+kd*((ave_data[1,]-ave_data[0,])/faketime)
    return fd_value
    
    




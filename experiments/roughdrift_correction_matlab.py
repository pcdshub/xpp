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

 def tt_rough_FB(self, ttamp_th = 0.05, ipm2_th = 3000, tt_window = 0.05):
        fbvalue = 0 # for drift record
        matPV = EpicsSignal('LAS:FS11:VIT:matlab:04')
        org_matPV = matPV.get()
        while(1):
            tenshots_tt = np.zeros([1,])
            dlen = 0
            while(dlen < 61):
                #ttcomm = Popen("caget XPP:TIMETOOL:TTALL",shell = True, stdout=PIPE)
                #ttdata = (ttcomm.communicate()[0]).decode()
                ttall = EpicsSignal('XPP:TIMETOOL:TTALL')
                ttdata = ttall.get()
                
                current_tt = ttdata[1,]
                ttamp = ttdata[2,]
                ipm2val = ttdata[3,]
                ttfwhm = ttdata[5,]
                #current_tt = float((ttdata.split(" "))[3])
                #ttamp = float((ttdata.split(" "))[4])
                #ipm2val = float((ttdata.split(" "))[5])
                #ttfwhm = float((ttdata.split(" "))[7])
                if(dlen%10 == 0):
                    print("tt_value",current_tt,"ttamp",ttamp,"ipm2",ipm2val)
                if (ttamp > ttamp_th)and(ipm2val > ipm2_th)and(ttfwhm < 130)and(ttfwhm >  70)and(current_tt != tenshots_tt[-1,]):# for filtering the last one is for when DAQ is stopping
                    tenshots_tt = np.insert(tenshots_tt,dlen,current_tt)
                    dlen = np.shape(tenshots_tt)[0]
                time.sleep(0.01)
            tenshots_tt = np.delete(tenshots_tt,0)
            ave_tt = np.mean(tenshots_tt)
            print("Moving average of timetool value:", ave_tt)
    
            if np.abs(ave_tt) > tt_window:
                ave_tt_second=-(ave_tt*1e-12)#delay with the unit of second
                #m.lxt.mvr(ave_tt_second)#for XPP use
                matlabPV_FB(ave_tt_second)
                print("feedback %f ps"%ave_tt)
                fbvalue = ave_tt + fbvalue
                drift_log(str(fbvalue))
        return


def drift_log(idata):
    savefilename = "/cds/home/opr/xppopr/experiments/xpplu9818/drift_log_Apr13.txt"
    currenttime = time.ctime()
    out_f = open(savefilename,'a')
    out_f.write(str(idata)+ "," + currenttime.split(" ")[3] +"\n")
    out_f.close()

def matlabPV_FB(feedbackvalue):
    matPV = EpicsSignal('LAS:FS11:VIT:matlab:04')
    org_matPV = matPV.get()#the matlab PV value before FB
    fbvalns = feedbackvalue * 1e+9#feedback value in ns
    fbinput = org_matPV - fbvalns
    matPV.put(fbinput) 
    
    




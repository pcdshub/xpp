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
def tt_rough_FB():
    ...:     while(1):
    ...:         tenshots_tt = np.zeros([0,])
    ...:         dlen = 0
    ...:         while(dlen < 61):
    ...:             ttcomm = Popen("caget XPP:TIMETOOL:TTALL",shell = True, stdout=PIPE)
    ...:             ttdata = (ttcomm.communicate()[0]).decode()
    ...:             current_tt = float((ttdata.split(" "))[3])
    ...:             ttamp = float((ttdata.split(" "))[4])
    ...:             ipm2val = float((ttdata.split(" "))[5])
    ...:             ttfwhm = float((ttdata.split(" "))[7])
    ...:             if(dlen%10 == 0):
    ...:                 print("tt_value",current_tt,"ttamp",ttamp,"ipm2",ipm2val)
    ...:             if (ttamp > 0.03)and(ipm2val > 3000)and(ttfwhm < 130)and(ttfwhm > 70):
    ...:                 tenshots_tt = np.insert(tenshots_tt,dlen,current_tt)
    ...:             dlen = np.shape(tenshots_tt)[0]
    ...:             
    ...:  
    ...:             time.sleep(0.1)
    ...:         tenshots_tt = np.delete(tenshots_tt,0)
    ...:         ave_tt = np.mean(tenshots_tt)
    ...:         print("Moving average of timetool value:", ave_tt)
    ...:         if np.abs(ave_tt) > 0.1:
    ...:             ave_tt_second=-(ave_tt*1e-12)
    ...:             m.lxt.mvr(ave_tt_second)
    ...:             print("feedback %f ps"%ave_tt)


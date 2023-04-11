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
import pexpect

def startami():
    savefilename = "/cds/home/opr/xppopr/experiments/xpplw8419/amirestart_log_Dec5.txt"
    #proc = Popen("startami -s",shell = True, stdout=PIPE) for xpp-control
    proc = pexpect.spawnu("startami -s")#for xppdaq
    proc.expect(['Do you really intend to restart the ami_client on DAQ is running on xpp-daq? (y/n)'],timeout = 5)
    proc.sendline("y")
    numline = countline(savefilename)
    elog.post("ami_restarted_{}".format(numline))
    ami_log(savefilename)
    return

def startami_XPPC():
    savefilename = "/cds/home/opr/xppopr/experiments/xpplw8419/amirestart_log_Dec5.txt"
    proc = Popen("startami -s",shell = True, stdout=PIPE) for xpp-control
    #prco = pexpect.spawnu("startami -s")#for xppdaq
    #proc.expect([' Do you really intend to restart the ami_client on DAQ is running on xpp-daq? (y/n)'],timeout = 30)
    #proc.sendline("y")
    numline = countline(savefilename)
    elog.post("ami_restarted_{}".format(numline))
    ami_log(savefilename)
    return


def countline(savefilename):
    if os.path.exists(savefilename) == True:
        numlines = sum(1 for line in open(savefilename)) 
    else:  
        in_f = open(savefilename,"w")
        in_f.close()
        numlines = sum(1 for line in open(savefilename)) 
    return (numlines+1)
 
def ami_log(savefilename):
    currenttime = time.ctime()
    out_f = open(savefilename,'a')
    out_f.write(currenttime.split(" ")[3] +"\n")
    out_f.close()



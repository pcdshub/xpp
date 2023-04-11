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
from ophyd import Component as Cpt
from ophyd import Device
from pcdsdevices.interface import BaseInterface
from pcdsdevices.areadetector import plugins
from xpp.devices import ImagerHdf5
from xpp.db import daq
from xpp.db import camviewer
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger


class TTALL_Record():
    def __init__(self, pvname='XPP:TIMETOOL:TTALL',time=1, 
                   filename=None):
        self.collection_time = time
        self.arr = []
        self.pvname = pvname
        self.sig = EpicsSignalRO(pvname)
        try:
            self.sig.wait_for_connection(timeout=3.0)
        except TimeoutError:
            print(f'Could not connect to data PV {pvname}, timed out.')
            print('Either on wrong subnet or the ioc is off.')
        if filename is not None:
            self.filename = filename
        else:
            self.setFilename()

    def cb(self, value, **kwargs):
        self.arr.append(value)

    def setCollectionTime(self, ctime=None):
        self.collection_time = ctime

    def collectData(self, collection_time = None):
        if collection_time is not None:
            self.setCollectionTime(collection_time)
        cbid = self.sig.subscribe(self.cb)
        time.sleep(self.collection_time)
        self.sig.unsubscribe(cbid)

    def setFilename(self, basename=None, useTime=False):
        if basename is None:
            basename = self.pvname.split(':')[0]+'_timetool_data'
        if useTime:
            self.filename = basename+'_{}'.format(int(time.time()))
        else:
            self.filename = basename
        
    def writeFile(self):
        #print('saving to {}'.format(self.filename))
        with open(self.filename, 'w') as fd:
            for value in self.arr:
                print(value, file=fd)
        #if len(self.arr) == 0:
        #    print('Warning: no data points collected! File is empty!')
        self.arr = []


class User():
    def __init__(self):
        self.t0 = 894756
        try:
            self.im1l0_h5 = ImagerHdf5(camviewer.im1l0)
            self.im2l0_h5 = ImagerHdf5(camviewer.im2l0)
            self.im3l0_h5 = ImagerHdf5(camviewer.im3l0)
            self.im4l0_h5 = ImagerHdf5(camviewer.im4l0)
            self.gige13_h5 = ImagerHdf5(camviewer.xpp_gige_13)
        except:
            self.im1l0_h5 = None
            self.im2l0_h5 = None
            self.im3l0_h5 = None
            self.im4l0_h5 = None
        self.ttall_record = TTALL_Record()

    ###############################################################################################
    #                   Functions from default files
    ###############################################################################################
    def takeRun(self, nEvents, record=None):
        daq.configure(events=nEvents, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    def takeRun_wTTALL(self, nEvents, record=None):
        daq.configure(events=nEvents, record=record)
        self.ttall_record.setFilename(useTime=True)
        self.ttall_record.collectData(int(nEvents/120))
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()
        self.ttall_record.writeFile()

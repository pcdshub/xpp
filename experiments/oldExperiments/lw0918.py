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
from bluesky.plans import count
from ophyd import Component as Cpt
from ophyd import Device
from pcdsdevices.interface import BaseInterface
from pcdsdevices.areadetector import plugins
from pcdsdevices.device_types import Trigger
from xpp.db import daq, seq
from xpp.db import camviewer
from xpp.db import RE
from xpp.db import at2l0
from pcdsdevices.device_types import Newport, IMS, Trigger

from bluesky.plan_stubs import configure
from xpp.db import xpp_pulsepicker as pp
from xpp.db import fake_motor


class WFS:
    def __init__(self):
        pass


class LMC(Device):
    cmd_send = Cpt(EpicsSignal, ':SEND', kind='normal')
    cmd_wait = Cpt(EpicsSignal, ':WAIT', kind='normal')

    wf_file = Cpt(EpicsSignal, ':OPEN', kind='normal')
    ncycles = Cpt(EpicsSignal, ':CYCLES', kind='normal')
    fileList = Cpt(EpicsSignal, ':FILES', kind='normal')
    wavetime = Cpt(EpicsSignal, ':WAVETIME', kind='normal')

    x_offset = Cpt(EpicsSignal, ':XOFFSET', kind='normal')
    z_offset = Cpt(EpicsSignal, ':ZOFFSET', kind='normal')

    def updateFilelist(self):
        self._fileList = self.fileList.enum_strs

    def listFiles(self):
        self.updateFilelist()
        print('Available files:',self._fileList)

    def status(self):
        self.updateFilelist()
        print('Current file loaded:',self.wf_file.get())
        print('N cycles:',self.ncycles.get())
        self.listFiles()

    def selectFile(self, fileName=None):
        if not fileName in self.fileList:
            self.updateFilelist()
        if fileName is not None and not fileName in self._fileList:
            print('Requested file %s is not in filelist'%(fileName))
            print('Files currently available:', self._fileList)
            return
        for ifile, thisfile in self._fileList:
            if thisfile == fileName:
                print('I would write file %d now'%ifile)
                #self.wf_file.put(ifile)

    def move_x(self, position):
        self.x_offset.put(position)
    
    def move_z(self, position):
        self.z_offset.put(position)

class User():
    def __init__(self):
        self._sync_markers = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7}
        try:
            self.t0 = 880000
        except:
            self.t0 = None
        with safe_load('lom_th2'):
            self.lom_th2 = IMS('XPP:MON:MMS:13', name='lom_th2')
        with safe_load('Be_motors'):
            #self.crl_x = IMS('XPP:SB2:MMS:13', name='crl_x')
            #self.crl_y = IMS('XPP:SB2:MMS:14', name='crl_y')
            #self.crl_z = IMS('XPP:SB2:MMS:15', name='crl_z')
            self.lens_x = IMS('XPP:USR:MMS:21', name='lens_x')
            self.lens_y = IMS('XPP:USR:MMS:22', name='lens_y')
            self.lens_theta_x = IMS('XPP:USR:MMS:23', name='lens_theta_x')
            self.lens_theta_y = IMS('XPP:USR:MMS:24', name='lens_theta_y')
        with safe_load('user_newports'):
            #self.pr_phi = Newport('XPP:USR:MMN:08', name='pr_phi')
            #self.pr_th = Newport('XPP:USR:MMN:05', name='pr_th')
            #self.pr_x = Newport('XPP:USR:MMN:06', name='pr_x')
            #self.pr_z = Newport('XPP:USR:MMN:07', name='pr_z')
            self.sam_translation = Newport('XPP:USR:MMN:01', name='sam_translation')
            self.sam_rotation = Newport('XPP:USR:MMN:02', name='sam_rotation')
            self.det_x = Newport('XPP:USR:PRT:MMN:03', name='det_x')
            self.op_rot = Newport('XPP:USR:PRT:MMN:04', name='op_rot')
            self.grating_y = Newport('XPP:USR:PRT:MMN:05', name='grating_y')
            self.grating_x = Newport('XPP:USR:PRT:MMN:06', name='grating_x')
            self.op_x = Newport('XPP:USR:PRT:MMN:07', name='op_x')
            self.grating_z = Newport('XPP:USR:PRT:MMN:08', name='grating_z')
        with safe_load('user_dumb'):
            #self.pl_x = IMS('XPP:USR:MMS:23', name='pl_x')
            #self.pl_y = IMS('XPP:USR:MMS:24', name='pl_y')
            #self.pl_th = IMS('XPP:USR:MMS:28', name='pl_th')
            #self.vpl_y = IMS('XPP:USR:MMS:29', name='vpl_y')
            #self.vpl_th = IMS('XPP:USR:MMS:30', name='vpl_th')
            self.sam_y = IMS('XPP:USR:MMS:31', name='sam_y')
            self.us_ygap = IMS('XPP:USR:MMS:25', name='us_ygap')
            self.us_yoff = IMS('XPP:USR:MMS:28', name='us_yoff')
            self.us_xgap = IMS('XPP:USR:MMS:29', name='us_xgap')
            self.us_xoff = IMS('XPP:USR:MMS:30', name='us_xoff')
            self.sam_z = IMS('XPP:USR:PRT:MMS:17', name='sam_z')
            self.sam_x = IMS('XPP:USR:PRT:MMS:20', name='sam_x')
            self.bb_x = IMS('XPP:USR:PRT:MMS:18', name='bb_x')
            #self.op_y = IMS('XPP:USR:PRT:MMS:18', name='op_y')
            self.bb_y = IMS('XPP:USR:PRT:MMS:19', name='bb_y')
            self.ds_ygap = IMS('XPP:USR:PRT:MMS:21', name='ds_ygap')
            self.ds_yoff = IMS('XPP:USR:PRT:MMS:22', name='ds_yoff')
            self.ds_xgap = IMS('XPP:USR:PRT:MMS:23', name='ds_xgap')
            self.ds_xoff = IMS('XPP:USR:PRT:MMS:24', name='ds_xoff')
        with safe_load('trigger'):
            self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
            #self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp_temp')
            self.evr_pp = Trigger('XPP:R30:EVR:26:TRIG3', name='evr_pp_temp')
            self.delay = self.evr_R30E28.ns_delay
        with safe_load('lmc'):
            self.lmc = LMC(name='lmc',prefix='XPP:LMC:01')


    def takeRun(self, nEvents, record=None):
        daq.configure(events=nEvents, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

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

    ### LW09 specific functions ###

    def prepare_seq_freeRun(self):
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        ff_seq = [[98, 0, 0, 0]]
        #logging.debug("Sequence: {}".format(fly_seq))                  
        seq.sequence.put_seq(ff_seq) 

    def prepare_seq_PPburst(self, nShots=None, nWaitShots=None, noLmc=False):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
        #seq.rep_count.put(nshots) # Run sequence N Times
    
        ff_seq = [[94, 0, 0, 0]]
        if noLmc:
            ff_seq.append([96, 2 , 0, 0])
        else:
            ff_seq.append([98, 2 , 0, 0])
        if nShots is not None:
            if isinstance(nShots , int):
                ff_seq.append([94, nShots-2, 0, 0])
            else:
                ff_seq.append([94, int(nShots*120)-2, 0, 0])
        if nWaitShots is not None:
            if isinstance(nWaitShots , int):
                ff_seq.append([96, nWaitShots-2, 0, 0])
            else:
                ff_seq.append([96, int(nWaitShots*120)-2, 0, 0])

        #logging.debug("Sequence: {}".format(fly_seq))                  
        seq.sequence.put_seq(ff_seq) 

    def set_pp_burst(self):
        burstdelay=4.5e-3*1e9
        flipflopdelay=8e-3*1e9
        followerdelay=3.8e-5*1e9
        self.evr_pp.ns_delay.set(burstdelay)
        pp.burst(wait=True)

    def lmcScan(self, nRepeats=1, usePP=True, record=None, use_l3t=False, lmcScanTime=None, postWaitTime=0.1, noLmc=False):
        if lmcScanTime is None:
            lmcScanTime = float(self.lmc.wavetime.get())
        if usePP:
            self.set_pp_burst()
            self.prepare_seq_PPburst(nShots=lmcScanTime, nWaitShots=postWaitTime, noLmc=noLmc)
            # wait for sequence to be applied
            time.sleep(3)
        else:
            self.prepare_seq_freeRun()
        daq.configure(0, record=record, use_l3t=use_l3t)
        RE(count([daq, seq], num=nRepeats))
    

    #def lmc_ascan(self, motor, start, end, nsteps, nEvents, record=None):
    #    
    #    currPos = self.lmc.x_move.get()
    #    daq.configure(nEvents, record=record, controls=[motor])
    #    RE(scan([daq], motor, start, end, nsteps))
    #    self.lmc.x_move.set(currPos)



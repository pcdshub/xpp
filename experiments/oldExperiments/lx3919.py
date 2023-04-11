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
from pcdsdevices.interface import BaseInterface, tweak_base
from pcdsdevices.device import UnrelatedComponent as UCpt
from pcdsdevices.pseudopos import (PseudoPositioner, PseudoSingleInterface,
                                   real_position_argument, pseudo_position_argument)
from pcdsdevices.epics_motor import MMC100

from bluesky.plan_stubs import configure
from xpp.db import xpp_pulsepicker as pp
from xpp.db import fake_motor

from epics import camonitor, camonitor_clear, PV
import requests

#from psp import Pv
#gdet = Pv.Pv('GDET:FEE1:242:ENRC')

lmc_trig = PV('XPP:LMC:01:TRIG.PROC')

# get the x-ray pulse energy
pulse = EpicsSignal('XPP:SB2:BMMON:SUM')


class WFS:
    def __init__(self):
        pass


class LMC(Device):
    cmd_send = Cpt(EpicsSignal, ':SEND', kind='normal')
    cmd_wait = Cpt(EpicsSignal, ':WAIT', kind='normal')
    cmd_trig = Cpt(EpicsSignal, ':TRIG', kind='normal')

    wf_file = Cpt(EpicsSignal, ':OPEN', kind='normal')
    ncycles = Cpt(EpicsSignal, ':CYCLES', kind='normal')
    fileList = Cpt(EpicsSignal, ':FILES', kind='normal')
    wavetime = Cpt(EpicsSignal, ':WAVETIME', kind='normal')
    running = Cpt(EpicsSignal, ':SCAN_RUNNING', kind='normal')
    disable = Cpt(EpicsSignal, ':DISABLE', kind='normal')

    x_offset = Cpt(EpicsSignal, ':XOFFSET', kind='normal')
    z_offset = Cpt(EpicsSignal, ':ZOFFSET', kind='normal')
    tomo = Cpt(EpicsSignal, ':TOMO', kind='normal')

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


class XZStage(BaseInterface, PseudoPositioner):
     z0 = UCpt(MMC100 , kind='config')
     x0 = UCpt(MMC100, kind='config')
     theta = UCpt(IMS, kind='config')

     z = Cpt(PseudoSingleInterface, kind='hinted')
     x = Cpt(PseudoSingleInterface, kind='hinted')

     def __init__(self, **kwargs):
         UCpt.collect_prefixes(self, kwargs)
         super().__init__('', **kwargs)
 
     @pseudo_position_argument
     def forward(self, pseudo_pos):
         theta = self.theta.position
         z0=pseudo_pos.z*np.cos(theta)+pseudo_pos.x*np.sin(theta)
         x0=-pseudo_pos.z*np.sin(theta)+pseudo_pos.x*np.cos(theta)

         return self.RealPosition(x0=x0,z0=z0,theta=theta)

     @real_position_argument
     def inverse(self, real_pos):
         theta = real_pos.theta
         z = real_pos.z0*np.cos(theta)-real_pos.x0*np.sin(theta)
         x = real_pos.z0*np.sin(theta)+real_pos.x0*np.cos(theta)

         return self.PseudoPosition(x=x,z=z)

     def tweak(self):
         return tweak_base(self.x,self.z)


class User():
    def __init__(self):
        self._sync_markers = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7}
        self.sam_r= IMS('XPP:USR:MMS:30',name='sam_r')
        try:
            self.t0 = 880000
        except:
            self.t0 = None
        with safe_load('trigger'):
            #self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
            #self.evr_pp = Trigger('XPP:R30:EVR:26:TRIG3', name='evr_pp_temp')
            #self.delay = self.evr_R30E28.ns_delay
            self.evr_USR1 = Trigger('XPP:USR:EVR:TRIG1', name='evr_USR1')
            self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp_temp')
            self.delay = self.evr_USR1.ns_delay
        with safe_load('lmc'):
            self.lmc = LMC(name='lmc',prefix='XPP:LMC:01')
        with safe_load('ipm2 signal'): 
            self.pulse = EpicsSignal('XPP:SB2:BMMON:SUM')

        self.ws_url = 'https://pswww.slac.stanford.edu/ws/lgbk/lgbk/xpplx3919/ws/current_run'

        #with safe_load('xz_stage'):
        #    self.xz = XZStage(x0_prefix='XPP:USR:MMC:01', z0_prefix='XPP:USR:MMC:02',
        #                      theta_prefix='XPP:USR:MMS:26', name='xz_stage')


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
            self.lmc.wavetime.put(1)
            time.sleep(10)
            lmcScanTime = float(self.lmc.wavetime.get())*1.5
            print('Scan time estimate: {} s.'.format(lmcScanTime))
        if usePP:
            self.set_pp_burst()
            self.prepare_seq_PPburst(nShots=lmcScanTime, nWaitShots=postWaitTime, noLmc=noLmc)
            # wait for sequence to be applied
            time.sleep(3)
        else:
            self.prepare_seq_freeRun()
        daq.configure(0, record=record, use_l3t=use_l3t)
        self.lmc.cmd_wait.put(1)
        time.sleep(1)
        RE(count([daq, seq], num=nRepeats))

    
    def lmcScan2(self, nRepeats=1, record=None):
        """ Wont freeze termninal, can be a problem to loop scans """
        self.lmc.cmd_send.put(1)
        daq.configure(0, record=record)
        time.sleep(10)
        self.lmc.cmd_wait.put(1)
        #self.callback_count = 0
        #camonitor(self.lmc.running.pvname, callback=self.daq_monitor)
        daq.begin()
        print('Start run')
        pp.open()
        print('Open pulse picker')
        time.sleep(0.5)
        print('Send trigger to LMC')
        self.lmc.cmd_trig.put(1)
        time.sleep(0.5) # just to make sure we start monitoring the PV when scan_running=1
        camonitor(self.lmc.running.pvname, callback=self.daq_monitor)
        return
    
    def daq_monitor(self, **kwargs):
        if kwargs['value']==0: #and self.callback_count!=0:
            time.sleep(0.5)
            daq.end_run()
            pp.close()
            print('Run ended, close pulse picker.')
            camonitor_clear(self.lmc.running.pvname)
            print('Stop monitor')
        #elif kwargs['value']==1:
        #    daq.begin()
        #    pp.open()
        #    print('Run started')
        #self.callback_count+=1
        return
    
    def lmcTomo(self, angleList, record=None):
        initialAngle=self.sam_r.wm()
        for angle in angleList:
            self.sam_r.umv(angle)
            self.lmc.tomo.put(angle)
            self.lmcScan3(record=record)
        #self.lmc.tomo.put(initialAngle)
        return

    def lmcTomo2(self, angleList, record=None):
        initialAngle=self.sam_r.wm()
        for angle in angleList:
            self.sam_r.umv(angle)
            self.lmc.tomo.put(angle)
            restart = self.lmcScan4(record=record)
            while (restart > 2):
                print('Restarting')
                restart = self.lmcScan4(record=record)
            print('scan done at angle %.3f' % angle)
        #self.lmc.tomo.put(initialAngle)
        return

    def lmcScan3(self, record=None):
        """ Will freeze terminal. To be used in scan loops. """
        self.lmc.cmd_send.put(1)
        daq.configure(0, record=record)
        time.sleep(0.2)
        while(self.lmc.disable.get()==1):
            time.sleep(0.2)
        self.lmc.cmd_wait.put(1)
        daq.begin()
        print('Start run')
        pp.open()
        print('Open pulse picker')
        time.sleep(1)
        print('Send trigger to LMC')
        #self.lmc.cmd_trig.put(1)
        lmc_trig.put(1)
        time.sleep(0.5) # just to make sure we start monitoring the PV when scan_running=1
        while(self.lmc.running.get()==1):
            time.sleep(0.5)
        time.sleep(0.2)
        daq.end_run()
        pp.close()
        print('Run ended, close pulse picker.')
        return


    def lmcScan4(self, record=None):
        """ Will freeze terminal. To be used in scan loops. """
        self.lmc.cmd_send.put(1)
        daq.configure(0, record=record)
        time.sleep(0.2)
        while(self.lmc.disable.get()==1):
            time.sleep(0.2)
        self.lmc.cmd_wait.put(1)
        daq.begin()
        print('Start run')
        pp.open()
        print('Open pulse picker')
        time.sleep(1)
        print('Send trigger to LMC')
        #self.lmc.cmd_trig.put(1)
        lmc_trig.put(1)
        time.sleep(0.5) # just to make sure we start monitoring the PV when scan_running=1
        redo = 0
        while(self.lmc.running.get()==1):
            val = 0.
            for i in range(120):
                time.sleep(0.00833)
                val += self.pulse.get()
            val = val/120.
            if (val < 500):
                redo += 1
        time.sleep(0.2)
        daq.end_run()
        pp.close()
        redo_daq = 0
        #time.sleep(1.0)
        
        run_param = requests.get(self.ws_url).json()['value']['params']
        while not 'DAQ Detector Totals/Events' in run_param.keys():
            time.sleep(0.1)
            run_param = requests.get(self.ws_url).json()['value']['params']
        nEvents = run_param['DAQ Detector Totals/Events']
        print('We got ' + str(nEvents) + ' events')
        if nEvents<1000:
            redo_daq = 3
        
            #redo_daq=0

        redo += redo_daq
        print('Run ended, close pulse picker.')
        return redo



    #def lmc_ascan(self, motor, start, end, nsteps, nEvents, record=None):    
    #    currPos = self.lmc.x_move.get()
    #    daq.configure(nEvents, record=record, controls=[motor])
    #    RE(scan([daq], motor, start, end, nsteps))
    #    self.lmc.x_move.set(currPos)

    # defining motors for preset functions
    # for the phase corrector 
    pc_x_val = EpicsSignal('XPP:USR:MMN:25')
    pc_y_val = EpicsSignal('XPP:USR:MMN:26')

    # for the pinhole
    ph_x_val = EpicsSignal('XPP:USR:MMS:18')
    ph_y_val = EpicsSignal('XPP:USR:MMS:17')
    ph_z_val = EpicsSignal('XPP:USR:MMS:29')

    # for the target positions
    sam_cx_val = EpicsSignal('XPP:USR:MMS:27')
    sam_cz_val = EpicsSignal('XPP:USR:MMS:28')
    sam_x_val = EpicsSignal('XPP:USR:MMN:28')
    sam_y_val = EpicsSignal('XPP:USR:MMS:25')
    sam_z_val = EpicsSignal('XPP:USR:MMN:27')
    sam_r_val = EpicsSignal('XPP:USR:MMS:30')

    # for the CRL
    crl_x_val = EpicsSignal('XPP:USR:MMS:24')
    crl_y_val = EpicsSignal('XPP:USR:MMS:20')
    crl_z_val = EpicsSignal('XPP:USR:MMS:21')
    crl_thx_val = EpicsSignal('XPP:USR:MMS:22')
    crl_thy_val = EpicsSignal('XPP:USR:MMS:23')
    crl_thz_val = EpicsSignal('XPP:USR:MMS:24')

    def yag_in(self):
        self.sam_cx_val.put(-3.54)
        self.sam_cz_val.put(-11.82)
        self.sam_x_val.put(0.0)
        self.sam_y_val.put(-1.2)
        self.sam_z_val.put(0.0)
        self.sam_r_val.put(0)
        print('YAG is IN.')

    def ronN_in(self):
        self.sam_cx_val.put(4.835)
        self.sam_cz_val.put(-11.795)
        self.sam_x_val.put(0.0)
        self.sam_y_val.put(-0.993)
        self.sam_z_val.put(0.0)
        self.sam_r_val.put(0)
        print('Ronchi N is IN.')

    def rs3_in(self):
        self.sam_cx_val.put(0.66)
        self.sam_cz_val.put(-11.82)
        self.sam_x_val.put(0.0)
        self.sam_y_val.put(-1.2)
        self.sam_z_val.put(0.0)
        self.sam_r_val.put(0)
        print('RS3 is IN.')

    def rs4_in(self):
        self.sam_cx_val.put(0.66)
        self.sam_cz_val.put(-11.82)
        self.sam_x_val.put(0.0)
        self.sam_y_val.put(2.3)
        self.sam_z_val.put(0.0)
        self.sam_r_val.put(0)
        print('RS4 is IN.')

    def rs9_in(self):
        self.sam_cx_val.put(9.135)
        self.sam_cz_val.put(-11.795)
        self.sam_x_val.put(0.0)
        self.sam_y_val.put(-1.15)
        self.sam_z_val.put(0.0)
        self.sam_r_val.put(0)
        print('RS9 is IN.')

    def pc_in(self):
        self.pc_x_val.put(0.0453)
        self.pc_y_val.put(0.0172)
        print('Phase corrector is IN.')
    
    def pc_out(self):
        self.pc_x_val.put(12.0)
        self.pc_y_val.put(0.0172)
        print('Phase corrector is OUT.')

    def ph_in(self):
        self.ph_y_val.put(-0.0950)
        self.ph_x_val.put(-0.7125)
        time.sleep(6)
        self.ph_z_val.put(-28)
        print('X-ray pinhole is IN.')

    def ph_out(self):
        self.ph_y_val.put(-0.095)
        self.ph_z_val.put(-40)
        time.sleep(6)
        self.ph_x_val.put(-10)
        print('X-ray pinhole is OUT.')

    def print_crl_status(self):
        print('CRL X value: {} mm'.format(self.crl_x_val.get()))
        print('CRL Y value: {} mm'.format(self.crl_y_val.get()))
        print('CRL Z value: {} mm'.format(self.crl_z_val.get()))
        print('CRL theta X value: {} mm'.format(self.crl_thx_val.get()))
        print('CRL theta Y value: {} mm'.format(self.crl_thy_val.get()))
        print('CRL theta Z value: {} mm'.format(self.crl_thz_val.get()))

    def print_sam_status(self):
        print('Sample coarse X value: {} mm'.format(self.sam_cx_val.get()))
        print('Sample coarse Z value: {} mm'.format(self.sam_cz_val.get()))
        print('Sample fine X value: {} mm'.format(self.sam_x_val.get()))
        print('Sample fine Y value: {} mm'.format(self.sam_y_val.get()))
        print('Sample Fine Z value: {} mm'.format(self.sam_z_val.get()))
        print('Sample rotation value: {} deg'.format(self.sam_r_val.get()))

    def print_status(self):
        self.print_crl_status()
        self.print_sam_status()

    def angle(self,offset, stepsize):
        return [i for i in np.arange(-180+offset, 160+stepsize+offset, stepsize)]


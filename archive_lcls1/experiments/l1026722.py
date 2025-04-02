import subprocess
import json
import sys
import time
import os
from pathlib import Path

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
from pcdsdevices.device_types import Trigger
from xpp.db import daq, seq
from xpp.db import camviewer
from xpp.db import RE
from pcdsdevices.device_types import Newport, IMS, Trigger
from pcdsdevices.interface import BaseInterface, tweak_base
from pcdsdevices.device import UnrelatedComponent as UCpt
from pcdsdevices.pseudopos import (
    PseudoPositioner, 
    PseudoSingleInterface,
    real_position_argument, 
    pseudo_position_argument
)
from pcdsdevices.epics_motor import MMC100

from bluesky.plan_stubs import configure
from xpp.db import xpp_pulsepicker as pp
from xpp.db import fake_motor

from epics import camonitor, camonitor_clear, PV
import requests


lmc_trig = PV('XPP:LMC:01:TRIG.PROC')

# get the x-ray pulse energy
pulse = EpicsSignal('XPP:SB2:BMMON:SUM')


class WFS:
    def __init__(self):
        pass


class EpicsSignalSettle(EpicsSignal):
    def __init__(self, *args, settle_time=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.settle_time = settle_time
        return

    def set(self, value, *args, settle_time=None, **kwargs):
        if settle_time is None:
            settle_time = self.settle_time
        status = super().set(value, *args, settle_time=settle_time, **kwargs)
        return status


class LMC(Device):
    cmd_send = Cpt(EpicsSignal, ':SEND', kind='normal')
    cmd_wait = Cpt(EpicsSignal, ':WAIT', kind='normal')
    cmd_trig = Cpt(EpicsSignal, ':TRIG.PROC', kind='normal')
    cmd_save = Cpt(EpicsSignal, ':SAVEDATA', kind='normal')
    cmd_runnum = Cpt(EpicsSignal, ':RUN_NUM', kind='normal')

    ncycles = Cpt(EpicsSignal, ':CYCLES', kind='normal')
    running = Cpt(EpicsSignal, ':SCAN_RUNNING', kind='normal')
    disable = Cpt(EpicsSignal, ':DISABLE', kind='normal')

    x_offset = Cpt(EpicsSignal, ':XOFFSET', kind='normal')
    z_offset = Cpt(EpicsSignal, ':ZOFFSET', kind='normal')
    tomo = Cpt(EpicsSignal, ':TOMO', kind='hinted')

    x = Cpt(EpicsSignalSettle, ':MOVEX', kind='hinted', settle_time=0.1)
    y = Cpt(EpicsSignalSettle, ':MOVEY', kind='hinted', settle_time=0.1) 
    z = Cpt(EpicsSignalSettle, ':MOVEZ', kind='hinted', settle_time=0.1) 

    def move_x_offset(self, position):
        self.x_offset.put(position)
    
    def move_z_offset(self, position):
        self.z_offset.put(position)


class XZStage(BaseInterface, PseudoPositioner):
     z0 = UCpt(MMC100, kind='config')
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
        self.sam_rot= IMS('HXR:PRT:01:MMS:10',name='sam_rot')
        try:
            self.t0 = 880000
        except:
            self.t0 = None
        with safe_load('trigger'):
            self.evr_USR1 = Trigger('XPP:USR:EVR:TRIG1', name='evr_USR1')
            self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp_temp')
            self.delay = self.evr_USR1.ns_delay
        with safe_load('lmc'):
            self.lmc = LMC(name='lmc',prefix='XPP:LMC:01')
        with safe_load('ipm2 signal'): 
            self.pulse = EpicsSignal('XPP:SB2:BMMON:SUM')

        self.ws_url = 'https://pswww.slac.stanford.edu/ws/lgbk/lgbk/xppl1026722/ws/current_run'

        #with safe_load('xz_stage'):
        #    self.xz = XZStage(x0_prefix='XPP:USR:MMC:01', z0_prefix='XPP:USR:MMC:02',
        #                      theta_prefix='XPP:USR:MMS:26', name='xz_stage')


    ### Exp specific functions ###

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
    

    def lmcTomo(self, angleList, record=True):
        initialAngle = self.sam_rot.wm()
        for angle in angleList:
            self.sam_rot.umv(angle)
            self.lmc.tomo.put(angle)
            restart = self.lmcScan(record=record)
            #while (restart > 2):
            #    print('Restarting')
            #    restart = self.lmcScan(record=record)
            print('Scan done at angle %.3f' % angle)
        #self.lmc.tomo.put(initialAngle)
        return


    def lmcScan(self, record=True):
        """ Will freeze terminal. To be used in scan loops. """
        # LMC Send and configure DAQ
        self.lmc.cmd_send.put(1)
        daq.configure(0, record=record)
        time.sleep(0.1)
        while(self.lmc.disable.get()==1):
            time.sleep(0.05)
        
        # LMC Wait and start DAQ
        self.lmc.cmd_wait.put(1)
        print('Start run')
        daq.begin()
        #print('Open pulse picker')
        #pp.open()
        time.sleep(0.2)

        # Send run number to lmc
        print('Send run number to LMC')
        run = daq._control.runnumber()
        print(f'Run {run}')
        self.lmc.cmd_runnum.put(run)
        time.sleep(0.1)

        # Start scan
        print('Send trigger to LMC')
        self.lmc.cmd_trig.put(1)
        
        time.sleep(3) # just to make sure we start monitoring the PV when scan_running=1
        redo = 0

        # Wait for scan to end
        #print(self.lmc.running.get())
        while(self.lmc.running.get()==1):
            time.sleep(0.2)
        time.sleep(0.1)
        daq.end_run()
        #pp.close()
        redo_daq = 0
        
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
        print('Run ended, close pulse picker.\n')

        print('Tell the LMC to save trajectory')
        self.lmc.cmd_save.put(1)
        
        #if run > 0:
        #    print('Copy LMC files.')
        #    self.get_lmc_files(run)
        return redo


    def get_lmc_files(self, run):
        p = Path('/cds/home/opr/xppopr/experiments/xppd00120/lmc_files')
        flist = [
            'distance.flt32', 'pixel_size.flt32', 'scan_positions.flt32', 
            'scan_positions.tsv', 'wavelength.flt32'
        ]
        cmd = "scp pi@xpp-gleason-lmc:/home/pi/ptycho/data/* /cds/home/opr/xppopr/experiments/xppd00120/lmc_files"
        process = subprocess.run(cmd.split())
        for f in flist: 
            os.rename(p/f, p/f'Run{run:04d}_{f}')
        print('LMC files copied to /cds/home/opr/xppopr/experiments/xppd00120/lmc_files')
        return



    ## defining motors for preset functions
    ## for the phase corrector 
    #pc_x_val = EpicsSignal('XPP:USR:MMN:28')
    #pc_y_val = EpicsSignal('XPP:USR:MMN:29')

    ## for the osa
    osa_x_val = EpicsSignal('XPP:USR:PRT:MMN:01')
    osa_y_val = EpicsSignal('XPP:USR:PRT:MMN:07')
    osa_z_val = EpicsSignal('XPP:USR:PRT:MMN:05')

    ## for the inline
    in_x_val = EpicsSignal('HXR:PRT:01:MMS:09')
    in_y_val = EpicsSignal('XPP:USR:PRT:MMS:25')
    in_z_val = EpicsSignal('HXR:PRT:01:MMS:03')

    ## for the target positions
    sam_cx_val = EpicsSignal('HXR:PRT:01:MMS:01')
    sam_cz_val = EpicsSignal('HXR:PRT:01:MMS:02')
    sam_x_val = EpicsSignal('XPP:USR:PRT:MMN:06')
    sam_y_val = EpicsSignal('HXR:PRT:01:MMS:11')
    sam_z_val = EpicsSignal('XPP:USR:PRT:MMN:02')
    sam_rot_val = EpicsSignal('HXR:PRT:01:MMS:10')

    ## for the zone plate
    zp_x_val = EpicsSignal('HXR:PRT:01:MMS:04')
    zp_y_val = EpicsSignal('HXR:PRT:01:MMS:05')
    zp_z_val = EpicsSignal('HXR:PRT:01:MMS:06')
    zp_pitch_val = EpicsSignal('HXR:PRT:01:MMS:07')
    zp_yaw_val = EpicsSignal('XPP:USR:PRT:MMS:27')

    def yag_in(self):
        self.sam_cx_val.put(28.8)
        self.sam_cz_val.put(-11.53)
        self.sam_x_val.put(-1.908)
        self.sam_y_val.put(0.97)
        self.sam_z_val.put(4.3675)
        self.sam_rot_val.put(0)
        print('YAG is IN.')
        print('inline z is -11.75')

    def ronN_in(self):
        self.sam_cx_val.put(28.8)
        self.sam_cz_val.put(-11.53)
        self.sam_x_val.put(2.5915)
        self.sam_y_val.put(0.97)
        self.sam_z_val.put(4.3675)
        self.sam_rot_val.put(0)
        print('Ronchi N is IN.')
        print('inline z is -11.75')

#    def pc_in(self):
#        self.pc_x_val.put(0.0)
#        self.pc_y_val.put(0.0)
#        print('Phase corrector is IN.')
    
#    def pc_out(self):
#        self.pc_x_val.put(12.0)
#        self.pc_y_val.put(0.0)
#        print('Phase corrector is OUT.')

    def ph_in(self):
        self.osa_y_val.put(9.9039)
        self.osa_x_val.put(4.32435)
        time.sleep(6)
        self.osa_z_val.put(-6)
        print('X-ray pinhole is IN.')

    def ph_out(self):
        self.osa_z_val.put(-10)
        self.osa_y_val.put(-0)
        time.sleep(6)
        self.osa_x_val.put(4.32435)
        print('X-ray pinhole is OUT.')

    def inline_in(self):
        self.in_y_val.put(0.8)
        self.in_z_val.put(-9.325) #coarse z  -3.4, samz 0
        self.in_x_val.put(0.25)
        print('Inline is IN.')

    def inline_out(self):
        self.in_y_val.put(0.8)
        self.in_z_val.put(-9.325) 
        time.sleep(6)
        self.in_x_val.put(-11)
        print('Inline is OUT.')

    def print_pinhole_status(self):
        print('Pinhole X value: {} mm'.format(self.osa_x_val.get()))
        print('Pinhole Y value: {} mm'.format(self.osa_y_val.get()))
        print('Pinhole Z value: {} mm'.format(self.osa_z_val.get()))

    def print_inline_status(self):
        print('Inline X value: {} mm'.format(self.in_x_val.get()))
        print('Inline Y value: {} mm'.format(self.in_y_val.get()))
        print('Inline Z value: {} mm'.format(self.in_z_val.get()))

    def print_zp_status(self):
        print('zp X value: {} mm'.format(self.zp_x_val.get()))
        print('zp Y value: {} mm'.format(self.zp_y_val.get()))
        print('zp Z value: {} mm'.format(self.zp_z_val.get()))
        print('zp pitch value: {} mm'.format(self.zp_pitch_val.get()))
        print('zp yaw value: {} mm'.format(self.zp_yaw_val.get()))

    def print_sam_status(self):
        print('Sample coarse X value: {} mm'.format(self.sam_cx_val.get()))
        print('Sample coarse Z value: {} mm'.format(self.sam_cz_val.get()))
        print('Sample fine X value: {} mm'.format(self.sam_x_val.get()))
        print('Sample fine Y value: {} mm'.format(self.sam_y_val.get()))
        print('Sample Fine Z value: {} mm'.format(self.sam_z_val.get()))
        print('Sample rotation value: {} deg'.format(self.sam_rot_val.get()))

    def print_status(self):
        self.print_zp_status()
        self.print_sam_status()
        self.print_inline_status()
        self.print_pinhole_status()

    def angle(self,offset, stepsize):
        return [i for i in np.arange(-180+offset, 160+stepsize+offset, stepsize)]


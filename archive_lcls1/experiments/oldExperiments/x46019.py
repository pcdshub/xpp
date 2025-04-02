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
from xpp.devices import ImagerHdf5, LaserShutter
from xpp.db import daq
from xpp.db import camviewer
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger

## XY Grid Scan
from pcdsdevices.targets import XYGridStage
from xpp.db import RE, bpp, bps, seq, xpp_gon_kappa
from xpp.db import xpp_pulsepicker as pp
import time


#grid_filepath = '/cds/home/opr/xppopr/experiments/xpplx5019/sample.yml'
grid_filepath = '/cds/home/opr/xppopr/experiments/xpplx5019/' # new version creates one file per sample
if not os.path.exists(grid_filepath):
    open(grid_filepath, 'a').close()

target_x = xpp_gon_kappa.x
target_y = xpp_gon_kappa.y
xy = XYGridStage(target_x, target_y, 1, 10, grid_filepath)


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
        self._sync_markers = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7}
        self.ttall_record = TTALL_Record()
        with safe_load('PP trigger'):
            self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp')
        with safe_load('collimators'):
            #self.col_h = Newport('XPP:USR:MMN:05', name='col_h')
            #self.col_v = Newport('XPP:USR:MMN:06', name='col_v')
            #self.pr_th = Newport('XPP:USR:MMN:01', name='pr_th')
            self.g_x = Newport('XPP:USR:PRT:MMN:01', name='g_x')
            self.g_y = Newport('XPP:USR:PRT:MMN:02', name='g_y')
            self.det_x = Newport('XPP:USR:PRT:MMN:03', name='det_x')
            self.det_th = Newport('XPP:USR:PRT:MMN:04', name='det_th')
            self.g_z = Newport('XPP:USR:PRT:MMN:05', name='g_z')
            self.th2 = IMS('XPP:MON:MMS:13', name='th2')
            self.det_y = IMS('XPP:USR:PRT:MMS:20', name='det_y')
            self.det_focus = IMS('XPP:USR:PRT:MMS:22', name='det_focus')
                

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

    ########################################################################### 
    # Fixed Target Scanning
    tx = target_x
    ty = target_y
    xy = xy
    lp = LaserShutter('XPP:USR:ao1:14', name='lp')

    def init_target_grid(self, m, n, sample_name):
        xy = XYGridStage(target_x, target_y, m, n, grid_filepath)
        xy.set_presets()
        xy.map_points()
        xy.save_grid(sample_name)
        xy.set_current_sample(sample_name)
        self.xy = xy

    def load_sample_grid(self, sample_name):
        self.xy.load_sample(sample_name)
        self.xy.map_points()

    def fts(self, detectors=[], shots_per_slot=1, slot_width=0):    
        length = len(self.xy.positions_x)

        _md = {'detectors': [det.name for det in detectors],
            'motors': [self.xy.x.name,self.xy.y.name],
            'num_points': length,
            'num_intervals': length - 1,
            'plan_name': 'fixed_target_scan',
            'hints': {'dimensions': [(['target_x', 'target_y'], 'primary')]},
            }

        seq.play_mode.put(0)
        if pp.mode.get()!=2:
            pp.set_pp_flipflop()

        @bpp.run_decorator(md=_md)
        def inner_scan():
            for i,j in zip(self.xy.positions_x,self.xy.positions_y):
                for k in range(shots_per_slot):
                    x_pos = i + ((k+1)/(shots_per_slot+1)-1/2)*slot_width
                    y_pos = j
                    yield from bps.mv(self.xy.x, x_pos, self.xy.y, y_pos)
                    yield from bps.trigger_and_read([seq, self.xy.x, self.xy.y])
                    time.sleep(0.1)
        yield from inner_scan()

    # Diling's lazy function for close packing with offsetted rows
    # modified by Tyler and Vincent for professionalism   
    @bpp.run_decorator()
    def gridScan_old(self, motor, posList, sample, iRange, jRange, deltaX):
        iRange = list(iRange)
        jRange = list(jRange)
        if len(posList) != len(iRange):
            print('number of scan steps not matching grid total row number, abort.')
        else:
            xs, ys = xy.compute_mapped_point(sample, 1,1, compute_all=True) # get all positions
            s_shape = xy.get_sample_map_info(sample)
            s_shape = (s_shape[0], s_shape[1])
            for ni,i in enumerate(iRange):
                motor.umv(posList[ni])
                jRange_thisRow = jRange
                #if np.mod(ind, 2)==1:
                    #jRange_thisRow.reverse()
                for j in jRange_thisRow:
                    idx = np.ravel_multi_index([i,j], s_shape) # find raveled index from 2d coord i,j
                    x_pos = xs[idx]
                    y_pos = ys[idx]
                    #x_pos,y_pos = xy.compute_mapped_point(sample, i, j, compute_all=False)
                    if np.mod(i,2)==1:
                        y_pos = y_pos+deltaX
                    yield from bps.mv(self.xy.x, x_pos, self.xy.y, y_pos)
                    yield from bps.trigger_and_read([seq, self.xy.x, self.xy.y])
                    time.sleep(0.2)
                    while seq.play_status.get() == 2: continue
                jRange.reverse()


    @bpp.run_decorator()
    def gridScan(self, motor, posList, sample, iRange, jRange, deltaX, snake=True):
        iRange = list(iRange)
        jRange = list(jRange)
        if len(posList) != len(iRange):
            print('number of scan steps not matching grid total row number, abort.')
        else:
            self.xy.load(sample)
            for ni,i in enumerate(iRange):
                motor.umv(posList[ni])
                jRange_thisRow = jRange
                for j in jRange_thisRow:
                    x_pos,y_pos = xy.compute_mapped_point(i, j, sample, compute_all=False)
                    if np.mod(i,2)==1:
                        x_pos = x_pos+deltaX
                    yield from bps.mv(self.xy.x, x_pos, self.xy.y, y_pos)
                    yield from bps.trigger_and_read([seq, self.xy.x, self.xy.y])
                    time.sleep(0.1)
                    while seq.play_status.get() == 2: continue
                if snake:
                    jRange.reverse()

    


    def gridScan_Daq(self, motor, posList, sample, iRange, jRange, deltaX, snake=True):
        plan = self.gridScan(motor, posList, sample, iRange, jRange, deltaX, snake)
        try:
            daq.disconnect()
        except:
            print('DAQ might be disconnected already')
        daq.connect()
        daq.begin()
        RE(plan)
        # for testing only 
        #seq.start()
        #time.sleep(0.1)
        #while seq.play_status.get() ==2: continue
        daq.end_run()

    def fixed_target_scan(self, detectors=[], shots_per_slot=1, slot_width=0):
        RE(self.fts(detectors=detectors, shots_per_slot=shots_per_slot, slot_width=slot_width))

    def daq_fixed_target_scan(self, detectors=[], shots_per_slot=1, slot_width=0, record=False):
        @bpp.daq_during_decorator(record=record, controls=[self.xy.x, self.xy.y])
        def inner_scan():
            yield from self.fts(detectors=detectors, shots_per_slot=shots_per_slot, slot_width=slot_width)
        RE(inner_scan())


    # to help move quickly between 120Hz CW mode for 
    # alignment and TT checking and single shot mode
    def go120Hz(self):
        try:
            daq.disconnect()
        except:
            print('DAQ might already be disconnected')
        self.lp('IN')
        pp.open()
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(2)
        shot_sequence=[]
        shot_sequence.append([95,0,0,0])
        shot_sequence.append([97,0,0,0])
        seq.sequence.put_seq(shot_sequence) 
        time.sleep(0.5)
        seq.start()
        daq.connect()
        daq.begin_run(record=False)

    def goSS(self, nPre=20, nOn=1, nPost=20):
        daq.end_run()
        daq.disconnect()
        pp.flipflop()
        self.prepare_seq(nPre, nOn, nPost)
        time.sleep(0.2)
        self.lp('OUT')
        
    
    def prepare_seq(self, nShotsPre=30, nShotsOn=1, nShotsPost=30, nBuff=1):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        sync_mark = int(self._sync_markers[10])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
        #seq.rep_count.put(nshots) # Run sequence N Times
    
        ppLine = [94, 2, 0, 0]
        daqLine = [95, 2, 0, 0]
        preLine = [190, 0, 0, 0]
        onLine = [97, 0, 0, 0]
        postLine = [193, 0, 0, 0]
        bufferLine = [95, 1, 0, 0] # line to avoid falling on the parasitic 10Hz from TMO

        shot_sequence=[]
        for buff in np.arange(nBuff):
            shot_sequence.append(bufferLine)
        for preShot in np.arange(nShotsPre):
            shot_sequence.append(ppLine)
            shot_sequence.append(daqLine)
            shot_sequence.append(preLine)
        for onShot in np.arange(nShotsOn):
            shot_sequence.append(ppLine)
            shot_sequence.append(daqLine)
            shot_sequence.append(onLine)
        for postShot in np.arange(nShotsPost):
            shot_sequence.append(ppLine)
            shot_sequence.append(daqLine)
            shot_sequence.append(postLine)

        #logging.debug("Sequence: {}".format(shot_sequence))                  
        seq.sequence.put_seq(shot_sequence) 

    def set_pp_flipflop(self):
        burstdelay=4.5e-3*1e9 # not needed here
        flipflopdelay=8e-3*1e9
        followerdelay=3.8e-5*1e9 # not needed here
        self.evr_pp.ns_delay.set(flipflopdelay) # evr channel needs to be defined
        pp.flipflop(wait=True)

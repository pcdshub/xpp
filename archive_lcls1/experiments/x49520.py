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
from bluesky.plans import scan
from bluesky.plans import list_scan
from ophyd import Component as Cpt
from ophyd import Device
from pcdsdevices.interface import BaseInterface
from pcdsdevices.areadetector import plugins
from xpp.db import daq
from xpp.db import camviewer
from xpp.db import RE, bpp, bps, seq, lp
from xpp.db import at2l0
from xpp.db import s4
from xpp.db import xpp_pulsepicker as pp
from xpp.db import xpp_attenuator as att
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger
from pcdsdevices import analog_signals

from pcdsdevices.targets import XYGridStage
from pcdsdevices.sim import FastMotor, SlowMotor

from pcdsdevices.sequencer import EventSequencer
seq2 = EventSequencer('ECS:SYS0:10', name='seq_10')

grid_filepath = '/cds/home/opr/xppopr/experiments/xppx49520/'
#target_x = FastMotor() # fake motors
#target_y = FastMotor()
target_x = IMS('HXR:PRT:01:MMS:06', name='grid_x')
target_y = IMS('XPP:USR:PRT:MMS:31', name='grid_y')
xy = XYGridStage(target_x, target_y, 1, 10, grid_filepath)


class MpodChannel(Device):
    voltage = Cpt(EpicsSignal, ':GetVoltageMeasurement', write_pv=':SetVoltage', kind='normal')
    current = Cpt(EpicsSignalRO, ':GetCurrentMeasurement', kind='normal')
    state = Cpt(EpicsSignal, ':GetSwitch', write_pv=':SetSwitch', kind='normal')
    # 0 means no EPICS high limit.
    voltage_highlimit = Cpt(EpicsSignal, ':SetVoltage.DRVH', kind='normal')

class User():
    def __init__(self):
        self.t0 = 894756
        self._sync_markers = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7}
        with safe_load('PP trigger'):
            self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp')
        try:
            self.im1l0_h5 = ImagerHdf5(camviewer.im1l0)
            self.im2l0_h5 = ImagerHdf5(camviewer.im2l0)
            self.im3l0_h5 = ImagerHdf5(camviewer.im3l0)
            self.im4l0_h5 = ImagerHdf5(camviewer.im4l0)
            self.gige13_h5 = ImagerHdf5(camviewer.xpp_gige_13)
            self.im1l0_stats = ImagerStats(camviewer.im1l0)
            self.im2l0_stats = ImagerStats(camviewer.im2l0)
            self.im3l0_stats = ImagerStats(camviewer.im3l0)
            self.im4l0_stats = ImagerStats(camviewer.im4l0)
            self.im1l0_stats3 = ImagerStats3(camviewer.im1l0)
            self.im2l0_stats3 = ImagerStats3(camviewer.im2l0)
            self.im3l0_stats3 = ImagerStats3(camviewer.im3l0)
            self.im4l0_stats3 = ImagerStats3(camviewer.im4l0)
        except:
            self.im1l0_h5 = None
            self.im2l0_h5 = None
            self.im3l0_h5 = None
            self.im4l0_h5 = None
            self.im1l0_stats = None
            self.im2l0_stats = None
            self.im3l0_stats = None
            self.im4l0_stats = None
            self.im1l0_stats3 = None
            self.im3l0_stats3 = None
            self.im4l0_stats3 = None
        with safe_load('analog_out'):
            self.aio = analog_signals.Acromag(name = 'xpp_aio', prefix = 'XPP:USR')

    def show_CC(self):
        self.aio.ao1_0.set(0)
        self.aio.ao1_1.set(5)
    def show_VCC(self):
        self.aio.ao1_0.set(5)
        self.aio.ao1_1.set(0)
    def show_both(self):
        self.aio.ao1_0.set(5)
        self.aio.ao1_1.set(5)
    def show_neither(self):
        self.aio.ao1_0.set(0)
        self.aio.ao1_1.set(0)
    ###############################################################################################
    #                   Functions from default files
    ###############################################################################################
    def takeRun(self, nEvents, record=None):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    # dscan & ascan kludge for x421 evr delay scan, as the evr object does not have the wm and mv attributes
    def pvascan(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.get()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.put(currPos)

    def pvdscan(self, motor, start, end, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.get()
        RE(scan([daq], motor, currPos + start, currPos + end, nsteps))
        motor.put(currPos)

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
        RE(scan([daq], motor, currPos + start, currPos + end, nsteps))
        motor.mv(currPos)

    def a2scan(self, m1, a1, b1, m2, a2, b2, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[m1, m2])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, nsteps))

    def a3scan(self, m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[m1, m2, m3])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps))

    def set_current_position(self, motor, value):
        motor.set_use_switch.put(1)
        motor.set_use_switch.wait_for_connection()
        motor.user_setpoint.put(value, force=True)
        motor.user_setpoint.wait_for_connection()
        motor.set_use_switch.put(0)


    def si220bragg(self,energy_kev):
        """
        Get the bragg angle in degree for Silicon 220 and energy in keV

        :param energy_kev: This can be either a float number, or a numpy array.
        :return:
        """
        # Define constants for the conversion
        hbar_local = 0.0006582119514  # This is the reduced planck constant in keV/fs
        c_local = 299792458. * 1e-9  # The speed of light in um / fs

        # Get the reciprocal lattice for Si 220
        reciprocal_lattice_local = 2. * np.pi / (1.9201 / 10. / 1000.)  # um^-1

        # Convert energy to wavevector
        wave_number_local = energy_kev / hbar_local / c_local

        # Get the angle in radian
        bragg_angle_local = np.arcsin(reciprocal_lattice_local / 2. / wave_number_local)

        # Convert the bragg angle from radian to degree
        bragg_angle_local = np.rad2deg(bragg_angle_local)
    
        return bragg_angle_local
  
    def move_unfocused(self):
        att(1e-6)
        self.crl_x.umv_X495_clear()
        self.crl_y.umv_X495_clear()
        att(1)
        print('CRL OUT.')

    def move_focused(self):
        att(1e-6)
        self.crl_x.umv_X495_SD_beam()
        self.crl_y.umv_X495_SD_beam()
        att(0.1)
        print('CRL IN.')

    def move_silica(self):
        att(1e-6)
        self.grid_x.umv_X495_silica() 
        self.grid_y.umv_X495_silica() 
        att(0.05)
        print ('silica in')
    
    def move_frosted_LuAG(self):
        att(1e-6)
        self.grid_x.umv_X495_frosted_LuAG() 
        self.grid_y.umv_X495_frosted_LuAG() 
        att(0.1)
        print ('frosted LuAG in')


    def print_JJ(self):
        print ("JJ1 {:.2f} {:.2f}".format(self.jjhg1.wm(),self.jjvg1.wm()))
        print ("JJ2 {:.2f} {:.2f}".format(self.jjhg2.wm(),self.jjvg2.wm()))
        print ("s4 {:.2f} {:.2f}".format(s4.hg.wm(),s4.vg.wm()))

    xy = xy
    
    def init_target_grid(self, m, n, sample_name):
        xy = XYGridStage(target_x, target_y, m, n, grid_filepath)
        xy.set_presets()
        xy.map_points()
        xy.save_grid(sample_name)
        #xy.set_current_sample(sample_name)
        self.xy = xy
    

    def load_sample_grid(self, sample_name):
        self.xy.load_sample(sample_name)
        self.xy.map_points()

    @bpp.run_decorator()
    def gridScan(self, motor, posList, sample, iRange, jRange, deltaX, snake=True):
        """ Perform a grid scan according to a pre-defined sample grid
        Args:
            motor: motor to move at each new row
            posList: position list for motor. Its length must match the number of rows being scanned
            sample: sample grid name
            iRange: list of row to scan
            jRange: list of column to scan
            deltaX: horizontal offset to allow close packing
            snake: if the scan must follow a snake pattern or return to the first column at the end of each row
        """
        if len(posList) != len(iRange):
            print('number of scan steps not matching grid total row number, abort.')
        else:
            xy.load(sample)
        self.prepare_seq(0,1,0,nBuff=0)
        seq.play_mode.set(0)
        pp.flipflop()
        xy.move_to_sample(iRange[0], jRange[0])
        iRange = list(iRange)
        jRange = list(jRange)

        for ni,i in enumerate(iRange):
            motor.umv(posList[ni])
            jRange_thisRow = jRange
            for j in jRange_thisRow:
                x_pos,y_pos = xy.compute_mapped_point(i, j, sample, compute_all=False)
                if np.mod(i,2)==1:
                    x_pos = x_pos+deltaX
                yield from bps.mv(self.xy.x, x_pos, self.xy.y, y_pos)
                yield from bps.trigger_and_read([seq, self.xy.x, self.xy.y])
                while seq.play_status.get() == 2: continue
            if snake:
                jRange.reverse()

    @bpp.run_decorator()
    def gridScanDumb(self, motor, posList, sample, iRange, jRange, deltaX, snake=True):
        """ Perform a grid scan according to a pre-defined sample grid
        Args:
            motor: motor to move at each new row
            posList: position list for motor. Its length must match the number of rows being scanned
            sample: sample grid name
            iRange: list of row to scan
            jRange: list of column to scan
            deltaX: horizontal offset to allow close packing
            snake: if the scan must follow a snake pattern or return to the first column at the end of each row
        """
        if len(posList) != len(iRange):
            print('number of scan steps not matching grid total row number, abort.')
        else:
            xy.load(sample)
        self.prepare_seq(0,1,0,nBuff=0)
        seq.play_mode.set(0)
        pp.flipflop()
        xy.move_to_sample(iRange[0], jRange[0])
        iRange = list(iRange)
        jRange = list(jRange)

        for ni,i in enumerate(iRange):
            motor.umv(posList[ni])
            jRange_thisRow = jRange
            for j in jRange_thisRow:
                x_pos,y_pos = xy.compute_mapped_point(i, j, sample, compute_all=False)
                if np.mod(i,2)==1:
                    x_pos = x_pos+deltaX
                #self.xy.x.mv(x_pos)
                #self.xy.y.mv(y_pos)
                #self.xy.x.wait()
                #self.xy.y.wait()
                #seq.start()
                yield from bps.mv(self.xy.x, x_pos, self.xy.y, y_pos)
                yield from bps.trigger_and_read([seq, self.xy.x, self.xy.y])
                time.sleep(0.05)
                #while seq.play_status.get() == 2: continue
            if snake:
                jRange.reverse()

    def gridScanDumb_Daq(self, motor, posList, sample, iRange, jRange, deltaX, snake=True):
        plan = self.gridScanDumb(motor, posList, sample, iRange, jRange, deltaX, snake)
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
    
    def alignment(self):
        try:
            daq.disconnect()
        except:
            print('DAQ might already be disconnected')
        lp('OUT')
        att(1e-20)
        time.sleep(2)
        pp.open()
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(2)
        shot_sequence=[]
        shot_sequence.append([95,0,0,0])
        seq.sequence.put_seq(shot_sequence)
        time.sleep(0.5)
        seq.start()
        #daq.connect()


    def SS(self):
        pp.flipflop()
        att(1)
        self.prepare_seq(0, 1, 0, nBuff=0)
        sync_mark = int(self._sync_markers[10])
        seq2.sync_marker.put(sync_mark)
        seq2.play_mode.put(0)
        shot_sequence=[]
        shot_sequence.append([92,0,0,0])
        seq2.sequence.put_seq(shot_sequence)
        time.sleep(0.2)

    def fire(self):
        seq2.start()


    def prepare_seq(self, nShotsPre=0, nShotsOn=1, nShotsPost=0, nBuff=1):
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
        onLine = [92, 0, 0, 0]
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

    def move_SD_in(self):
        self.g1pi.umv(30)
        self.t1x.umv(-4.8)
        self.t2x.umv(4.725)
        self.d2x.umv(-22)
        self.t3x.umv(5.4141)
        self.d4x.umv(23)
        self.t6x.umv(0)
        self.d6x.umv(0)
        self.g2pi.umv(-120)
        print ("move air-bearing stage to -7 mm")

    def move_SD_out(self):
        self.g1y.umv(-6)
        self.t1x.umv(-8)
        self.t2x.umv(10)
        self.d2x.umv(20)
        self.t3x.umv(10)
        self.d4x.umv(30)
        self.t6x.umv(5)
        self.d6x.umv(0)
        self.g2y.umv(-9)
        print ("move air-bearing stage to 13 mm")


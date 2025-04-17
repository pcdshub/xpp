from subprocess import check_output

import json
import sys
import time
import os
import socket
import logging
import time

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
from xpp.db import xpp_pulsepicker as pp
from xpp.db import xpp_attenuator as att
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger
from pcdsdevices import analog_signals

from pcdsdevices.sim import FastMotor, SlowMotor


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

#        with safe_load('sam_x'):
#            self.sam_x = IMS('XPP:USR:PRT:MMS:27', name='sam_x')
    def show_CC(self):
        self.aio.ao1_0.set(5)
        self.aio.ao1_1.set(0)
    def show_VCC(self):
        self.aio.ao1_0.set(0)
        self.aio.ao1_1.set(5)
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
  
    
   # for the target positions
    samx_val = EpicsSignal('XPP:USR:PRT:MMS:03')
    samz_val = EpicsSignal('XPP:USR:PRT:MMS:27')
    samy_val = EpicsSignal('XPP:USR:PRT:MMS:28')
    zylax_val = EpicsSignal('XPP:USR:MMN:32')

    jj1hg_val = EpicsSignal('XPP:USR:MMS:35')
    jj1ho_val = EpicsSignal('XPP:USR:MMS:36')
    jj1vg_val = EpicsSignal('XPP:USR:MMS:33')
    jj1vo_val = EpicsSignal('XPP:USR:MMS:34')

    jj2hg_val = EpicsSignal('XPP:USR:PRT:MMS:31')
    jj2ho_val = EpicsSignal('XPP:USR:PRT:MMS:32')
    jj2vg_val = EpicsSignal('XPP:USR:PRT:MMS:30')
    jj2vo_val = EpicsSignal('XPP:USR:PRT:MMS:29')

    sndt2th_val = EpicsSignal('XPP:USR:MMS:25')
    sndt3th_val = EpicsSignal('XPP:USR:MMS:26')
    sndt4th_val = EpicsSignal('XPP:USR:MMS:30')
    sndt5th_val = EpicsSignal('XPP:USR:PRT:MMS:17')
	
    sample_x = IMS('XPP:USR:PRT:MMS:03', name='sample_x')
    sample_y = IMS('XPP:USR:PRT:MMS:28', name='sample_y')
    sample_z = IMS('XPP:USR:PRT:MMS:27', name='sample_z')


    def print_status(self):
        print('sam X value: {} mm'.format(self.samx_val.get()))
        print('sam Y value: {} mm'.format(self.samy_val.get()))
        print('sam Z value: {} mm'.format(self.samz_val.get()))
        print('zyla X value: {} mm'.format(self.zylax_val.get()))
        print('JJ1 hg:{} '.format(self.jj1hg_val.get()) , '  vg:{}'.format(self.jj1vg_val.get()))
        print('JJ1 ho:{} '.format(self.jj1ho_val.get()) , '  vo:{}'.format(self.jj1vo_val.get()))
        print('JJ2 hg:{} '.format(self.jj2hg_val.get()) , '  vg:{}'.format(self.jj2vg_val.get()))
        print('JJ2 ho:{} '.format(self.jj2ho_val.get()) , '  vo:{}'.format(self.jj2vo_val.get()))
        print('t2th: {}'.format(self.sndt2th_val.get()))
        print('t3th: {}'.format(self.sndt3th_val.get()))
        print('t4th: {}'.format(self.sndt4th_val.get()))
        print('t5th: {}'.format(self.sndt5th_val.get()))


    def move_sample(self):
        self.sample_x.umv(20.20)	
        self.sample_z.umv(-5.4975+0.2)	
        self.samy_val.put(1)
        print('Sample IN.')

    def move_yag(self):
        self.sample_x.umv(2.3585)
        self.sample_z.umv(-5.4975)	
        self.samy_val.put(1)
        print('YAG IN.')

    def move_silia(self):
        self.sample_x.umv(-19.5)
        self.sample_z.umv(-5.4975)	
        self.samy_val.put(1)
        print('silica IN.')

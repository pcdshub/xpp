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
from xpp.db import s4
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
        self.crl_x.umv_LX_92_clear_beam()
        self.crl_y.umv_LX_92_clear_beam()
        att(1)
        print('CRL OUT.')

    def move_focused(self):
        att(1e-6)
        self.crl_x.umv_LX_92_SD_beam()
        self.crl_y.umv_LX_92_SD_beam()
        att(0.1)
        print('CRL IN.')

    def move_silica(self):
        att(1e-6)
        self.sam_x.umv_LX92_silica() 
        att(0.1)
        print ('silica in')

    def move_zyla(self):
        att(1e-6)
        self.sam_x.umv_LX92_zyla()
        att(0.1)
        print ('zyla in, att 0.1')

    def move_sample(self):
        att(1e-6)
        self.sam_x.umv_LX92_sample()
        self.sam_y.umv_LX92_sample()
        att(1)
        print ('sample in, att 1')


    def print_JJ(self):
        print ("JJ1 {:.2f} {:.2f}".format(self.jjhg1.wm(),self.jjvg1.wm()))
        print ("JJ2 {:.2f} {:.2f}".format(self.jjhg2.wm(),self.jjvg2.wm()))
        print ("s4 {:.2f} {:.2f}".format(s4.hg.wm(),s4.vg.wm()))

    def calc_MADM(self, r1, r2, angle):
        angle_rad = np.deg2rad(angle)
        y1 = r1*np.tan(angle_rad)
        y2 = r2*np.tan(angle_rad)
        z1 = y1/np.sin(angle_rad)-r1
        z2 = y2/np.sin(angle_rad)-r2
        print ("y1: {} mm".format(y1*1e3))
        print ("y2: {} mm".format(y2*1e3))
        print ("z1: {} mm".format(z1*1e3))
        print ("z2: {} mm".format(z2*1e3))
        return 

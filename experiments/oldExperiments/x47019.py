from subprocess import check_output

import json
import sys
import time
import os
import socket
import logging

import numpy as np
import elog
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
from xpp.db import lxt_fast
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger

#os.environ['EPICS_CA_ADDR_LIST']="172.21.87.255 172.21.46.255"

#with safe_load('Create Aliases'):
from xpp.db import xpp_ccm as ccm
#    ccmE = ccm.calc.energy
#    ccmE.name = 'ccmE'
#    ccmE_vernier = ccm.calc.energy_with_vernier
#    ccmE_vernier.name = 'ccmE_vernier'


class MpodChannel(Device):
    voltage = Cpt(EpicsSignal, ':GetVoltageMeasurement', write_pv=':SetVoltage', kind='normal')
    current = Cpt(EpicsSignalRO, ':GetCurrentMeasurement', kind='normal')
    state = Cpt(EpicsSignal, ':GetSwitch', write_pv=':SetSwitch', kind='normal')
    # 0 means no EPICS high limit.
    voltage_highlimit = Cpt(EpicsSignal, ':SetVoltage.DRVH', kind='normal')


class User():
    def __init__(self):
        self.t0 = 894756
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

        #########################################################################
        #            Add the axes
        #########################################################################

        # with safe_load('zyla0'):
        #    self.zyla0_y = IMS('XPP:USR:PRT:MMS:18', name='zyla0_y')
        #    self.zyla0_x = Newport('XPP:USR:PRT:MMN:07', name='zyla0_x')
        with safe_load('epix'):
            self.epix_x = Newport('XPP:USR:PRT:MMN:06', name='epix_x')
            self.epix_y = Newport('XPP:USR:PRT:MMN:07', name='epix_y')
        with safe_load('opa'):
            self.opa_pol = Newport('XPP:USR:MMN:32', name='opa_pol')
            #self.EOS_wp = Newport('XPP:USR:MMN:04', name='EOS_wp')
            #self.THz_pol = Newport('XPP:USR:MMN:06', name='THz_pol')
            #self.wp_1 = Newport('XPP:USR:MMN:02', name='wp_1')
        with safe_load('LIB'):
            self.lib_diag = IMS('XPP:USR:MMS:32', name='lib_diag')
        # with safe_load('Triggers'):
        #    self.evr_R30E26 = Trigger('XPP:R30:EVR:26:TRIGB', name='evr_R30E26')
        #    self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
        #    self.evr_R30E26_ticks = EpicsSignal('XPP:R30:EVR:26:CTRL.DGBD', name='evr_R30E26_ticks')
        #    self.evr_R30E28_ticks = EpicsSignal('XPP:R30:EVR:28:CTRL.DGBD', name='evr_R30E28_ticks')
        #    self.GD = self.evr_R30E28.ns_delay

#        with safe_load('MPOD'):
#            self.diode_bias = MpodChannel('XPP:R39:MPD:CH:100', name='diode_bias')

        with safe_load('Liquid Jet'):
            from pcdsdevices.jet import BeckhoffJet
            self.ljh = BeckhoffJet('XCS:LJH', name='ljh')

        with safe_load('Polycapillary System'):
            from pcdsdevices.epics_motor import EpicsMotorInterface
            from ophyd.device import Device, Component as Cpt 
            from ophyd.signal import Signal

            class MMC(EpicsMotorInterface):
                direction_of_travel = Cpt(Signal, kind='omitted')
            class Polycap(Device):
                m1 = Cpt(MMC, ':MOTOR1', name='motor1')    
                m2 = Cpt(MMC, ':MOTOR2', name='motor2')
                m3 = Cpt(MMC, ':MOTOR3', name='motor3')
                m4 = Cpt(MMC, ':MOTOR4', name='motor4')
                m5 = Cpt(MMC, ':MOTOR5', name='motor5')
                m6 = Cpt(MMC, ':MOTOR6', name='motor6')
                m7 = Cpt(MMC, ':MOTOR7', name='motor7')
                m8 = Cpt(MMC, ':MOTOR8', name='motor8')
            self.polycap = Polycap('BL152:MC1', name='polycapillary')



    ###############################################################################################
    #                   Functions from default files
    ###############################################################################################

    #preset both lxt_fast stage position and encoder to 0
    def lxt_fast_set_absolute_zero(self):
        currentpos = lxt_fast()
        currentenc = lxt_fast_enc.get()
        elog.post('Set current stage position {}, encoder value {} to 0'.format(currentpos,currentenc.pos))
        print('Set current stage position {}, encoder value {} to 0'.format(currentpos,currentenc.pos))
        lxt_fast.set_current_position(0)
        lxt_fast_enc.set_zero()
        return

    def takeRun(self, nEvents, record=None):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()
        return

    # dscan & ascan kludge for x421 evr delay scan, as the evr object does not have the wm and mv attributes
    def continuous_gscan(self,energies,pointTime=1):
    #Set to go up an down once.
        initial_energy=ccm.E_Vernier.position
        try:
            for E in energies:
                ccm.E_Vernier.mv(E)
                time.sleep(pointTime)
            for E in energies[::-1]:
                ccm.E_Vernier.mv(E)
                time.sleep(pointTime) 
            print('Up and down ccm scan complete. Returning ccm to energy before scan: '+str(initial_energy))
            ccm.E_Vernier.mv(initial_energy) 
        except KeyboardInterrupt:
            print('Scan end signal received. Returning ccm to energy before scan: '+ str(initial_energy))
            ccm.E_Vernier.mv(initial_energy)

    def daq_continuous_gscan(self,energies,pointTime=1,numberOfScans=None):
        '''
        Parameters:energy array, time per energy point, number of scans    
        Moves the CCM and Vernier through the energy array and saves the data after a forward and backwards sweep.
        Number of scans is optional. If not given then function will continuously loop. Starting a new run after each sweep.
        '''
        try:
            if numberOfScans==None:
                while 1==1:
                    daq.disconnect()
                    daq.configure()
                    daq.begin(record=True)
                    self.continuous_gscan(energies,pointTime)
                    daq.end_run()
            else:
                for i in range(numberOfScans):
                    daq.disconnect()
                    daq.configure()
                    daq.begin(record=True)
                    self.continuous_gscan(energies,pointTime)
                    daq.end_run()
            daq.disconnect()
        except KeyboardInterrupt:
            print('Scan end signal received. Disconnecting from the  DAQ.')
            daq.disconnect()

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

    def ascan_wimagerh5(self, imagerh5, motor, start, end, nsteps, nEvents, record=None):
        plan_duration = nsteps * nEvents / 120. + 0.3 * (nsteps - 1) + 4
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        # we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)
        imagerh5.write_wait()

    def ascan_wimagerh5_slow(self, imagerh5, motor, start, end, nsteps, nEvents, record=None):
        plan_duration = (nsteps * nEvents / 120. + 0.3 * (nsteps - 1) + 4) * 10
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        # we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)

        imagerh5.write_stop()

    def set_current_position(self, motor, value):
        motor.set_use_switch.put(1)
        motor.set_use_switch.wait_for_connection()
        motor.user_setpoint.put(value, force=True)
        motor.user_setpoint.wait_for_connection()
        motor.set_use_switch.put(0)

    def empty_delay_scan(self, start, end, sweep_time, record=None,
                         use_l3t=False, duration=None):
        """Delay scan without the daq."""
        self.cleanup_RE()
        #daq.configure(events=None, duration=None, record=record,
        #              use_l3t=use_l3t, controls=[lxt_fast])
        try:
            RE(delay_scan([], lxt_fast, [start, end], sweep_time,
                          duration=duration))
        except Exception:
            #logger.debug('RE Exit', exc_info=True)

            print("sorry")
        finally:
            self.cleanup_RE()
        return

#    def cleanup_RE(self):
#        if not RE.state.is_idle:
#            print('Cleaning up RunEngine')
#            print('Stopping previous run')
#            try:
#                RE.stop()

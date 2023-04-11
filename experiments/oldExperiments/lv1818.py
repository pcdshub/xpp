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
from bluesky.plans import list_grid_scan, scan_nd
from bluesky.plan_stubs import one_nd_step, trigger
from pcdsdaq.preprocessors import daq_during_decorator
from ophyd import Component as Cpt
from ophyd import Device
from pcdsdevices.interface import BaseInterface
from pcdsdevices.areadetector import plugins
from xpp.db import daq, seq
from xpp.db import camviewer
from xpp.db import RE
from xpp.db import at2l0
from xpp.db import pp
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger
from xpp.plans import serp_seq_scan
from cycler import cycler

import sys
#sys.path.append('/reg/g/pcds/pyps/apps/hutch-python/xpp/experiments/')

#import aerotech

try:
    from xpp.db import sam_x, sam_y
except:
    print('Failed to load sam_x, sam_y: possibly due to the questionnaire loading failing.')
from xpp.db import seq_laser

@daq_during_decorator()
def serp_seq_scan_3axis(shift_motor1, shift_pts1, shift_motor2, shift_pts2, shift_motor3, shift_pts3, fly_motor, fly_pts, seq):
    """
    Serpentine scan that triggers the event sequencer on every row.

    Parameters
    ----------
    shift_motor: Positioner
        The column axis to shift to the next fly scan row

    shift_pts:  list of floats
        The positions of the rows to scan down, e.g. [0, 1, 2, 3 ...],
        np.arange(0, 100, 1000), etc.

    fly_motor: Positioner
        The row axis to do fly collection on

    fly_pts: list of 2 floats
        The positions to fly between, e.g. [0, 100]

    seq: Sequencer
        The sequencer to start on each row.
    """
    if len(fly_pts) != 2:
        raise ValueError('Expected fly_pts to have exactly 2 points!')

    is_seq_step = False

    def per_step(detectors, step, pos_cache):
        """
        Override default per_step to start the sequencer on each row.

        The first move is not a fly scan move: it moves us into the start
        position. The second move is, as is the fourth, sixth...
        """
        nonlocal is_seq_step
        if is_seq_step:
            yield from trigger(seq)
            is_seq_step = False
        else:
            is_seq_step = True
        yield from one_nd_step(detectors, step, pos_cache)

    return (yield from list_grid_scan([],
                                      shift_motor1, shift_pts1,
                                      shift_motor2, shift_pts2,
                                      shift_motor3, shift_pts3,
                                      fly_motor, fly_pts,
                                      snake_axes=[fly_motor],
                                      per_step=per_step))

@daq_during_decorator()
def serp_seq_scan_nd(shift_motor1, shift_pts1, shift_motor2, shift_pts2, shift_motor3, shift_pts3, fly_motor, fly_pts, seq):
    """
    Serpentine scan that triggers the event sequencer on every row.

    Parameters
    ----------
    shift_motor: Positioner
        The column axis to shift to the next fly scan row

    shift_pts:  list of floats
        The positions of the rows to scan down, e.g. [0, 1, 2, 3 ...],
        np.arange(0, 100, 1000), etc.

    fly_motor: Positioner
        The row axis to do fly collection on

    fly_pts: list of 2 floats
        The positions to fly between, e.g. [0, 100]

    seq: Sequencer
        The sequencer to start on each row.
    """
    if len(fly_pts) != 2:
        raise ValueError('Expected fly_pts to have exactly 2 points!')

    is_seq_step = False

    def per_step(detectors, step, pos_cache):
        """
        Override default per_step to start the sequencer on each row.

        The first move is not a fly scan move: it moves us into the start
        position. The second move is, as is the fourth, sixth...
        """
        nonlocal is_seq_step
        if is_seq_step:
            yield from trigger(seq)
            is_seq_step = False
        else:
            is_seq_step = True

        yield from one_nd_step(detectors, step, pos_cache)

   
    traj1 = cycler(shift_motor1, shift_pts1)
    traj2 = cycler(shift_motor2, shift_pts2)
    traj3 = cycler(shift_motor3, shift_pts3)
    traj4 = cycler(fly_motor, fly_pts)

    full_cycler = (traj1 + traj2 + traj3) * traj4

    #return (yield from list_grid_scan([],
    #                                  shift_motor1, shift_pts1,
    #                                  shift_motor2, shift_pts2,
    #                                  shift_motor3, shift_pts3,
    #                                  fly_motor, fly_pts,
    #                                  snake_axes=[fly_motor],
    #                                  per_step=per_step))

    return (yield from scan_nd([], full_cycler, per_step=per_step))


@daq_during_decorator()
def serp_seq_scan_nd2(shift_motor1, shift_pts1, shift_motor2, shift_pts2, shift_motor3, shift_pts3, fly_motor, fly_pts, seq):
    """
    Serpentine scan that triggers the event sequencer on every row.

    Parameters
    ----------
    shift_motor: Positioner
        The column axis to shift to the next fly scan row

    shift_pts:  list of floats
        The positions of the rows to scan down, e.g. [0, 1, 2, 3 ...],
        np.arange(0, 100, 1000), etc.

    fly_motor: Positioner
        The row axis to do fly collection on

    fly_pts: list of 2 floats
        The positions to fly between, e.g. [0, 100]

    seq: Sequencer
        The sequencer to start on each row.
    """
    if len(fly_pts) != 2:
        raise ValueError('Expected fly_pts to have exactly 2 points!')

    is_seq_step = False

    def per_step(detectors, step, pos_cache):
        """
        Override default per_step to start the sequencer on each row.

        The first move is not a fly scan move: it moves us into the start
        position. The second move is, as is the fourth, sixth...
        """
        nonlocal is_seq_step
        
        if is_seq_step:
            yield from trigger(seq)
            is_seq_step = False
        else:
            is_seq_step = True

        yield from one_nd_step(detectors, step, pos_cache)

    # number of rows
    N = np.size(shift_pts1)

    # we need to repeat by a factor of 2 because we need the endpoints of each row to be the same for
    # all motors except for the "fly" motor
    traj1 = cycler(shift_motor1, np.repeat(shift_pts1,2))
    traj2 = cycler(shift_motor2, np.repeat(shift_pts2,2))
    traj3 = cycler(shift_motor3, np.repeat(shift_pts3,2))

    # first flip and append the fly endpoints so that the scan goes back and forth, then
    # tile to account for all the rows
    fly_pts = np.array(fly_pts)
    fly_pts = np.append(fly_pts, np.flip(fly_pts))
    fly_pts = np.tile(fly_pts, int(N/2))

    # if the number of steps wasn't even, we might need to subtract off a row
    if np.size(fly_pts)<np.size(np.repeat(shift_pts1,2)):
        fly_pts = fly_pts[:-2]

    traj4 = cycler(fly_motor, fly_pts)

    full_cycler = (traj1 + traj2 + traj3 + traj4)

    #return (yield from list_grid_scan([],
    #                                  shift_motor1, shift_pts1,
    #                                  shift_motor2, shift_pts2,
    #                                  shift_motor3, shift_pts3,
    #                                  fly_motor, fly_pts,
    #                                  snake_axes=[fly_motor],
    #                                  per_step=per_step))

    return (yield from scan_nd([], full_cycler, per_step=per_step))



class User():
    def __init__(self):
        self.t0 = 894756

        # set reference energy
        self.ref_energy = 8.98
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
        #with safe_load('crl2_xytheta'):
        #    self.crl2_x = IMS('XPP:USR:PRT:MMS:20', name='crl2_x')
        #    self.crl2_y = IMS('XPP:USR:PRT:MMS:22', name='crl2_y')
        #    self.crl2_z = IMS('XPP:USR:PRT:MMS:23', name='crl2_z')
        #    self.crl2_th_x = Newport('XPP:USR:MMN:05', name='crl2_th_x')
        #    self.crl2_th_y = Newport('XPP:USR:MMN:04', name='crl2_th_y')

        #########################################################################
        #            Add the axes
        #########################################################################
        #with safe_load("grating_1"):
        #    pass

        #with safe_load("CC1"):
        #    self.t1_x = IMS('XPP:USR:MMS:18', name='t1_x')
        #    self.t1_y = IMS('XPP:USR:MMS:22', name='t1_y')
        #    self.t1_th = IMS('XPP:USR:MMS:29', name='t1_th')

        #with safe_load("CC2"):
        #    self.t2_th = IMS('XPP:USR:MMS:23', name='t2_th')

        #with safe_load("CC3"):
        #    self.t3_th = IMS('XPP:USR:MMS:32', name='t3_th')

        #with safe_load("CC4"):
        #    self.t4_x = IMS('XPP:USR:MMS:25', name='t4_x')
        #    self.t4_th = IMS('XPP:USR:MMS:30', name='t4_th')

        #with safe_load("CC5"):
        #    self.t5_x = IMS('XPP:USR:MMS:21', name='t5_x')
        #    self.t5_th = IMS('XPP:USR:PRT:MMS:25', name='t5_th')

        #with safe_load("CC6"):
        #    self.t6_x = IMS('XPP:USR:PRT:MMS:24', name='t6_x')
        #    self.t6_y = IMS('XPP:USR:PRT:MMS:29', name='t6_y')
        #    self.t6_th = IMS('XPP:USR:PRT:MMS:21', name='t6_th')

        #with safe_load("Diagnosis"):
        #    self.d1_x = IMS('XPP:USR:MMS:17', name='d1_x')
        #    self.d2_x = IMS('XPP:USR:MMS:24', name='d2_x')
        #    self.d3_x = IMS('XPP:USR:MMS:31', name='d3_x')
        #    self.d4_x = IMS('XPP:USR:MMS:26', name='d4_x')
        #    self.d5_x = IMS('XPP:USR:PRT:MMS:32', name='d5_x')
        #    self.yag_x = IMS('XPP:USR:PRT:MMS:19', name='yag_x')

        # with safe_load('zyla0'):
        #    self.zyla0_y = IMS('XPP:USR:PRT:MMS:18', name='zyla0_y')
        #    self.zyla0_x = Newport('XPP:USR:PRT:MMN:07', name='zyla0_x')
        # with safe_load('Triggers'):
        #    self.evr_R30E26 = Trigger('XPP:R30:EVR:26:TRIGB', name='evr_R30E26')
        #    self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
        #    self.evr_R30E26_ticks = EpicsSignal('XPP:R30:EVR:26:CTRL.DGBD', name='evr_R30E26_ticks')
        #    self.evr_R30E28_ticks = EpicsSignal('XPP:R30:EVR:28:CTRL.DGBD', name='evr_R30E28_ticks')
        #    self.GD = self.evr_R30E28.ns_delay

        with safe_load('trigger'):
            self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
            #self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp')
            self.evr_pp = Trigger('XPP:R30:EVR:26:TRIG3', name='evr_pp_temp')
            self.delay = self.evr_R30E28.ns_delay

        #############################################
        #         Haoyuan: Load the aerotech stage
        #############################################
        #try:
        #    self.airbearing = aerotech.Ensemble()
        #except ConnectionError:
        #    print("Failed to connect the aerotech airbearing stage.")

    ##############################################
    #  Haoyuan: Functions for delay scan
    ##############################################
    #def constant_delay_scan(self, start, end, speed):
    #    self.airbearing.constant_delay_scan(start=start, end=end, speed=speed)
    #
    #def abmv(self, x_pos, speed):
    #    """
    #    Move the air-bearing stage to the absolute position
    #    :return:
    #    """
    #    self.airbearing.move(x_pos=x_pos, x_speed=speed)

    #def abmvr(self, displacement, speed):
    #    """
    #    Move the air-bearing with respect to its current position
    #    :return:
    #    """
    #    self.airbearing.linear(displace=displacement, speed=speed)

    #def abhome(self, ):
    #    """
    #    Move the air-bearing stage to the absolute position
    #    :return:
    #    """
    #    self.airbearing.home()

    #def ab_enable(self, ):
    #    """
    #    Move the air-bearing stage to the absolute position
    #    :return:
    #    """
    #    self.airbearing.enable()

    #def ab_disable(self, ):
    #    """
    #    Move the air-bearing stage to the absolute position
    #    :return:
    #    """
    #    self.airbearing.disable()
    
    #def ab_clear_error(self):
    #    """
    #    Try to clear all errors with the aerotech stage
    #    :return:
    #    """
    #    self.airbearing.clear_error()

    #def ab_reconnect(self):
    #    """
    #    Try to re-establish the connection
    #    :return:
    #    """
    #    self.airbearing.connect()

    #def ab_run(self, command):
    #    """
    #    Run a commandline with the ascii interface

    #    :param command:
    #    :return:
    #    """
    #    self.airbearing.run(command=command)



    ##############################################
    #  Haoyuan: Functions for Energy Scan
    ##############################################
    #def escan(self, delta_theta):
    #    """
    #    Change the angle of t1 and t6 in the same time to
    #    :param delta_theta:
    #    :return:
    #    """
    #    pass
    
    ###############################################
    #     Haoyuan: Bragg angle for silicon 220
    ###############################################

    def set_reference_energy(self, energy_kev):

        self.ref_energy = energy_kev

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

    def set_pp_burst(self):
        burstdelay=4.5e-3*1e9
        flipflopdelay=8e-3*1e9
        followerdelay=3.8e-5*1e9
        self.evr_pp.ns_delay.set(burstdelay)
        pp.burst(wait=True)

    def setupSequencer(self, flymotor, distance, freq_shots=120, pp_shot_delay=2):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        #sync_mark = int(self._sync_markers[120])
        sync_mark = 6
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
    
        #calculate how often to shoot in requested distance
        flyspeed = flymotor.velocity.get()
        print(flyspeed)
        flytime = distance/flyspeed
        flyshots = int(flytime*freq_shots)
        print(flyshots)

        # Determine the different sequences needed
        deltaShot = int(min((1024-2),int(120/freq_shots)))

        fly_seq = [[95, 0, 0, 0]]
        for i in range(10):
            fly_seq.append([95, deltaShot, 0, 0])
        #fly_seq = [[94, 0, 0, 0]]
        fly_seq.append([94, 0, 0, 0])
        fly_seq.append([95, pp_shot_delay, 0, 0])
        for i in range(flyshots-50):
            fly_seq.append([95, deltaShot, 0, 0])
        fly_seq.append([94, 0, 0, 0])
        fly_seq.append([95, deltaShot, 0, 0])
        #logging.debug("Sequence: {}".format(fly_seq))                  
        

        seq.sequence.put_seq(fly_seq) 

    def run_energy_and_serp_scan(self, energyStart, energyStop, energySteps, shiftStart, shiftStop, shiftSteps, flyStart, flyStop, freq_shots=120, record=None, pp_shot_delay=2):
        """
        :param energyStart: float
            starting photon energy (keV)
        :param energyStop: float
            ending photon energy (keV)
        :param energySteps: int
            number of steps for the photon energy
        :param shiftStart: float
            starting point for the "shifting" motor
        :param shiftStop: float
            ending point for the "shifting" motor
        :param shiftSteps: int or float
            number of fly scan rows or step size between rows
        :param flyStart: float
            starting position for the "fly" motor
        :param flyStop: float
            ending position for the "fly" motor
        :param freq_shots: int
            rep rate of X-rays, default is 120 Hz
        :param record: bool or None
            whether to record with the DAQ. This might not work, set in GUI
        :param pp_shot_delay: int
            number of shots to wait for the pulse picker to open
        """
        daq.disconnect() #make sure we start from fresh point.
        
        shiftMotor=self.sam_y
        flyMotor=self.sam_x
        self.setupSequencer(flyMotor, abs(flyStop-flyStart), freq_shots, pp_shot_delay=pp_shot_delay)
        daq.configure(-1, record=record, controls=[sam_x, sam_y])
        #daq.begin(-1)

        # get angle of starting energy
        angle_1 = self.si220bragg(energyStart)
        # get angle of final energy
        angle_2 = self.si220bragg(energyStop)

        energyMotor1 = self.t1_th
        energyMotor2 = self.t6_th

         

        # calculate number of rows per energy step
        rowsPerEnergy = int(shiftSteps/energySteps)
        # recalculate number of shift steps
        shiftSteps = energySteps*rowsPerEnergy

        # get angles for energy scan
        energySteps1 = np.repeat(np.linspace(angle_1, angle_2, energySteps),rowsPerEnergy)


        if isinstance(shiftSteps, int):
            RE(serp_seq_scan_nd2(shiftMotor, np.linspace(shiftStart, shiftStop, shiftSteps), energyMotor1, energySteps1, energyMotor2, energySteps1, flyMotor, [flyStart, flyStop], seq))
        else:
            RE(serp_seq_scan_nd2(shiftMotor, np.arange(shiftStart, shiftStop, shiftSteps), energyMotor1, energySteps1, energyMotor2, energySteps1, flyMotor, [flyStart, flyStop], seq))

         


    def run_serp_seq_scan(self, shiftStart, shiftStop, shiftSteps, flyStart, flyStop, freq_shots=120, record=None, pp_shot_delay=2):
        daq.disconnect() #make sure we start from fresh point.
        shiftMotor=self.sam_y
        flyMotor=self.sam_x
        self.setupSequencer(flyMotor, abs(flyStop-flyStart), freq_shots, pp_shot_delay=pp_shot_delay)
        daq.configure(-1, record=record, controls=[sam_x, sam_y])
        #daq.begin(-1)
            
        if isinstance(shiftSteps, int):
             RE(serp_seq_scan(shiftMotor, np.linspace(shiftStart, shiftStop, shiftSteps), flyMotor, [flyStart, flyStop], seq))
        else:
             RE(serp_seq_scan(shiftMotor, np.arange(shiftStart, shiftStop, shiftSteps), flyMotor, [flyStart, flyStop], seq))

        #daq.end()



    def sequenceTest(self, nEvts, nWait=120, nSwitch=60, waitAfter=True):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        #sync_mark = int(self._sync_markers[120])
        sync_mark = 6
        seq_laser.sync_marker.put(sync_mark)
        seq_laser.play_mode.put(2) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
    
        #nSwitch=60
        
        fly_seq = [[96, 0, 0, 0]]
        if waitAfter:
            fly_seq = [[96, nWait, 0, 0]]
            nWait=1
        for i in range(min(nEvts,nSwitch-1)):
            fly_seq.append([97, 1, 0, 0])
        if nEvts>nSwitch:
            for i in range(nEvts-nSwitch):
                fly_seq.append([98, 1, 0, 0])
        fly_seq.append([93, nWait, 0, 0])

        seq_laser.sequence.put_seq(fly_seq) 

    def set_current_position(self, motor, value):
        motor.set_use_switch.put(1)
        motor.set_use_switch.wait_for_connection()
        motor.user_setpoint.put(value, force=True)
        motor.user_setpoint.wait_for_connection()
        motor.set_use_switch.put(0)



"""
Contains function definitions for managing the timetool and ultrafast timing
during experiments.

Functions
----------
correct_timing_drift(amplitude_thresh: float, ipm_thresh: float,
                     drift_adjustment_thresh: float, fwhm_threshs: Tuple,
                     num_events: int, will_log: bool)
    Automate the correction of long-term drift in timing by monitoring the mean
    edge position on the timetool camera.
"""

__all__ = ["correct_timing_drift"]

import logging
import time
from typing import Tuple
from enum import IntEnum

import numpy as np
from ophyd.signal import EpicsSignal

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

from pcdsdevices.lxe import LaserTiming
from pcdsdevices.epics_motor import DelayNewport
from xpp.db import xpp_txt

ebuild_pv = "XPP:TT:01:EVENTBUILD.VALA"
drift_corr_pv = "LAS:FS11:VIT:DRIFT_CORRECT_VAL"  # bay1
#drift_corr_pv = "LAS:FS11:VIT:DRIFT_CORRECT_VAL"  # bay4
drift_enable_pv = "LAS:FS11:VIT:TT_DRIFT_ENABLE"

lxt_FS11 = LaserTiming('LAS:FS11', name='lxt')
lxt_FS14 = LaserTiming('LAS:FS14', name='lxt')
lxt = lxt_FS11

txt = DelayNewport('XPP:LAS:MMN:16', name='txt', n_bounces=14)

class EBUILD_XPP(IntEnum):
    I0 = 1  # ipm2
    TT_POS_PX = 14
    TT_POS_PS = 15
    TT_AMPL = 16
    TT_AMPL_2 = 17
    TT_FWHM = 19
    TT_INTG = 20

class EBUILD_XPP_NO_BLD(IntEnum):
    I0 = 1  # ipm2
    TT_POS_PX = 14
    TT_POS_PS = 15
    TT_AMPL = 16
    TT_AMPL_2 = 17
    TT_FWHM = 19
    TT_INTG = 20



EBUILD = EBUILD_XPP



def is_good_data(
    tt_data: np.ndarray,
    amplitude_threshs: Tuple[float, float],
    amplitude2_thresh: float,
    fwhm_threshs: Tuple[float, float],
    i0_thresh: float,
    print_info=False
) -> bool:
    """
    Determine whether a specific detected edge on the timetool camera is "good"

    Good/bad is defined by whether the timetool data shows the detected edge
    has a reasonable amplitude and a FWHM that falls within a specified range.
    A minimum X-ray intensity, as measured at IPM DG2, is also required for us
    to accept a measurement as accurate.

    Parameters
    ----------
    tt_data : np.ndarray
        Data read from the new timetool/EBUILD IOC which includes the TTALL
        data as well as ipm readings.
    amplitude_thresh : float
        Minimum amplitude extracted from timetool camera processing for the
        measurement to be considered "good."
    i0 : float
        Minimum reading at the i0 monitor to be considered 'Good".
    fwhm_threshs : Tuple[float, float]
        Minimum and maximum FWHM from the processed timetool signal to consider
        a measurement to be "good."
    """
    tt_pos_ps: float = tt_data[EBUILD.TT_POS_PS]
    tt_ampl: float = tt_data[EBUILD.TT_AMPL]
    tt_ampl_2: float = tt_data[EBUILD.TT_AMPL_2]
    tt_fwhm: float = tt_data[EBUILD.TT_FWHM]
    i0: float = tt_data[EBUILD.I0]

    if print_info:
        s = "tt_value: %0.3f" %tt_pos_ps
        s += "   ttamp: %0.3f " %tt_ampl
        s += "   tt_amp2: %d" %tt_ampl_2
        s += "   tt_fwhm: %d" %tt_fwhm
        s += "   i0: %d\n" %i0
        print(s)

    if i0 < i0_thresh:
        return False
    elif tt_ampl < amplitude_threshs[0] or tt_ampl > amplitude_threshs[1]:
        return False
    elif tt_fwhm < fwhm_threshs[0] or tt_fwhm > fwhm_threshs[1]:
        return False
    elif tt_ampl_2 < amplitude2_thresh:#for now commented out since not essential
        return False
    elif txt.moving:
        return False
    return True


def correct_timing_drift(
    tt_amplitude_threshs: Tuple[float, float] = (0.02, 0.07),
    tt_amplitude2_thresh: float = 2000,
    tt_fwhm_threshs: Tuple[float, float] = (100, 350),
    i0_thresh: float = 0.0,
    #drift_adjustment_thresh: float = 0.05,
    num_events: int = 121,
    kp: float = 0.2,
    ki: float = 0.1,
    kd: float = 1,
    will_log: bool = False,
) -> None:
    """
    Automate the correction of timing drift. Will adjust the stages to
    center the timetool edge on the camera and compensate the laser delay to
    maintain the desired nominal time point. Runs in an infinite loop.

    Parameters
    ----------
    tt_amplitude_thresh : float, optional
        The minimum amplitude of the fitted timetool peak to include the
        data point in the rolling average used for drift correction.
        Default: 0.02.
    tt_fwhm_threshs : Tuple[float, float], optional
        Minimum and maximum FWHM from the processed timetool signal to consider
        a measurement to be "good."
    ipm_thresh : float, optional
        The minimum ipm DG2 value to perform drift correction. Setting a
        reasonable value prevents attempts at drift correction when X-rays
        are very weak or down. Default: 500.
    num_events : int, optional
        The number of "good" timetool edge measurements to include in the
        rolling average. Ideally a prime number to remove effects from
        sytematic errors. Default 61 measurements.
    will_log : bool, optional
        Log timing corrections to a file.
    """

    logfile: str = ""
    if will_log:
        logfile = input("Please enter a file to log correction info to: ")


    write_log(f"Entering timetool drift correction loop", logfile)

    sig_evt_build: EpicsSignal = EpicsSignal(ebuild_pv)
    sig_drift_correction = EpicsSignal(drift_corr_pv)
    sig_drift_enable = EpicsSignal(drift_enable_pv)

    while not sig_drift_enable.get():
        print('\033[1;31m' +  "Please Turn On -----FS Timing Correction-----" + '\033[0m')
        time.sleep(2)

    while True:
        num_curr_edges: int = 0
        iteration : int = 0
        time_last_good_val: float = time.time()
        fake_time = 0
        timetool_edges: np.ndarray = np.zeros([num_events])
        ave_tt = np.zeros([2,])
        previous_evt_build_data = np.zeros(sig_evt_build.get().shape)

        while num_curr_edges < num_events:
            try:
                iteration += 1
                evt_build_data: np.ndarray = sig_evt_build.get()
                if evt_build_data[-2] == previous_evt_build_data[-2]:
                    time.sleep(0.1)
                    continue
                previous_evt_build_data = evt_build_data

                timetool_edge_ps: float = evt_build_data[EBUILD.TT_POS_PS]

                if iteration % 120 == 0:
                    is_good_data(
                        evt_build_data,
                        tt_amplitude_threshs,
                        tt_amplitude2_thresh,
                        tt_fwhm_threshs,
                        i0_thresh,
                        print_info=True
                    )

                # Check is_good_measurement function for configuring / adding
                # new thresholds.
                if is_good_data(
                    evt_build_data,
                    tt_amplitude_threshs,
                    tt_amplitude2_thresh,
                    tt_fwhm_threshs,
                    i0_thresh,
                ):
                    timetool_edges[num_curr_edges] = timetool_edge_ps
                    num_curr_edges += 1
                    time_last_good_val = time.time()

                elif time.time() - time_last_good_val > 60:
                    write_log(
                        f"No good measurement over one minute. Check thresholds?",
                        logfile,
                    )
                    time_last_good_val = time.time()

                fake_time += 1
                time.sleep(0.01)
            except KeyboardInterrupt as e:
                raise KeyboardInterrupt

        timetool_edges = np.delete(timetool_edges, 0)
        ave_tt[1] = ave_tt[0]
        ave_tt[0] = np.mean(timetool_edges)
        print("Moving average of timetool value:", ave_tt)
        fbk_val = pid_control(kp, ki, kd, ave_tt, fake_time)#on Sep.14. fixed typo

        if (round(lxt(), 13) == -round(txt(), 13)) and not txt.moving:
            # Check that we are not moving lxt_ttc and that we are in the
            # the correct lxt = -txt condition for lxt_ttc to work.
            fbk_val_seconds = -fbk_val * 1e-12
            apply_correction(sig_drift_correction, fbk_val_seconds)


def pid_control(kp, ki, kd, ave_data, faketime):
    prop = kp * ave_data[0,]
    integral = ki * (np.sum(ave_data[:,]))
    differential = kd * ((ave_data[1,] - ave_data[0,]) / faketime)
    fd_value = prop + integral + differential
    return fd_value


def apply_correction(sig_correction, fbk_val_seconds):
    start_val = sig_correction.get()
    fbk_val_ns = fbk_val_seconds * 1e+9##switched the sign from - to + on Sep.14
    print(f"Correction: {fbk_val_ns} ns.")
    sig_correction.put(start_val + fbk_val_ns)
    return


def write_log(msg: str, logfile: str = "") -> None:
    """
    Log messages both via the standard logger and optionally to a file.

    All messages will be timestamped.

    Parameters
    ----------
    msg : str
        Message to log. A timestamp will be prepended to the beginning of the
        message - do NOT include one.
    logfile : str, optional
        A logfile to also write the message to. Will append if the logfile
        already exists. If the empty string is passed, no logfile is written
        to. Default: "", i.e. do not write to a logfile.
    """
    timestamped_msg: str = f"[{time.ctime()}] {msg}"
    logger.info(timestamped_msg)

    if logfile:
        with open(logfile, "a") as f:
            f.write(timestamped_msg)

















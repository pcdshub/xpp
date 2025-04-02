import os
import time
import os.path
import logging
import subprocess

import numpy as np
from ophyd import EpicsSignalRO
from bluesky import RunEngine
from hutch_python.utils import safe_load
from bluesky.plans import scan
from bluesky.plans import list_scan
from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal
from pcdsdevices.interface import BaseInterface
from xpp.db import daq, seq, elog
from ophyd.status import wait as status_wait
from pcdsdevices.evr import Trigger
from xpp.db import cp
from xpp.db import lp
from xpp.db import xpp_pulsepicker as pp
from xpp.db import xpp_ccm as ccm
from pcdsdevices.device_types import Newport, IMS
# WAIT A WHILE FOR THE DAQ TO START
import pcdsdaq.daq
pcdsdaq.daq.BEGIN_TIMEOUT = 5

#########
# TODO  #
#########

logger = logging.getLogger(__name__)


#######################
#  Object Declaration #
#######################
# Declare shutter 

# Trigger objects - created from questionnaire

# Laser parameter

# event code

#####
# XPP event code
#####
# 94 PP      (MFX: 197)
# 95 DAQ     (MFX: 198)
# 190 WATER
# 191 SAMPLE 



class User:
    """Generic User Object"""
    with safe_load('Dummy'):
        print('Import dummy')



    ######################
    # Scanning Functions #
    ######################
    def perform_run(self, events, record=True, comment='', post=True,
                    **kwargs):
        """
        Perform a single run of the experiment

        Parameters
        ----------
        events: int
            Number of events to include in run

        record: bool, optional
            Whether to record the run

        comment : str, optional
            Comment for ELog

        post: bool, optional
            Whether to post to the experimental ELog or not. Will not post if
            not recording

        Note
        ----
        """

        comment = comment or ''
        # Start recording
        logger.info("Starting DAQ run, -> record=%s", record)
        daq.begin(events=events, record=record)
        time.sleep(1)
        # Post to ELog if desired
        runnum = daq._control.runnumber()
        info = [runnum, comment, events, self._delaystr]
        post_msg = post_template.format(*info)
        print(post_msg)
        if post and record:
            elog(msg=post_msg, run=runnum)

        # Wait for the DAQ to finish
        logger.info("Waiting or DAQ to complete %s events ...", events)
        daq.wait()
        logger.info("Run complete!")
        daq.end_run()
        time.sleep(0.5)
        return


    def continuous_ccmscan(self,energies, pointTime=1, move_vernier=True, bidirectional=False, kill=True):
        #Set to go up an down once.
        initial_energy=ccm.E_Vernier.position
        try:
            for E in energies:
                if move_vernier:
                    ccm.E_Vernier.move(E, kill=kill)
                else:
                    ccm.E.move(E, kill=kill)
                time.sleep(pointTime)
            if bidirectional:
                for E in energies[::-1]:
                    if move_vernier:
                        ccm.E_Vernier.move(E, kill=kill)
                    else:
                        ccm.E.move(E, kill=kill)
                    time.sleep(pointTime)
        except KeyboardInterrupt:
                print(f'Scan end signal received. Returning ccm to energy before scan: {initial_energy}')
                ccm.E_Vernier.move(initial_energy, kill=False)
        finally:
            if move_vernier:
                ccm.E_Vernier.move(initial_energy, kill=kill)
            else:
                ccm.E.move(initial_energy, kill=kill)
            time.sleep(pointTime)


    def perform_run_with_escan(self, energies, record=True, comment='', pointTime=1,
                                 post=True, move_vernier=True,bidirectional=False,
                    **kwargs):
        """
        Perform a single run of the experiment

        Parameters
        ----------
        energies: List[float] a list of energies to scan over

        record: bool, optional
            Whether to record the run

        comment : str, optional
            Comment for ELog

        pointTime : int, optional
            how long in seconds to wait at a given energy before moving

        post: bool, optional
            Whether to post to the experimental ELog or not. Will not post if
            not recording

        move_vernier: bool, optional
            Whether or not to move the vernier while scanning the channel cut mono.


        Note
        ----
        """

        # Create descriptive message
        comment = comment or ''
        logger.info("Starting DAQ run, -> record=%s", record)
        daq.disconnect()
        daq.configure()
        try:
            #start DAQ, then start scanning
            daq.begin(record=record) #note we do not specify # of events, so it records until we stop
            # Post to ELog if desired
            runnum = daq._control.runnumber()
            #info = [runnum, comment, self._delaystr, min(energies), max(energies)]
            #post_msg = post_template_escan.format(*info)
            time.sleep(1) # give DAQ a second
           #print(post_msg)
           # if post and record:
           #     elog.post(msg=post_msg, run=runnum)
            #now start scanning
            self.continuous_ccmscan(energies, pointTime=pointTime, move_vernier=move_vernier,bidirectional=bidirectional)
        except KeyboardInterrupt:
            print('Interrupt signal received. Stopping run and DAQ')
        finally: 
            daq.end_run()
            logger.info("Run complete!")
            daq.disconnect()
        
        

    def loop(self, delays=[], nruns=1, light_events=3000, 
             dark_events=None, record=True, comment='', post=True):
        """
        Loop through a number of delays a number of times while running the DAQ
        Parameters
        ----------
        delays: list, optional
            Requested laser delays in nanoseconds
            close fs_shutter if False or None, 
            i.e., delays=[None, 1000, 1e6, 1e7] loop through:
            - close opo shutter
            - 1 us delay
            - 1 ms delay
            - 10 ms delay

        nruns: int, optional
            Number of iterations to run requested delays

        light_events: int, optional
            Number of events to sample with requested laser pulses
        dark_events: int, optional
           Number of events to sample with all lasers shuttered
        record: bool, optional
           Choice to record or not
        comment: str, optional
           Comment for ELog
        post : bool, optional
           Whether to post to ELog or not. Will not post if not recording.
        """
        
        # Accept a single int or float
        if isinstance(delays, (float, int)):
            delays = [delays]
        
        # Preserve the original state of DAQ
        logger.info("Running delays %r, %s times ...", delays, nruns)
        delays = delays or [False]
        try:
            for irun in range(nruns):
                run = irun+1
                logger.info("Beginning run %s of %s", run, nruns)
                for delay in delays:
                    if light_events:
                        # Perform the light run
                        self.perform_run(light_events,
                                         record=record,
                                         post=post, comment=comment)

                    # Perform the dark run
                    if dark_events:
                        self.perform_run(events=dark_events, record=record,
                                         post=post, comment=comment)
            logger.info("All requested scans completed!")
        except KeyboardInterrupt:
            logger.warning("Scan interrupted by user request!")
            logger.info("Stopping DAQ ...")
            daq.stop()
        
        # Return the DAQ to the original state
        finally:
            logger.info("Disconnecting from DAQ ...")
            daq.disconnect()
        return


    def loop_escan(self, energies, delays=[], nruns=1, record=True, comment='', 
                   post=True, pointTime=1, move_vernier=True):
        """
        Loop through a number of delays a number of times while running the DAQ
        Parameters
        ----------
        delays: list, optional
            Requested laser delays in nanoseconds
            close fs_shutter if False or None, 
            i.e., delays=[None, 1000, 1e6, 1e7] loop through:
            - 1 us delay
            - 1 ms delay
            - 10 ms delay

        nruns: int, optional
            Number of iterations to run requested delays

        record: bool, optional
            Whether to record the run or not
        comment: str, optional
           Comment for ELog
        post : bool, optional
           Whether to post to ELog or not. Will not post if not recording.
        pointTime: positive Number, optional
           time in seconds to dwell at a given energy before moving
        move_vernier: bool, optional
            whether to have vernier track CCM motion or not
        """
        
        # Accept a single int or float
        if isinstance(delays, (float, int)):
            delays = [delays]
        
        # Preserve the original state of DAQ
        logger.info("Running delays %r, %s times ...", delays, nruns)
        delays = delays or [False]
        try:
            for irun in range(nruns):
                run = irun+1
                logger.info("Beginning run %s of %s", run, nruns)
                for delay in delays:

                    # Perform the run
                    self.perform_run_with_escan(energies,
                                 record=record,
                                 post=post,
                                 comment=comment,
                                 pointTime=pointTime,
                                 move_vernier=move_vernier)
            logger.info("All requested scans completed!")
        except KeyboardInterrupt:
            logger.warning("Scan interrupted by user request!")
            logger.info("Stopping DAQ ...")
            daq.stop()
        
        # Return the DAQ to the original state
        finally:
            logger.info("Disconnecting from DAQ ...")
            daq.disconnect()
        return


    def dummy_daq_test(self, events=360, sleep=3, record=False):
        daq.connect()
        while 1:
            daq.begin(events=events, record=record)
            daq.wait()
            daq.end_run()
            time.sleep(sleep)
            print(time.ctime(time.time()))
        return


    def ccm_many(self, elist, pointTime=1, nRepeat=10, kill=True):
        for ii in range(nRepeat):
            print(f'Start scan {ii}')
            self.continuous_ccmscan(elist, pointTime=pointTime, kill=kill)
        return


post_template = """\
Run Number: {} {}

Acquiring {} events

{}
"""


post_template_escan = """\
Run Number: {} {}

{}
Minimum photon_energy -> {}
Maximum photon_energy -> {}
"""

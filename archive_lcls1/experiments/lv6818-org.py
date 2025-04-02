import os
import time
import os.path
import logging
import subprocess

import numpy as np
from ophyd import EpicsSignalRO
from bluesky import RunEngine
from bluesky.plans import scan
from bluesky.plans import list_scan
from xpp.devices import LaserShutter, MpodChannel, LaserShutterMPD
from xpp.devices import LaserShutterMPD_switch
from xpp.db import daq, elog, seq
from ophyd.status import wait as status_wait
from pcdsdevices.sequencer import EventSequencer
from pcdsdevices.evr import Trigger
from xpp.db import cp
from xpp.db import lp
from xpp.db import xpp_pulsepicker as pp
from xpp.db import xpp_ccm as ccm
#from xpp.db import vh_rot
from xpp.evosequence import Evosequence

from xpp.db import inhibit
from xpp.db import evo
from xpp.db import pacemaker

# WAIT A WHILE FOR THE DAQ TO START
import pcdsdaq.daq
pcdsdaq.daq.BEGIN_TIMEOUT = 5

#########
# TODO  #
#########
# * elog
# * time estimations


logger = logging.getLogger(__name__)


#######################
#  Object Declaration #
#######################
# Declare shutter 
test_shutter = LaserShutterMPD_switch('XPP:R39:MPD:CH:0', name='test_shutter')

evo_shutter1 = LaserShutterMPD('XPP:R39:MPD:CH:2', name='evo_shutter1')
evo_shutter2 = LaserShutterMPD('XPP:R39:MPD:CH:3', name='evo_shutter2')
evo_shutter3 = LaserShutterMPD('XPP:R39:MPD:CH:4', name='evo_shutter3')
#evo_shutter1 = LaserShutter('XPP:USR:ao1:7', name='evo_shutter1')
#evo_shutter2 = LaserShutter('XPP:USR:ao1:5', name='evo_shutter2')
#evo_shutter3 = LaserShutter('XPP:USR:ao1:6', name='evo_shutter3')
opo_shutter  = lp

# Trigger objects - created from questionnaire

# Laser parameter
opo_time_zero = 748935
base_inhibit_delay = 500000
evo_time_zero = 800000

LED    = MpodChannel('XPP:R39:MPD:CH:206', name='LED')
blower = MpodChannel('XPP:R39:MPD:CH:207', name='blower')

evosequence = Evosequence(seq)

#####
# XPP event code
#####
# 94 PP      (MFX: 197)
# 95 DAQ     (MFX: 198)
# 193 EVO    (MFX: 210)
# 194 EVO-1  (MFX :211)
# 215 EVO-2  (MFX :212)
# 216 EVO-3  (MFX :213)


###########################
# Configuration Functions #
###########################

class Alio_Record():
    def __init__(self, pvname='XPP:MON:MPZ:07A:POSITIONGET',time=1, 
                   filename=None):
        self.collection_time = time
        self.arr = []
        self.ts = []
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
        self.ts.append(kwargs['timestamp'])

    def setCollectionTime(self, ctime=None):
        self.collection_time = ctime

    def collectData(self):
        cbid = self.sig.subscribe(self.cb)
        time.sleep(self.collection_time)
        self.sig.unsubscribe(cbid)

    def setFilename(self, basename=None, useTime=True):
        if basename is None:
            basename = self.pvname.split(':')[0]+'_alio_position'
        if useTime:
            self.filename = basename+'_{}'.format(int(time.time()))
        else:
            self.filename = basename
        
    def writeFile(self):
        #print('saving to {}'.format(self.filename))
        with open(self.filename, 'w') as fd:
            for value,ts in zip(self.arr, self.ts):
                print(value, ts, file=fd)
        #if len(self.arr) == 0:
        #    print('Warning: no data points collected! File is empty!')
        self.arr = []


class User:
    """Generic User Object"""
    opo_shutter = cp
    evo_shutter1 = evo_shutter1
    evo_shutter2 = evo_shutter2
    evo_shutter3 = evo_shutter3
    sequencer = seq
    evosequence = evosequence

    inhibit = inhibit
    pacemaker = pacemaker
    evo = evo

    LED = LED
    blower = blower
    ccmE = ccm.calc

    evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp')
    evr_R30E28B = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28B')
    evr_pp = evr_R30E28B
    #_sync_markers = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7}
    _aliorecord = Alio_Record()

    @property
    def delay(self):
        """
        Laser delay in ns.
        """
        code = inhibit.eventcode.get()
        #MFX:
        #ipulse = {198: 0, 210: 0, 211:1, 212:2}.get(code)
        ipulse = {95: 0, 193: 0, 194:1, 215:2}.get(code)
        if ipulse is None:
            print('Inhibit event code {:} invalid'.format(code))

        return opo_time_zero+ipulse*1.e9/120. - pacemaker.ns_delay.get()

    @property
    def shutter_status(self):
        """Show current shutter status"""
        status = []
        for shutter in (evo_shutter1, evo_shutter2,
                        evo_shutter3, opo_shutter):
            status.append(shutter.state.get())
        return status

    def configure_shutters(self, pulse1=False, pulse2=False, pulse3=False, opo=None):
        """
        Configure all four laser shutters

        True means that the pulse will be used and the shutter is removed.
        False means that the pulse will be blocked and the shutter is inserted 
           - default for evo laser pulse1, pulse2, pulse3
        None means that the shutter will not be changed
           - default for opo laser

        Parameters
        ----------
        pulse1: bool
            Controls ``evo_shutter1``

        pulse2: bool
            Controls ``evo_shutter2``

        pulse3: bool
            Controls ``evo_shutter3``

        opo: bool
            Controls ``opo_shutter``
        """
        for state, shutter in zip((pulse1, pulse2, pulse3, opo),
                                  (evo_shutter1, evo_shutter2,
                                   evo_shutter3, opo_shutter)):
            if state is not None:
                logger.debug("Using %s : %s", shutter.name, state)
                shutter.move(int(state) + 1)

        time.sleep(1)

    def configure_evr(self):
        """
        Configure the Pacemaker and Inhibit EVR

        This handles setting the correct polarity and widths. However this
        **does not** handle configuring the delay between the two EVR triggers.
        """
        logger.debug("Configuring triggers to defaults ...")
        # Pacemaker Trigger
        pacemaker.eventcode.put(40)
        pacemaker.polarity.put(0)
        pacemaker.width.put(50000.)
        pacemaker.enable()
        # Inhibit Trigger
        inhibit.polarity.put(1)
        inhibit.width.put(2000000.)
        inhibit.enable()
        time.sleep(0.5)

    def set_pp_flipflop(self):
        burstdelay=4.5e-3*1e9
        flipflopdelay=8e-3*1e9
        #flipflopdelay=2e-3*1e9
        followerdelay=3.8e-5*1e9
        self.evr_pp.ns_delay.set(flipflopdelay)
        pp.flipflop(wait=True)

    def prepare_seq_120Hz(self):
        sync_mark = 6#int(_sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(2) # Run sequence forever
        ff_seq = [[95, 0, 0, 0]]
        #logging.debug("Sequence: {}".format(fly_seq))                  
        seq.sequence.put_seq(ff_seq) 

    @property
    def _delaystr(self):
        """
        OPO delay string
        """
        delay = self.delay
        if self.opo_shutter.state.value == 'IN':
            return 'No OPO Laser'
        elif delay >= 1e6:
            return 'Laser delay is set to {:10.6f} ms'.format(delay/1.e6)
        elif delay >= 1e3:
            return 'Laser delay is set to {:7.3f} us'.format(delay/1.e3)
        elif delay >= 0:
            return 'Laser delay is set to {:4.0f} ns'.format(delay)
        else:
            return 'Laser delay is set to {:8.0f} ns (AFTER X-ray pulse)'.format(delay)

    def set_delay(self, delay):
        """
        Set the relative delay between the pacemaker and inhibit triggers

        Parameters
        ----------
        delay: float
            Requested laser delay in nanoseconds. Must be less that 15.5 ms
        """
        # Determine event code of inhibit pulse
        logger.info("Setting delay %s ns (%s us)", delay, delay/1000.)
        if delay <= 0.16e6:
            if delay > 0 and delay < 1:
                logger.info("WARNING:  Read the doc string -- delay is in ns not sec") 
            logger.debug("Triggering on simultaneous event code")
            inhibit_ec = 193#210
            ipulse = 0
        elif delay <= 7.e6:
            logger.debug("Triggering on one event code prior")
            inhibit_ec = 194#211
            ipulse = 1
        elif delay <= 15.5e6:
            if self.sequencer.sync_marker.get() == '60Hz':
                raise ValueError("Invalid input %s ns, must be < 7.5 ms at 60 Hz")
            logger.debug("Triggering two event codes prior")
            inhibit_ec = 215#212
            ipulse = 2
        else:
            raise ValueError("Invalid input %s ns, must be < 15.5 ms")
        # Determine relative delays
        pulse_delay = ipulse*1.e9/120 - delay # Convert to ns
        # Conifgure Pacemaker pulse
        pacemaker_delay = opo_time_zero + pulse_delay
        pacemaker.ns_delay.put(pacemaker_delay)
        logger.info("Setting pacemaker delay %s ns", pacemaker_delay)
        # Configure Inhibit pulse
        inhibit_delay = opo_time_zero - base_inhibit_delay + pulse_delay
        inhibit.disable()
        time.sleep(0.1)
        inhibit.ns_delay.put(inhibit_delay)
        logger.info("Setting inhibit delay %s ns", inhibit_delay)
        inhibit.eventcode.put(inhibit_ec)
        logger.info("Setting inhibit ec %s", inhibit_ec)
        time.sleep(0.1)
        inhibit.enable()
        time.sleep(0.2)
        logger.info(self._delaystr)

#    def set_evo_delay(self, delay):
#        """
#        Set the evolution laser triggers delay
#
#        Parameters
#        ----------
#        delay: float
#            Requested evo laser delay in nanoseconds. Must be less that 15.5 ms
#        """
#        # Determine event code of evo pulse
#        logger.info("Setting evo delay %s ns (%s us)", delay, delay/1000.)
#        if delay <= 0.16e6:
#            logger.debug("Triggering on simultaneous event code")
#            evo_ec = 193#(MFX: 210, typically same as DAQ)
#            ipulse = 0
#        elif delay <= 7.e6:
#            logger.debug("Triggering on one event code prior")
#            evo_ec = 194:(MFX: 211, rayonix-1)
#            ipulse = 1
#        elif delay <= 15.5e6:
#            logger.debug("Triggering two event codes prior")
#            evo_ec = 215#(MFX: 212, rayonix-2)
#            ipulse = 2
#        else:
#            raise ValueError("Invalid input %s ns, must be < 15.5 ms")
#        # Determine relative delay
#        pulse_delay = ipulse*1.e9/120 - delay # Convert to ns
#        # Configure Inhibit pulse
#        evo_delay = evo_time_zero + pulse_delay
#        evo.eventcode.put(evo_ec)
#        evo.ns_delay.put(evo_delay)

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

        kwargs:
            Used to control the laser shutters. See ``configure_shutters`` for more
            information

        Note
        ----
        This does not configure the laser parameters. Either use ``loop`` or
        ``configure_evr`` and ``configure_sequencer`` to set these parameters
        """
        # Configure the shutters
        self.configure_shutters(**kwargs)
        # time.sleep(3) / a leftover from original script
        # Create descriptive message
        comment = comment or ''
        # Setup Event Sequencer
        #sequencer.stop()
        #sequencer.rep_count.put(events)
        #sequencer.play_mode.put(1)  # Run N Times
        # Start recording
        logger.info("Starting DAQ run, -> record=%s", record)
        daq.begin(events=events, record=record)
        #time.sleep(5)  # Wait for the DAQ to get spinnign before sending events
        #logger.debug("Starting EventSequencer ...")
        #sequencer.kickoff()
        time.sleep(1)
        # Post to ELog if desired
        runnum = daq._control.runnumber()
        info = [runnum, comment, events, self.current_rate, self._delaystr]
        info.extend(self.shutter_status)
        post_msg = post_template.format(*info)
        print(post_msg)
        if post and record:
            try:
                elog.post(post_msg, run=runnum)
            except:
                pass
        # Wait for the DAQ to finish
        logger.info("Waiting or DAQ to complete %s events ...", events)
        daq.wait()
        logger.info("Run complete!")
        daq.end_run()
        logger.debug("Stopping Sequencer ...")
        #sequencer.stop()
        #logger.info("Waiting for Sequencer to complete")
        #status_wait(sequencer.complete())
        #logger.info("Run complete!")
        #logger.debug("Stopping DAQ")
        #daq.end_run()
        # allow short time after sequencer stops
        time.sleep(0.5)

    def loop(self, delays=[], nruns=1, pulse1=False, pulse2=False,
             pulse3=False, light_events=3000, dark_events=None,
             record=True, comment='', post=True):
        """
        Loop through a number of delays a number of times while running the DAQ

        Parameters
        ----------
        delays: list, optional
            Requested laser delays in nanoseconds
            close opo_shutter if False or None, 
            i.e., delays=[None, 1000, 1e6, 1e7] loop through:
            - close opo shutter
            - 1 us delay
            - 1 ms delay
            - 10 ms delay

        nruns: int, optional
            Number of iterations to run requested delays

        pulse1: bool, optional
            Include the first pulse

        pulse2: bool, optional
            Include the second pulse

        pulse3: bool, optional
            Include the third pulse

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
        # Stop the EventSequencer
        #sequencer.stop()
        #self.configure_sequencer(rate=rate)
        self.configure_evr()
        # Preserve the original state of DAQ
        logger.info("Running delays %r, %s times ...", delays, nruns)
        delays = delays or [False]
        # Estimated time for completion
        try:
            for irun in range(nruns):
                run = irun+1
                logger.info("Beginning run %s of %s", run, nruns)
                for delay in delays:
                    if light_events:
                        # Set the laser delay if it exists
                        if delay is None or delay is False:
                            logger.info("Beginning light events with opo shutter closed")
                            # Close state = 1
                            opo_shutter.move(1)
                        else:
                            logger.info("Beginning light events using delay %s", delay)
                            # Open state = 2
                            opo_shutter.move(2)
                            self.set_delay(delay)

                        # Perform the light run
                        self.perform_run(light_events, pulse1=pulse1,
                                         pulse2=pulse2, pulse3=pulse3,
                                         record=record,
                                         post=post, comment=comment)
                    # Estimated time for completion
                    # Perform the dark run
                    # No shutter information means all closed!
                    if dark_events:
                        opo_shutter.move(1)
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
            logger.info("Closing all laser shutters ...")
            self.configure_shutters(pulse1=False, pulse2=False, pulse3=False, opo=False)
#            logger.info("Restarting the EventSequencer ...")
#            sequencer.play_mode.put(2)  # Run Forever!
#            sequencer.start()

    def saveAlio(self, colltime=None, filename=None):
        aliorecord = self._aliorecord
        if colltime is not None:
            aliorecord.setCollectionTime(colltime)
        if filename is not None:
            aliorecord.setFilename(filename)
        else:
            basename = aliorecord.pvname.split(':')[0]+'_alio'
            expname = subprocess.check_output('get_curr_exp').decode('utf-8').replace('\n','')
            try:
                runnr = int(subprocess.check_output('get_lastRun').decode('utf-8').replace('\n',''))
            except:
                runnr=0
            dirname = '/reg/neh/operator/%sopr/experiments/%s'%(expname[:3], expname)
            aliorecord.setFilename('%s/alioData/%s_Run%03d_%s.data'%(dirname,expname, runnr+1, basename))
        aliorecord.collectData()
        aliorecord.writeFile()
        print('Wrote %d seconds of alio data to %s'%(aliorecord.collection_time,aliorecord.filename))

    def takeRun(self, nEvents, record=None, use_l3t=False):
        daq.configure(events=120, record=record, use_l3t=use_l3t)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    def ascan(self, motor, start, end, nsteps, nEvents, record=None, use_l3t=False):
        self.cleanup_RE()
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor], use_l3t=use_l3t)
        try:
            RE(scan([daq], motor, start, end, nsteps))
        except Exception:
            logger.debug('RE Exit', exc_info=True)
        finally:
            self.cleanup_RE()
        motor.mv(currPos)

    def listscan(self, motor, posList, nEvents, record=None, use_l3t=False):
        self.cleanup_RE()
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor], use_l3t=use_l3t)
        try:
            RE(list_scan([daq], motor, posList))
        except Exception:
            logger.debug('RE Exit', exc_info=True)
        finally:
            self.cleanup_RE()
        motor.mv(currPos)

    def dscan(self, motor, start, end, nsteps, nEvents, record=None, use_l3t=False):
        self.cleanup_RE()
        daq.configure(nEvents, record=record, controls=[motor], use_l3t=use_l3t)
        currPos = motor.wm()
        try:
            RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        except Exception:
            logger.debug('RE Exit', exc_info=True)
        finally:
            self.cleanup_RE()
        motor.mv(currPos)

post_template = """\
Run Number: {} {}

Acquiring {} events at {} Hz

{}

While the laser shutters are:
EVO Pulse 1 ->  {}
EVO Pulse 2 ->  {}
EVO Pulse 3 ->  {}
OPO Shutter ->  {}
"""


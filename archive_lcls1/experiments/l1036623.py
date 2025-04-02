import numpy as np
import logging
import time

from ophyd import EpicsSignal, EpicsSignalRO

from pcdsdevices.sim import FastMotor, SlowMotor
from pcdsdevices.device_types import Trigger
from pcdsdevices.device_types import IMS, Newport
from pcdsdevices.targets import XYGridStage

from xpp.db import RE, bpp, bps, seq
from xpp.db import daq
from xpp.db import xpp_pulsepicker as pp
import time


sim_x = SlowMotor(name='x')
sim_y = SlowMotor(name='y')
sam_z = IMS(name='sam_z', prefix='XPP:USR:MMS:29')
sam_x = IMS(name='sam_x', prefix='XPP:USR:MMS:30')
target_x = IMS(name='sam_x', prefix='XPP:USR:MMS:05')
target_y = IMS(name='sam_x', prefix='XPP:USR:MMS:06')
sam_y = IMS(name='sam_y', prefix='XPP:USR:MMS:32')
grid_filepath = '/cds/home/opr/xppopr/experiments/xppl1012822/'

class User():
    def __init__(self):
        self._sync_markers = {0.5:0, 1:1, 5:2, 10:3, 30:4, 60:5, 120:6, 360:7}

        # pp trigger
        self.evr_pp = Trigger('XPP:USR:EVR:TRIG5', name='evr_pp')

        self.xy = XYGridStage(target_x, target_y, 6, 4, grid_filepath)
        return

    # ######### Target stages ################################
    def setup_target_grid(self, m, n, sample_name, sim=False):
        if sim:
            xy = XYGridStage(sim_x, sim_y, m, n, grid_filepath)
        else:
            xy = XYGridStage(target_x, target_y, m, n, grid_filepath)
        xy.set_presets()
        xy.map_points()
        xy.save_grid(sample_name)
        time.sleep(0.5)
        xy.load(sample_name)
        self.xy = xy
        return

    def load_sample_grid(self, sample_name):
        self.xy.load_sample(sample_name)
        self.xy.map_points()
        return

    # ######### Sequencer and pulse picker ################################
    def prepare_sequence(self, nShotsPre=1, nShotsOn=1, nShotsPost=0):
        # Setup sequencer
        self.clear_sequence()
        self.set_pp_flipflop()
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
        #seq.rep_count.put(nshots) # Run sequence N Times

        ppLine = [94, 2, 0, 0]  # delay 2 to make 30Hz
        daqLine = [95, 2, 0, 0]  # always wait 2 for the pulse-picker to open
        preLine = [190, 0, 0, 0]  # marker for shot with no laser
        onLine = [90, 0, 0, 0]  # laser on-demand
        postLine = [193, 0, 0, 0]  # marker for pulses after the laser

        shot_sequence=[]
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

        logging.info("Sequence: {}".format(shot_sequence))
        seq.sequence.put_seq(shot_sequence)
        return

    def sequence_120hz(self):
        self.clear_sequence()
        pp.close(wait=True)
        shot_sequence = [[95,0,0,0]]
        seq.sequence.put_seq(shot_sequence)
        seq.play_mode.put(2) # Play forever
        seq.start()
        return

    def clear_sequence(self):
        seq.stop()
        sequence = [[0,0,0,0]] * 200
        seq.sequence.put_seq(sequence)
        return

    def set_pp_flipflop(self):
        burstdelay = 4.5e-3*1e9 # not needed here
        flipflopdelay = 8e-3*1e9
        followerdelay = 3.8e-5*1e9 # not needed here
        self.evr_pp.ns_delay.set(flipflopdelay) # evr channel needs to be defined
        pp.flipflop(wait=True)
        return

    # ######### Grid scan  ################################
    @bpp.run_decorator()
    def gridScan(self, motor, posList, sample, iRange, jRange, deltaX, snake=True):
        """
        Perform a grid scan according to a pre-defined sample grid and moves a
        given motor at each new row.

        Args:
            motor: motor to move at each new row
            posList: position list for motor.
                     Its length must match the number of rows being scanned
            sample: sample grid name
            iRange: list of row to scan
            jRange: list of column to scan
            deltaX: horizontal offset to allow close packing
            snake: if the scan must follow a snake pattern or return to the
                   first column at the end of each row
        """
        if len(posList) != len(iRange):
            print('number of scan steps not matching grid total row number, abort.')
            return

        self.xy.load(sample)
        #self.prepare_sequence(1,1,1)
        #self.xy.move_to_sample(iRange[0], jRange[0])
        iRange = list(iRange)
        jRange = list(jRange)

        for ni,i in enumerate(iRange):
            print(f'Moving to row (line) {i}.')
            motor.umv(posList[ni])
            jRange_thisRow = jRange
            for j in jRange_thisRow:
                x_pos,y_pos = self.xy.compute_mapped_point(i, j, sample,
                                                      compute_all=False)
                if np.mod(i,2)==1:
                    x_pos = x_pos+deltaX
                yield from bps.mv(self.xy.x, x_pos, self.xy.y, y_pos)
                yield from bps.trigger_and_read([seq, self.xy.x, self.xy.y])
                while seq.play_status.get() == 2: continue
            if snake:
                jRange.reverse()

    
    def takeRun(self, nEvents, record=True):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    def get_ascan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        return scan([daq], motor, start, end, nsteps)

    def get_dscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record)
        currPos = motor.wm()
        return scan([daq], motor, currPos+start, currPos+end, nsteps)

    def ascan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))

    def listscan(self, motor, posList, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        RE(list_scan([daq], motor, posList))

    def dscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.wm()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))

    def setupSequencer(self, flymotor, distance, deltaT_shots, pp_shot_delay=2):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        #seq.play_mode.put(0) # Run sequence once
        seq.play_mode.put(1) # Run sequence N Times
    
        # Determine the different sequences needed
        beamDelay = int(120*deltaT_shots)-pp_shot_delay
        if (beamDelay+pp_shot_delay)<4:
            print('PP cannot go faster than 40 Hz in flip-flip mode, quit!')
            return
        fly_seq = [[185, beamDelay, 0, 0],
                   [187, pp_shot_delay, 0, 0]]
        #logging.debug("Sequence: {}".format(fly_seq))                  

        #calculate how often to shoot in requested distance
        flyspeed = flymotor.velocity.get()
        flytime = distance/flyspeed
        flyshots = int(flytime/deltaT_shots)
        seq.rep_count.put(flyshots) # Run sequence N Times

        seq.sequence.put_seq(fly_seq) 

    def setPP_flipflip(self, nshots=20, deltaShots=30):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        #seq.play_mode.put(0) # Run sequence once
        seq.play_mode.put(1) # Run sequence N Times
        seq.rep_count.put(nshots) # Run sequence N Times
    
        # Determine the different sequences needed
        beamDelay = int(delta_shots)-pp_shot_delay
        if (beamDelay+pp_shot_delay)<4:
            print('PP cannot go faster than 40 Hz in flip-flip mode, quit!')
            return
        ff_seq = [[185, beamDelay, 0, 0],
                   [187, pp_shot_delay, 0, 0]]
        #logging.debug("Sequence: {}".format(fly_seq))                  
        seq.sequence.put_seq(ff_seq) 

    def set_pp_flipflop(self):
        pp.flipflop(wait=True)

    def runflipflip(self, start, end, nsteps,nshots=20, deltaShots=30):
        self.set_pp_flipflop()
        #self.setPP_flipflip(nshots=20, deltaShots=6)
        for i in nsteps:
            self.evr_pp.ns_delay.set(start+delta*i)
            seq.start()
            time.sleep(5)

    def run_evr_seq_scan(self, start, env, nsteps, record=None, use_l3t=None):
        """RE the plan."""
        self.set_pp_flipflop()
        RE(evr_seq_plan(daq, seq, self.evr_pp, start, env, nsteps,
                        record=record, use_l3t=use_l3t))

    def evr_seq_plan(self, daq, seq, evr, start, end, nsteps,
                     record=None, use_l3t=None):
        """Configure daq and do the scan, trust other code to set up the sequencer."""
        yield from configure(daq, events=None, duration=None, record=record,
                             use_l3t=use_l3t, controls=[evr])
        yield from scan([daq, seq], evr, start, end, nsteps)

    def run_serp_seq_scan(self, shiftStart, shiftStop, shiftSteps, flyStart, flyStop, deltaT_shots, record=False, pp_shot_delay=2):
        daq.disconnect() #make sure we start from fresh point.
        shiftMotor=foil_y
        flyMotor=foil_x
        self.setupSequencer(flyMotor, abs(flyStop-flyStart), deltaT_shots, pp_shot_delay=pp_shot_delay)
        daq.configure(-1, record=record, controls=[foil_x, foil_y])
        #daq.begin(-1)
            
        if isinstance(shiftSteps, int):
             RE(serp_seq_scan(shiftMotor, np.linspace(shiftStart, shiftStop, shiftSteps), flyMotor, [flyStart, flyStop], seq))
        else:
             RE(serp_seq_scan(shiftMotor, np.arange(shiftStart, shiftStop, shiftSteps), flyMotor, [flyStart, flyStop], seq))

    def PPburst_sequence(self, nShots=None, nOffShots=2):
        if nOffShots < 2:
            raise ValueError('Minimum offshots is 2')
        ff_seq = [[185, 0, 0, 0]]
        ff_seq.append([179, 1 , 0, 0])
        ff_seq.append([179, 1 , 0, 0])
        if nShots is not None:
            if isinstance(nShots , int):
                ff_seq.append([185, nShots-2, 0, 0])
            else:
                ff_seq.append([185, int(nShots*120)-2, 0, 0])
        ff_seq.append([179, 2, 0, 0])
        if nShots is not None:
            if isinstance(nShots , int):
                for i in range(nOffShots-2):
                    ff_seq.append([179, 1, 0, 0])
            else:
                for i in range(int(nOffShots*120)-2):
                    ff_seq.append([179, 1, 0, 0])
        return ff_seq

    def prepare_seq_PPburst(self, nShots=None, nOffShots=None):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
        #seq.rep_count.put(nshots) # Run sequence N Times
    
        ff_seq = self.PPburst_sequence(nShots=nShots, nOffShots=nOffShots)
        seq.sequence.put_seq(ff_seq)

    def PPburst_sequence_pattern(self, nShots=None, nOffShots=None, nTimes=1):
        single_burst = self.PPburst_sequence(nShots=nShots, nOffShots=nOffShots)
        ff_seq = []
        for i in range(nTimes):
            ff_seq += single_burst
        return ff_seq

    def prepare_seq_PPburst_pattern(self, nShots=None, nOffShots=None, nTimes=1):
        ## Setup sequencer for requested rate
        #sync_mark = int(self._sync_markers[self._rate])
        #leave the sync marker: assume no dropping.
        sync_mark = int(self._sync_markers[120])
        seq.sync_marker.put(sync_mark)
        seq.play_mode.put(0) # Run sequence once
        #seq.play_mode.put(1) # Run sequence N Times
        #seq.rep_count.put(nshots) # Run sequence N Times

        ff_seq = self.PPburst_sequence_pattern(nShots=nShots, nOffShots=nOffShots, nTimes=nTimes)
        seq.sequence.put_seq(ff_seq)
        
    def dumbSnake(self, xStart, xEnd, yDelta, nRoundTrips,sweepTime):
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
         
        Need some testing how to deal with intermittent motion errors.
        """
        self.sam_x.umv(xStart)
        #sweeptime = abs(xStart-xEnd)/7
        daq.connect()
        daq.begin(record = True)
        time.sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        for i in range(nRoundTrips):
            
            print('starting round trip %d' % (i+1))
            self.sam_x.mv(xEnd)
            time.sleep(0.2)
            pp.open()
            time.sleep(sweepTime)
            pp.close()
            self.sam_x.wait()
            self.sam_y.umvr(yDelta)
            time.sleep(0.5)#orignal was 1
            self.sam_x.mv(xStart)
            time.sleep(0.2)
            pp.open()
            time.sleep(sweepTime)
            pp.close()
            self.sam_x.wait()
            self.sam_y.umvr(yDelta)
            print('ypos',self.sam_y.wm())
            time.sleep(0.5)#original was 1
            #except:
                #print('round trip %d didn not end happily' % i)
        daq.end_run()
        daq.disconnect()

    def dumbSnake_focus(self, xStart, xEnd, yDelta, zStart,zEnd,zDelta,nRoundTrips,sweepTime):
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
         
        Need some testing how to deal with intermittent motion errors.
        """
        self.sam_x.umv(xStart)
        self.sam_z.umv(zStart)
        zsteps = np.arange(zStart,zEnd+zDelta,zDelta)
        #sweeptime = abs(xStart-xEnd)/7
        daq.connect()
        time.sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        for i in range(round(np.shape(zsteps)[0]/2)):
           
            daq.begin(record = True)
            time.sleep(0.5)
            print('starting round trip %d' % (i+1))
            self.sam_x.mv(xEnd)
            time.sleep(0.2)
            pp.open()
            time.sleep(sweepTime)
            pp.close()
            self.sam_x.wait()
            daq.end_run()
            #daq.disconnect()

            self.sam_z.umvr(zDelta)
            self.sam_y.umvr(yDelta)
            #daq.connect()
            daq.begin(record = True)
            time.sleep(0.5)#orignal was 1
            self.sam_x.mv(xStart)
            time.sleep(0.2)
            pp.open()
            time.sleep(sweepTime)
            pp.close()
            self.sam_x.wait()
            daq.end_run()
            self.sam_z.umvr(zDelta)
            self.sam_y.umvr(yDelta)
            print('ypos',self.sam_y.wm())
            time.sleep(0.5)#original was 1
            #except:
                #print('round trip %d didn not end happily' % i)
        
    def dumbSnake_burst(self, xStart, xEnd, yDelta, nRoundTrips):
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
         
        Need some testing how to deal with intermittent motion errors.
        """
        self.sam_x.umv(xStart)
        daq.connect()
        daq.begin()
        sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        for i in range(nRoundTrips):
            try:
                print('starting round trip %d' % (i+1))
                self.sam_x.mv(xEnd)
                sleep(0.02)
                seq.start()
                #sleep(sweepTime)
                #pp.close()
                self.sam_x.wait()
                self.sam_y.mvr(yDelta)
                self.sam_y.wait()
                sleep(1.2)#orignal was 1
                self.sam_x.mv(xStart)
                sleep(0.02)
                #pp.open()
                #sleep(sweepTime)
                #pp.close()
                seq.start()
                self.sam_x.wait()
                self.sam_y.mvr(yDelta)
                self.sam_y.wait()
                print('ypos',x.sam_y.wm())
                sleep(1.2)#original was 1
            except:
                print('round trip %d didn not end happily' % i)
        daq.end_run()
        daq.disconnect()
    def dumbSnake_v(self, yStart, yEnd, xDelta, nRoundTrips, sweepTime):
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
         
        Need some testing how to deal with intermittent motion errors.
        """
        self.sam_y.umv(yStart)
        daq.connect()
        daq.begin()
        sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        for i in range(nRoundTrips):
            try:
                print('starting round trip %d' % (i+1))
                self.sam_y.mv(yEnd)
                sleep(0.05)
                pp.open()
                sleep(sweepTime)
                pp.close()
                self.sam_y.wait()
                self.sam_x.mvr(xDelta)
                sleep(1.2)#orignal was 1
                self.sam_y.mv(yStart)
                sleep(0.05)
                pp.open()
                sleep(sweepTime)
                pp.close()
                self.sam_y.wait()
                self.sam_x.mvr(xDelta)
                sleep(1.2)#original was 1
            except:
                print('round trip %d didn not end happily' % i)
        daq.end_run()
        daq.disconnect()




    def dumbSnake_burst_window(self,xStart,xEnd,yDelta, nRoundTrips, sweepTime,windowlist):#for burst mode
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
         
        Need some testing how to deal with intermittent motion errors.
        """
        #windowList = np.zeros([numYwindow,numXwindow],dtype=object)
        
        self.sam_x.umv(xStart)
        daq.connect()
        daq.begin()
        sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        for j in (windowList):
            self.sam_y.umv(windowList)
            self.sam_y.wait()
            print('Windos position %f'%(self.sam_w.wm()))
            for i in range(nRoundTrips):
                try:
                    print('starting round trip %d' % (i+1))
                    self.sam_x.mv(xEnd)
                    sleep(0.05)
                    seq.start()#start sequence Need to be set 
                    #sleep(sweepTime)
                    #pp.close()
                    self.sam_x.wait()
                    self.sam_y.mvr(yDelta)
                    sleep(1)#wait for turning around 
                    self.sam_x.mv(xStart)
                    sleep(0.05)
                    #pp.open()
                    seq.start()#start sequence 
                    #sleep(sweepTime)
                    #pp.close()
                    self.sam_x.wait()
                    self.sam_y.mvr(yDelta)
                    sleep(1)
                except:
                    print('round trip %d didn not end happily' % i)
        daq.end_run()
        daq.disconnect()

    def dumbSnake_burst_window_dev(self, xStart, xEnd, yDelta, nRoundTrips, sweepTime,windowList,startgrid):#for burst mode
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
        sleeptime is the pp close time between window 
        Need some testing how to deal with intermittent motion errors.
        """
        self.sam_x.umv(xStart)
        self.sam_y.umv(windowList[startgrid])
        daq.connect()
        daq.begin()
        sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        
        for j in range(len(windowList)-startgrid):
            self.sam_y.umv(windowList[startgrid+j])
            self.sam_y.wait()
            print('Window position %f'%(self.sam_y.wm()))

            for i in range(nRoundTrips):
                try:
                    print('starting round trip %d' % (i+1))
                    self.sam_x.mv(xEnd)
                    sleep(0.1)
                    seq.start()#start sequence Need to be set 
                    #sleep(sweepTime)
                    #pp.close()
                    self.sam_x.wait()
                    self.sam_y.mvr(yDelta)
                    print('yposition',self.sam_y.wm())
                    sleep(1.2)#wait for turning around 
                    self.sam_x.mv(xStart)
                    sleep(0.1)
                    #pp.open()
                    seq.start()#start sequence 
                    #sleep(sweepTime)
                    #pp.close()
                    self.sam_x.wait()
                    self.sam_y.mvr(yDelta)
                    print('yposition',self.sam_y.wm())
                    sleep(1.2)
                except:
                    print('round trip %d didn not end happily' % i)
                 
        daq.end_run()
        daq.disconnect()


    def dumbSnake_burst_dev(self, xStart, xEnd, yDelta, nRoundTrips, sweepTime,windowList,startgrid,mergin = 0.3):#for burst mode
        """ 
        simple rastering for running at 120Hz with shutter open/close before
        and after motion stop.
        sleeptime is the pp close time between window 
        Need some testing how to deal with intermittent motion errors.
        """
        self.sam_x.umv(xStart-mergin)#make the mergin for the acceleration
        self.sam_y.umv(windowList[startgrid])# go to the grid we want to start
        daq.connect()
        daq.begin()
        sleep(2)
        print('Reached horizontal start position')
        # looping through n round trips
        if(xEnd < xStart):
            mergin = mergin *(-1)
        for j in range(len(windowList)-startgrid):
            self.sam_y.umv(windowList[startgrid+j])
            self.sam_y.wait()
            print('Windos position %f'%(self.sam_y.wm()))

            for i in range(nRoundTrips):
                try:
                    print('starting round trip %d' % (i+1))
                    self.sam_x.mv(xEnd+mergin)
                    sleep(0.3)#wait for mergin and getting the constant velocity
                    seq.start()#start sequence Need to be set 
                    #sleep(sweepTime)
                    #pp.close()
                    self.sam_x.wait()
                    self.sam_y.mvr(yDelta)
                    print('yposition',self.sam_y.wm())
                    sleep(1.2)#wait for turning around 
                    self.sam_x.mv(xStart-mergin)
                    sleep(0.3)
                    #pp.open()
                    seq.start()#start sequence 
                    #sleep(sweepTime)
                    #pp.close()
                    self.sam_x.wait()
                    self.sam_y.mvr(yDelta)
                    print('yposition',self.sam_y.wm())
                    sleep(1.2)
                except:
                    print('round trip %d didn not end happily' % i)
                 
        daq.end_run()
        daq.disconnect()


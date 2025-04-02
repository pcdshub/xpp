import numpy as np
from hutch_python.utils import safe_load
from pcdsdevices import analog_signals
from xpp.db import xpp_attenuator as att
from xpp.db import xpp_jj_3 as xpp_jj_3
from xpp.db import xpp_jj_2 as xpp_jj_2
from xpp.db import daq, pp
from time import sleep
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import EpicsMotor
from xpp.db import RE, bpp, bps, seq, lp
from pcdsdevices.beam_stats import BeamEnergyRequest, BeamEnergyRequestACRWait

from pcdsdevices import analog_signals
import epics
from pcdsdevices.targets import XYGridStage

from pcdsdevices.sim import FastMotor, SlowMotor
grid_filepath = '/cds/home/opr/xppopr/experiments/xppl1016922/'
target_x = FastMotor() # fake motors
target_y = FastMotor()


#target_x = IMS('XPP:USR:PRT:MMN:08', name='grid_x')
#target_y = IMS('XPP:USR:PRT:MMS:32', name='grid_y')
xy = XYGridStage(target_x, target_y, 1, 10, grid_filepath)

SET_WAIT = 2


class SettleSignal(EpicsSignal):
    def __init__(self, *args, settle_time=None, **kwargs):
        self._settle_time = settle_time
        super().__init__(*args, **kwargs)
    
    def set(self, *args, **kwargs):
        return super().set(*args, settle_time=self._settle_time, **kwargs)

class User():
    def __init__(self):
        self.aio = analog_signals.Acromag(name = 'xpp_aio', prefix = 'XPP:USR')
        self.dl = EpicsMotor(prefix='XPP:ENS:01:m0', name='aero')
    
    # ----------------------------------------------
    #    Move crystals gratings and diodes
    #    Haoyuan: 
    #    If we can reserve some presets with each motors
    #    the functions can be defined in a more general and 
    #    robust way. However, I do not know if that is possible
    #    Therefore, I decide not to do it in that way. 
    #    Instead, I'll just keep updating this file and urge 
    #    X-ray opterator to restart their xpp3 interface.
    # ----------------------------------------------
    def miniSD_bypass_g1g2Sb4(self):
        self.miniSD_bypass_g1g2()
        self.miniSD_bypass_Sb4()
        self.miniSD_bypass_diode()

    def miniSD_bypass_g1g2(self):
        self.g1y.umv(-9)
        self.g2y.umv(-9)
    
    def miniSD_bypass_crystals(self):
        self.t1x.umv(-5.5)
        self.t2x.umv(5.85)
        self.t3x.umv(7.35)
        self.dl.move(0)
        self.t6x.umv(5.5)
    
    def miniSD_insert_crystals(self):
        self.t1x.umv(-3.85)
        self.t2x.umv(1.38)
        self.t3x.umv(2.02)
        self.dl.move(14.78)
        self.t6x.umv(2.2)

    def miniSD_bypass_diode(self):
        self.d2x.umv(20)
        self.d3x.umv(20)
        self.d4x.umv(40)
    
    def miniSD_insert_g1g2Sb4(self):
        self.miniSD_insert_diode()
        self.miniSD_insert_Sb4_crystals()
        self.miniSD_insert_diode()

    def miniSD_insert_diode(self):
        self.d2x.umv(-24)
        self.d3x.umv(0)
        self.d4x.umv(24.3)
       
    def miniSD_insert_g1g2(self):
        self.g1_y.umv(0.52)
        self.g2y.umv(1.09)
    

    def miniSD_insert_diode_for_directBeam(self):
        self.d2x.umv(0)
        self.d3x.umv(0)
        self.d4x.umv(0)

    def miniSD_remove_diode_for_dataCollection(self):
        self.d2x.umv(0)
        self.d3x.umv(-1)
        self.d4x.umv(0)

    # ------------------------------------------------------------
    #    Change beam position, CC/VCC/Both/Neither and delay time range with miniSD
    # ------------------------------------------------------------
    def move_delay_offset(self, offset):
        self.t2x.umvr(offset)
        self.t3x.umvr(offset)

    def move_unfocused_beam(self, offset):
        self.t2x.umvr(offset)
        self.t3x.umvr(-offset)

    def move_focused_beam(self, offset):
        if offset>4e-4: 
            print ("this step seems to be rather large")
        self.t3th.umvr(offset)
        self.t5th.umvr(-offset)

    def show_CC(self):
        self.aio.ao1_2.set(5)
        self.aio.ao1_3.set(0)
    
    def show_VCC(self):
        self.aio.ao1_2.set(0)
        self.aio.ao1_3.set(5)
    
    def show_both(self):
        self.aio.ao1_2.set(5)
        self.aio.ao1_3.set(5)
    
    def show_neither(self):
        self.aio.ao1_2.set(0)
        self.aio.ao1_3.set(0)

		
    def takeRun(self, nEvents=None, duration=None, record=True, use_l3t=False):
        daq.configure(events=120, record=record, use_l3t=use_l3t)
        daq.begin(events=nEvents, duration=duration)
        daq.wait()
        daq.end_run()

    def calc_MADM(self, r1 = 0.605, r2 = 1.805, angle = 21.0):
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

    def move_CC_out(self,_t1x = -5.5, _t6x = 5.5):
        self.t1x.umv(_t1x)
        self.t6x.umv(_t6x)
        return

        
    def move_CC_in(self, _t1x = -3.1, _t6x = 2.05):
        self.t1x.umv(_t1x)
        self.t6x.umv(_t6x)
        return

### grid scan script

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



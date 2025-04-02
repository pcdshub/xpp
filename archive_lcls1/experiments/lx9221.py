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

from pcdsdevices.beam_stats import BeamEnergyRequest, BeamEnergyRequestACRWait

from pcdsdevices import analog_signals
#import pcdsdevices.analog_signals as analog_signals

SET_WAIT = 2


class SettleSignal(EpicsSignal):
    def __init__(self, *args, settle_time=None, **kwargs):
        self._settle_time = settle_time
        super().__init__(*args, **kwargs)
    
    def set(self, *args, **kwargs):
        return super().set(*args, settle_time=self._settle_time, **kwargs)

class User():
    def __init__(self):
        self.energy_set = SettleSignal('XPP:USER:MCC:EPHOT:SET1', 
                                       name='energy_set', 
                                       settle_time=SET_WAIT)
        self.energy_ref = SettleSignal('XPP:USER:MCC:EPHOT:REF1', 
                                       name='energy_ref')

        self.acr_energy = BeamEnergyRequestACRWait(name='acr_energy', 
                                                   prefix='XPP', 
                                                   acr_status_suffix='AO805')

        #with safe_load('analog_out'):
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
        self.g1_y.umv(-9)
        self.g2y.umv(-9)
    
    def miniSD_bypass_Sb4_crystals(self):
        self.t1x.umv(-9.3)
        self.t2x.umv(36.5)
        self.t3x.umv(7.0)
        self.dl.move(1)
        self.t6x.umv(5.0)

    def miniSD_bypass_diode(self):
        self.d2x.umv(20)
        self.d3x.umv(20)
        self.d4x.umv(40)
    
    def miniSD_insert_g1g2Sb4(self):
        self.miniSD_insert_diode()
        self.miniSD_insert_Sb4_crystals()
        self.miniSD_insert_diode()

    def miniSD_insert_diode(self):
        self.d2x.umv(22)
        self.d3x.umv(-1)
        self.d4x.umv(-22)
       
    def miniSD_insert_g1g2(self):
        self.g1_y.umv(0.52)
        self.g2y.umv(1.09)
    
    def miniSD_insert_Sb4_crystals(self):
        self.t1x.umv(-7.1)
        self.t2x.umv(26.48)
        self.t3x.umv(-2.17998)
        self.dl.move(12)
        self.t6x.move(1.9)

    def miniSD_insert_diode_for_directBeam(self):
        self.d2x.umv(0)
        self.d3x.umv(-1)
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
        self.aio.ao1_2.set(0)
        self.aio.ao1_3.set(5)
    
    def show_VCC(self):
        self.aio.ao1_2.set(5)
        self.aio.ao1_3.set(0)
    
    def show_both(self):
        self.aio.ao1_2.set(5)
        self.aio.ao1_3.set(5)
    
    def show_neither(self):
        self.aio.ao1_2.set(0)
        self.aio.ao1_3.set(0)

    # ----------------------------------------------
    #    Move beam with CRL
    # ----------------------------------------------
    def move_unfocused(self):
        self.crl_x.umv_out()
        self.crl_y.umv_out()
        att(1)
        xpp_jj_3.hg(1)

    def move_focused(self):
        att(0.01)
        self.crl_x.umv_in()
        self.crl_y.umv_in()
        xpp_jj_3.hg(0.25)

    # ----------------------------------------------
    #    Move sample tower to switch between static sample, yag 200um, yag 20um, and pressurecell window
    # ----------------------------------------------
    def samTower_move_static(self):
        print("Haoyuan has not implemented them yet")
        pass

    def samTower_move_yag200(self):
        print("Haoyuan has not implemented them yet")
        pass

    def samTower_move_yag20(self):
        print("Haoyuan has not implemented them yet")
        pass

    def samTower_move_cellDiamond(self):
        print("Haoyuan has not implemented them yet")
        pass

    # ----------------------------------------------
    #    Legacy function from old experiments
    # ----------------------------------------------    
    def takeRun(self, nEvents=None, duration=None, record=True, use_l3t=False):
        daq.configure(events=120, record=record, use_l3t=use_l3t)
        daq.begin(events=nEvents, duration=duration)
        daq.wait()
        daq.end_run()

    def dumbSnake(self, xStart, xEnd, yDelta, nRoundTrips, sweepTime):
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
                sleep(0.1)
                pp.open()
                sleep(sweepTime)
                pp.close()
                self.sam_x.wait()
                self.sam_y.umvr(yDelta)
                sleep(1.2)#orignal was 1
                self.sam_x.mv(xStart)
                sleep(0.1)
                pp.open()
                sleep(sweepTime)
                pp.close()
                self.sam_x.wait()
                self.sam_y.umvr(yDelta)
                print('ypos',self.sam_y.wm())
                sleep(0.5)#original was 1
            except:
                print('round trip %d didn not end happily' % i)
        daq.end_run()
        daq.disconnect()            

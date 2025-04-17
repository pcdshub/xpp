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
    #    Legacy function from old experiments
    # ----------------------------------------------    
    def takeRun(self, nEvents=None, duration=None, record=True, use_l3t=False):
        daq.configure(events=120, record=record, use_l3t=use_l3t)
        daq.begin(events=nEvents, duration=duration)
        daq.wait()
        daq.end_run()


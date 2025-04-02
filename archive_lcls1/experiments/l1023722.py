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
import epics



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

    def mirror_gap_monitor(self,m2x0=0,m3x0=0, gaplimit=0.2):
    	# check the m2 m3 mirror position
    	monitorstop=0
    	while(monitorstop<1):
    		m2xp=self.m2x.wm()
    		m3xp=self.m3x.wm()
    		mgap=(m2xp-m2x0)-(m3xp-m3x0)    		
    		if (mgap<gaplimit): 
    			epics.caput("XPP:USR:PRT:MMS:19.SPG",0)
    			epics.caput("XPP:USR:PRT:MMS:20.SPG",0)

    			print('\033[91m Currrent gap limit is \033[0m',gaplimit )
    			print('\033[91m Currrent gap is \033[0m',mgap )
    			print('\033[91m Stopped the motor movement \033[0m')
    			print('\033[91m Use command x.mirros_enable() to reuse it\033[0m')
    			monitorstop = 2
    		else : print("mirror gap is : ", mgap)
    		sleep(0.2)

		
    def mirror_enable(self):
    	epics.caput("XPP:USR:PRT:MMS:19.SPG",2)
    	epics.caput("XPP:USR:PRT:MMS:20.SPG",2)

    def surface_move_si_z(self, delta):
        self.si_z.umvr(delta)
        self.si_y.umvr( - delta * np.sin(np.deg2rad(11.639)))

    def surface_move_m2_z(self, delta):
        self.m2z.move(delta + self.m2z.position)
        self.m2x.umvr( - delta * np.sin(np.deg2rad(self.m2chi())))

    def surface_move_m3_z(self, delta):
        self.m3z.move(delta + self.m3z.position)
        self.m3x.umvr(delta * np.sin(np.deg2rad(self.m3chi())))

    # ----------------------------------------------
    #    Legacy function from old experiments
    # ----------------------------------------------    
    def takeRun(self, nEvents=None, duration=None, record=True, use_l3t=False):
        daq.configure(events=120, record=record, use_l3t=use_l3t)
        daq.begin(events=nEvents, duration=duration)
        daq.wait()
        daq.end_run()

    def calc_MADM(self, r1 = 571.2, r2 = 1774.7, angle = 21.0):
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

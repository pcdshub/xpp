import numpy as np
from hutch_python.utils import safe_load
from pcdsdevices import analog_signals

from ophyd import EpicsSignal
from ophyd import EpicsSignalRO

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
        self.energy_set = SettleSignal('XPP:USER:MCC:EPHOT:SET1', name='energy_set', settle_time=SET_WAIT)
        self.energy_ref = SettleSignal('XPP:USER:MCC:EPHOT:REF1', name='energy_ref')

        self.acr_energy = BeamEnergyRequestACRWait(name='acr_energy', prefix='XPP', acr_status_suffix='AO805')

    #with safe_load('analog_out'):
        self. aio = analog_signals.Acromag(name = 'xpp_aio', prefix = 'XPP:USR')
    def miniSD_clear_beam(self):
        self.t1x.umv(-7.0)
        self.t2x.umv(36.5)
        self.t3x.umv(7.0)
        self.t6x.umv(5.0)
        self.d2x.umv(0)
        self.d4x.umv(0)
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

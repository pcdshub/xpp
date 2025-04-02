import numpy as np
from hutch_python.utils import safe_load
from pcdsdevices import analog_signals
from pcdsdevices.device_types import IMS 
from xpp.db import xpp_attenuator as att
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
        self.sy = IMS('XPP:USR:MMS:26', name='sy')
        self.sx = IMS('XPP:USR:MMS:27', name='sx')

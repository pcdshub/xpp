import os
import time
import os.path
import logging

import numpy as np
import random
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FCpt
from ophyd import  Device, EpicsSignal, EpicsSignalRO
from bluesky import RunEngine
from hutch_python.utils import safe_load
from pcdsdevices.state import StatePositioner
from nabs.plans import delay_scan, daq_delay_scan
from pcdsdevices.interface import BaseInterface
from ophyd.device import Device
from ophyd.signal import EpicsSignal
from pcdsdevices.sequencer import EventSequencer# for evt sequence 
from pcdsdevices.device_types import Newport, IMS, DelayNewport
############ for sudo lxt motion##############################################
#for laser drop shot
try:
    from xpp.db import daq, seq, elog
except:
    print('Cannot import elog as normal user')
from xpp.db import cp
from xpp.db import lp
seq = EventSequencer('ECS:SYS0:3', name='seq_3') 
logger = logging.getLogger(__name__)

class HeaterState(StatePositioner):
    state = FCpt(EpicsSignal, '{self.prefix}:PUT_RANGE_{self.channel}', kind='normal')
    _unknown = False # override default state 0 = Unknown
    states_list = ['Off', 'Low', 'Medium', 'High']

    def __init__(self, prefix, channel=1, **kwargs):
        self.channel = channel
        super().__init__(prefix, **kwargs)


class LakeShore336(Device):
    inp_a = Cpt(EpicsSignal, ':GET_TEMP_A', kind='normal')
    inp_b = Cpt(EpicsSignal, ':GET_TEMP_B', kind='normal')
    inp_c = Cpt(EpicsSignal, ':GET_TEMP_C', kind='normal')
    inp_d = Cpt(EpicsSignal, ':GET_TEMP_D', kind='normal')

qwp = Newport('XPP:USR:MMN:07', name='qwp')
class User: 
    def wp_switcher(self,rlratio = 1):
        while(1):
            qwp.mv(68,wait = True)
            while(qwp.moving == True):
                time.sleep(0.1)
                print("switch polarization")
            shot_seq = [[94,1,0,0]]
            seq.sequence.put_seq(shot_seq)
            seq.start()
            accumtime = random.randint(550,750)*0.1
            time.sleep(accumtime)
            seq.stop()
            qwp.mv(-22,wait = True)
            while(qwp.moving == True):
                time.sleep(0.1)
                print("switch polarization")
            shot_seq = [[95,1,0,0]]
            seq.sequence.put_seq(shot_seq)
            seq.start()
            accumtime = random.randint(550,750)*rlratio*0.1
            time.sleep(accumtime)
            seq.stop()
        return
 
            
    """Generic User Object"""
    with safe_load('Lakeshore'):
        sample = EpicsSignalRO('XPP:USR:TCT:01:GET_TEMP_B', name='sample_T')
        copper = EpicsSignalRO('XPP:USR:TCT:01:GET_TEMP_C', name='copper_T')
        coldhead = EpicsSignalRO('XPP:USR:TCT:01:GET_TEMP_D', name='cold_head_T')
        heater_copper = EpicsSignal('XPP:USR:TCT:01:GET_SOLL_1',
                                    write_pv='XPP:USR:TCT:01:PUT_SOLL_1',
                                    name='heater_copper')
        heater_coldhead = EpicsSignal('XPP:USR:TCT:01:GET_SOLL_2',
                                      write_pv='XPP:USR:TCT:01:PUT_SOLL_2',
                                      name='heater_coldhead')
        heater_range_1 = HeaterState('XPP:USR:TCT:01', channel=1, name='heater_1')
        heater_range_2 = HeaterState('XPP:USR:TCT:01', channel=2, name='heater_2')

    valve = EpicsSignal('XPP:USR:ao1:0.VAL', name='valve')

    def set_valve(self, new_valve):
        self.valve.put(new_valve)
        return
    
    def get_valve(self):
        valve_value = self.valve.get() 
        print(valve_value)       
        return

    def set_temp(self, new_temp, delta=30.0):
        #if (new_temp > 200) and (new_temp < 250):
        #    delta = 25.0
        #if (new_temp < 200):
        #    delta = 50.0
        target_T = new_temp
        current_T = self.sample.get()
        self.heater_copper.put(new_temp)
        self.heater_coldhead.put(new_temp-delta)
        self.heater_range_1.set('High')
        self.heater_range_2.set('High')
        while True:
            if abs(target_T - current_T) < 0.1:
                time.sleep(30) #do nothing
                continue
            else: #it needs tweaking
                if current_T < target_T:
                    current_T = self.sample.get()
                    print("Target Tempoerature: {tt}, Current Temperature: {ct}, Power will be increased.".format(tt=target_T, ct=current_T))
                    coldhead_set_T = self.heater_coldhead.get()
                    print(copper_set_T, coldhead_set_T)
                    time.sleep(30)
                    continue
                if current_T > target_T:
                    current_T = self.sample.get()
                    copper_set_T = self.heater_copper.get()
                    coldhead_set_T = self.heater_coldhead.get()
                    print("Target Tempoerature: {tt}, Current Temperature: {ct}, Power will be reduced.".format(tt=target_T, ct=current_T))
                   
                    time.sleep(30)
                    continue    
        #heater_copper.put(new_temp)
        #heat_coldhead.put(new_temp)
        #self.heater_range_1.set('High')
        return






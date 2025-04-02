import numpy as np
from ophyd import EpicsSignal



class User:
    def __init__(self, ):
        self.citius_dl = EpicsSignal('XPP:CITIUS::TPR:01:TRG10_SYS0_TDES',
                                name='citius_delay')
        return
    def move_citius_delay(self, delay_count, t0_count = 94805):
        t = (delay_count+t0_count)*8.4
        self.citius_dl.put(int(t))
        print (self.citius_dl.get(), t, delay_count)
        return


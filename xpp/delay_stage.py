
from ophyd.pseudopos import(PseudoPositioner, PseudoSingle, real_position_argument, pseudo_position_argument)
from pcdsdevices.epics_motor import Newport
from ophyd import Device, Component as Cpt
from ophyd.sim import SynSignal
from ophyd.positioner import SoftPositioner

speed_of_light = 2.99792458e8
units_mm = 1e3
class DelayStage(PseudoPositioner):
	delay = Cpt(PseudoSingle, egu = 'ns')
	real_motor = Cpt(Newport,'')
	def __init__(self,stage, prefix, *args,direction = 1 , **kwargs):
		self.stage = stage
		self.direction = direction
		super().__init__(prefix, *args, **kwargs)
	@pseudo_position_argument
	def forward(self, pseudo_pos):
		pseudo_pos = self.PseudoPosition(*pseudo_pos)
		ns = psuedo_pos.delay
                #Math to get from delay to real position
		mm = self.direction*ns*speed_of_light*units_mm
		print(mm)
		return self.RealPosition(real_motor=mm)
	@real_position_argument
	def inverse(self,real_pos):
		real_pos = self.RealPosition(*real_pos)
		mm = real_pos.real_motor
                #Math to get from real position to delay
		ns = self.direction*mm/units_mm/speed_of_light
		print(ns)
		return self.PseudoPosition(delay=ns)

class FakeDelay(DelayStage):
	real_motor= Cpt(SoftPositioner, init_pos=0)


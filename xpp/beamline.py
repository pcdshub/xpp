from hutch_python.utils import safe_load
from pcdsdevices.device_types import Newport, IMS
from xpp.delay_stage import FakeDelay
from xpp.db import scan_pvs
from ophyd.sim import motor as fake_motor

scan_pvs.enable()

with safe_load('fake_delay'):
    fake_delay = FakeDelay('', '',name='fake_delay')

with safe_load('xpp_gon_h'):
    xpp_gon_h = IMS('XPP:GON:MMS:01', name = 'xpp_gon_h')

with safe_load('xpp_gon_v'):
    xpp_gon_v = IMS('XPP:GON:MMS:02', name = 'xpp_gon_v')

with safe_load('xpp_gon_r'):
    xpp_gon_r = IMS('XPP:GON:MMS:03', name = 'xpp_gon_r')

with safe_load('xpp_gon_tip'):
    xpp_gon_tip = IMS('XPP:GON:MMS:04', name = 'xpp_gon_tip')

with safe_load('xpp_gon_tilt'):
    xpp_gon_tilt = IMS('XPP:GON:MMS:05', name = 'xpp_gon_tilt')

with safe_load('xpp_gon_z'):
    xpp_gon_z = IMS('XPP:GON:MMS:06', name = 'xpp_gon_z')

with safe_load('xpp_gon_x'):
    xpp_gon_x = IMS('XPP:GON:MMS:07', name = 'xpp_gon_x')

with safe_load('xpp_gon_y'):
    xpp_gon_y = IMS('XPP:GON:MMS:08', name = 'xpp_gon_y')

with safe_load('xpp_gon_kappa_eta'):
    xpp_gon_kappa_eta = IMS('XPP:GON:MMS:09', name = 'xpp_gon_kappa_eta')

with safe_load('xpp_gon_kappa_kappa'):
    xpp_gon_kappa_kappa = IMS('XPP:GON:MMS:10', name = 'xpp_gon_kappa_kappa')

with safe_load('xpp_gon_kappa_x'):
    xpp_gon_kappa_x = IMS('XPP:GON:MMS:12', name = 'xpp_gon_kappa_x')

with safe_load('xpp_gon_kappa_y'):
    xpp_gon_kappa_y = IMS('XPP:GON:MMS:13', name = 'xpp_gon_kappa_y')

with safe_load('xpp_gon_kappa_z'):
    xpp_gon_kappa_z = IMS('XPP:GON:MMS:14', name = 'xpp_gon_kappa_z')

with safe_load('xpp_gon_sam_phi'):
    xpp_gon_sam_phi = IMS('XPP:GON:MMS:15', name = 'xpp_gon_sam_phi')

with safe_load('xpp_gon_sam_z'):
    xpp_gon_sam_z = IMS('XPP:GON:MMS:16', name = 'xpp_gon_sam_z')

from xpp.db import RE, daq, bp
def run_ascan_daq_noplot(mot, a, b, points, events_per_point, use_l3t=False):
    if RE.state != 'idle':
        RE.abort()
    daq.configure(events=events_per_point, use_l3t=use_l3t, controls=[mot])
    RE(bp.scan([daq], mot, a, b, points))

#XXX

#with safe_load('xpp_las_delay'):
#    xpp_las_delay = Newport('XPP:LAS:MMN:04', name = 'xpp_las_delay')

#with safe_load('xpp_las_lensv'):
#    xpp_las_lensv = Newport('XPP:LAS:MMN:05', name = 'xpp_las_lensv')

#with safe_load('xpp_las_lensh'):
#     xpp_las_lensh = Newport('XPP:LAS:MMN:06', name = 'xpp_las_lensh')

#with safe_load('xpp_las_lensf'):
#     xpp_las_lensf = Newport('XPP:LAS:MMN:08', name = 'xpp_las_lensf')

#with safe_load('xpp_las_tt_lensh'):
#     xpp_las_tt_lensh = Newport('XPP:LAS:MMN:13', name = 'xpp_las_tt_lensh')

#with safe_load('xpp_las_tt_lensv'):
#     xpp_las_tt_lensv = Newport('XPP:LAS:MMN:14', name = 'xpp_las_tt_lensv')

#with safe_load('xpp_las_tt_lensf'):
#     xpp_las_tt_lensf = Newport('XPP:LAS:MMN:14', name = 'xpp_las_tt_lensf')

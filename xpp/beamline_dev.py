from hutch_python.utils import safe_load
from pcdsdevices.device_types import Newport, PMC100, IMS, BeckhoffAxis
from xpp.delay_stage import FakeDelay
from xpp.db import scan_pvs
from xpp.devices import LaserShutter
from ophyd.sim import motor as fake_motor

scan_pvs.enable()

with safe_load('pyami detectors'):
    from xpp.ami_detectors import *

# XPP has been assigned event sequencer 3 and 10. We largely use 10 for the laser dropped shots
# and 3 for pulse picker + other actions.
from pcdsdevices.sequencer import EventSequencer
seq = EventSequencer('ECS:SYS0:3', name='seq')
seq_laser = EventSequencer('ECS:SYS0:10', name='seq_laser')

with safe_load('fake_delay'):
    fake_delay = FakeDelay('', '',name='fake_delay')

with safe_load('xpp_lens'):
    from pcdsdevices.lens import LensStack
    from xpp.db import xpp_attenuator
    _folder = "/reg/g/pcds/pyps/apps/hutch-python/xpp/"

    #snelson: commenting this out for now as it's 'talky' 
    #   while not being called
    ##########################
    #xpp_lens = LensStack("XPP:SB2:MMS:13",  # X
    #                     "XPP:SB2:MMS:14",  # Y
    #                     "XPP:SB2:MMS:15",  # Z
    #                     name='xpp_lens',
    #                     z_offset=3.852,   # lifted from old
    #                     z_dir=-1,         # lifted from old
    #                     E=9.5,            # keV, not automatic
    #                     att_obj=xpp_attenuator,  # breaks happi
    #                     beamsize_unfocused=500e-6,  # from old
    #                     path=_folder + "lens/sets_Be")
#crl=xpp_lens

with safe_load('GON motors XYZ'):
    from pcdsdevices.gon import XYZStage
    xpp_gon_xyz = XYZStage(name = 'xpp_gon_xyz',
                           prefix_x = 'XPP:GON:MMS:07',
                           prefix_y = 'XPP:GON:MMS:08',
                           prefix_z = 'XPP:GON:MMS:06')

with safe_load('GON motors Phi-Z'):
    from pcdsdevices.gon import SamPhi
    xpp_gon_sam = SamPhi(name = 'xpp_gon_samphi',
                         prefix_samz = 'XPP:GON:MMS:16',
                         prefix_samphi = 'XPP:GON:MMS:15')

with safe_load('xpp_gon_kappa'):
    from pcdsdevices.gon import Kappa
    xpp_gon_kappa = Kappa(name = 'xpp_gon_kappa',
                          prefix_x = 'XPP:GON:MMS:13',
                          prefix_y = 'XPP:GON:MMS:12',
                          prefix_z = 'XPP:GON:MMS:14',
                          prefix_eta = 'XPP:GON:MMS:09',
                          prefix_kappa = 'XPP:GON:MMS:10',
                          #prefix_phi = 'XPP:GON:MMS:11')
                          prefix_phi = 'XPP:GON:MMS:15')
    kappa = xpp_gon_kappa

with safe_load('Combine gon objects'):
    from xpp.db import xpp_gon
    xpp_gon.xyz = xpp_gon_xyz
    xpp_gon.sam = xpp_gon_sam
    xpp_gon.kappa = xpp_gon_kappa

# create GON aliases
with safe_load('gon and kappa'):
    class gon():
        h = xpp_gon.hor
        v = xpp_gon.ver
        r = xpp_gon.rot
        roll = xpp_gon.tip
        pitch = xpp_gon.tilt
        x = xpp_gon.xyz.x
        y = xpp_gon.xyz.y
        z = xpp_gon.xyz.z
        sam_z = xpp_gon_sam.sam_z
        sam_phi = xpp_gon_sam.sam_phi	
#    class kappa():
#        eta=xpp_gon_kappa.eta
#        kappa=xpp_gon_kappa.kappa
#        phi=xpp_gon_kappa.phi
#        x = xpp_gon_kappa.x
#        y = xpp_gon_kappa.y
#        z = xpp_gon_kappa.z

with safe_load('Roving Spectrometer'):
    from ophyd.device import Device, Component as Cpt
    from pcdsdevices.epics_motor import BeckhoffAxis
    from pcdsdevices.interface import BaseInterface

    class RovingSpec(BaseInterface, Device):
        h = Cpt(BeckhoffAxis, ':ALL_H', name='all_h')
        v = Cpt(BeckhoffAxis, ':ALL_V', name='all_v')
        th = Cpt(BeckhoffAxis, ':XTAL_TH', name='xtal_th')
        tth = Cpt(BeckhoffAxis, ':XTAL_TTH', name='xtal_tth')
        xh = Cpt(BeckhoffAxis, ':XTAL_H', name='xtal_h')
        xv = Cpt(BeckhoffAxis, ':XTAL_V', name='xtal_v')
        dh = Cpt(BeckhoffAxis, ':DET_H', name='det_h')
        dv = Cpt(BeckhoffAxis, ':DET_V', name='det_v')
    rov_spec = RovingSpec('HXX:HXSS:ROV:MMS', name='rov_spec')
    RSpec=RovingSpec

with safe_load('Noplot ascan'):
    from xpp.db import RE, daq, bp    
    def run_ascan_daq_noplot(mot, a, b, points, events_per_point, use_l3t=False):
        if RE.state != 'idle':
            RE.abort()
        daq.configure(events=events_per_point, use_l3t=use_l3t, controls=[mot])
        RE(bp.scan([daq], mot, a, b, points))


with safe_load('FS11 lxt & lxt_ttc'):
    import logging
    logging.getLogger('pint').setLevel(logging.ERROR)

    ###from pcdsdevices.lxe import LaserTimingCompensation

    ###lxt_ttc = LaserTimingCompensation('', delay_prefix='XPP:LAS:MMN:16', laser_prefix='LAS:FS11', name='lxt_ttc')
    ###lxt_ttc.delay.n_bounces = 14

    ###lxt = lxt_ttc.laser
    ##from ophyd.device import Component as Cpt

    ##from pcdsdevices.epics_motor import Newport
    ##from pcdsdevices.lxe import LaserTiming
    ##from pcdsdevices.pseudopos import DelayMotor, SyncAxis, delay_class_factory

    ##DelayNewport = delay_class_factory(Newport)

    ### Reconfigurable lxt_ttc
    ### Any motor added in here will be moved in the group
    ##class LXTTTC(SyncAxis):
    ##    lxt = Cpt(LaserTiming, 'LAS:FS11', name='lxt')
    ##    txt = Cpt(DelayNewport, 'XPP:LAS:MMN:16',
    ##              n_bounces=14, name='txt')

    ##    tab_component_names = True
    ##    scales = {'txt': -1}
    ##    warn_deadband = 5e-14
    ##    fix_sync_keep_still = 'lxt'
    ##    sync_limits = (-10e-6, 10e-6)

    ##lxt_ttc = LXTTTC('', name='lxt_ttc')
    ##lxt = lxt_ttc.lxt

    from pcdsdevices.device import ObjectComponent as OCpt
    from pcdsdevices.lxe import LaserTiming
    from pcdsdevices.pseudopos import SyncAxis
    from xpp.db import xpp_txt

    lxt = LaserTiming('LAS:FS11', name='lxt')
    xpp_txt.name = 'txt'

    class LXTTTC(SyncAxis):
        lxt = OCpt(lxt)
        txt = OCpt(xpp_txt)

        tab_component_names = True
        scales = {'txt': -1}
        warn_deadband = 5e-14
        fix_sync_keep_still = 'lxt'
        sync_limits = (-10e-6, 10e-6)


    lxt_ttc = LXTTTC('', name='lxt_ttc')

#    # test to have the LV09 800nm and THz newport stage 
#    #form a 'pair' to scan synchronously.
#    class THz800Delay(SyncAxis):
#        thz_delay=Cpt(DelayNewport, 'XPP:USR:MMN:05', n_bounces=2,name='thz_delay')
#        lxt_fast=Cpt(DelayNewport, 'XPP:LAS:MMN:04', n_bounces=2,name='lxt_fast')
#
#        tab_component_names = True
#        warn_deadband = 5e-14
#        fix_sync_keep_still = 'lxt_fast'
#        scales = {'thz_delay': -1}
#        sync_limits = (-1e-9, 1e-9)
#
#    lxt_8ts = THz800Delay('', name='lxt_8ts')


# delay scan related scan plans and USB encoder object
with safe_load('Delay Scan'):
    from nabs.plans import delay_scan, daq_delay_scan
    from pcdsdevices.interface import BaseInterface
    from ophyd.device import Device
    from ophyd.signal import EpicsSignal
     
    class USBEncoder(BaseInterface, Device):
        tab_whitelist = ['pos', 'set_zero', 'scale', 'offset']
        zero = Cpt(EpicsSignal, ':ZEROCNT', kind='omitted')
        pos = Cpt(EpicsSignal, ':POSITION', kind='hinted')
        scale = Cpt(EpicsSignal, ':SCALE', kind='config')
        offset = Cpt(EpicsSignal, ':OFFSET', kind='config')
        def set_zero(self):
            self.zero.put(1)
    lxt_fast_enc = USBEncoder('XPP:GON:USDUSB4:01:CH0', name='lxt_fast_enc')

#Laser setup: standard XPP shutters.
with safe_load('Laser Shutters - cp&lp'):
    cp = LaserShutter('XPP:USR:ao1:15', name='cp')
    lp = LaserShutter('XPP:USR:ao1:14', name='lp')

    def lp_close():
        lp('IN')
    def lp_open():
        lp('OUT')
    def cp_close():
        cp('IN')
    def cp_open():
        cp('OUT')

## creating some aliases for less typing and easier lookups ##

with safe_load('Create Aliases'):
    from xpp.db import at1l0 as fat1
    from xpp.db import at2l0 as fat2

    from xpp.db import hx2_pim as  yag1
    from xpp.db import xpp_sb3_pim as yag2

    from xpp.db import hx2_ipm as ipm1
    from xpp.db import xpp_sb2_ipm as ipm2
    from xpp.db import xpp_sb3_ipm as ipm3

    from xpp.db import hx2_slits as s1
    from xpp.db import xpp_sb2_low_slits as s2
    from xpp.db import xpp_sb2_high_slits as s3
    from xpp.db import xpp_sb3_slits as s4

    from xpp.db import xpp_pulsepicker as pp
    from xpp.db import xpp_attenuator as att
    #from xpp.db import xpp_gon as gon
    #from xpp.db import xpp_lodcm as lom

    from xpp.db import xpp_txt as txt
    from xpp.db import xpp_lxt_fast as lxt_fast
    from xpp.db import xpp_lens_h as lens_h
    from xpp.db import xpp_lens_v as lens_v
    from xpp.db import xpp_lens_f as lens_f
    #from xpp.db import xpp_pol_wp as pol_wp # disconnected
    from xpp.db import xpp_com_wp as com_wp
    from xpp.db import xpp_opa_wp as opa_wp

with safe_load('add pp motors'):
    pp.x = IMS('XPP:SB2:MMS:28', name='pp_x')
    pp.y = IMS('XPP:SB2:MMS:16', name='pp_y')

with safe_load('add crl motors'):
    class crl():
        x = IMS('XPP:SB2:MMS:13', name='crl_x')
        y = IMS('XPP:SB2:MMS:14', name='crl_y')
        z = IMS('XPP:SB2:MMS:15', name='crl_z')

with safe_load('add laser motor groups'):
    class las():
        com_wp=com_wp # waveplate for the main compressor
        #pol_wp=pol_wp # disconnected, used to be the other waveplate
        opa_wp=opa_wp # for adjusting OPA output polarization
        opa_comp = Newport('XPP:LAS:MMN:10', name='opa_comp') # linear motor for OPA compressor
        lens_h=lens_h # main pump beam lens horizontal motion
        lens_v=lens_v # main pump beam lens vertical motion
        lens_f=lens_f # main pump beam lens travel along the beam
        delayFast = Newport('XPP:LAS:MMN:04', name='delayFast')
        
        # Time tool motors
        with safe_load('add tt motors'):
            tt_comp = Newport('XPP:LAS:MMN:12', name='tt_comp') # compressor for time tool
            tt_wp = Newport('XPP:LAS:MMN:11', name='tt_wp') # waveplate for TT
            delayTT = Newport('XPP:LAS:MMN:16', name='delayTT') # delay stage for time tool
            tt_y=IMS('XPP:SB2:MMS:31', name='tt_y') # time tool target insertion

        # reference laser steering motors
        with safe_load('add reference laser steering motors'):
            rlx = Newport('XPP:LAS:MMN:22', name='rlx')
            rldx = Newport('XPP:LAS:MMN:21', name='rldx')
            tt_v = Newport('XPP:LAS:MMN:23', name='tt_v')
            rly = tt_v
            rldy = Newport('XPP:LAS:MMN:24', name='rldy')
        
        # timing virtual motors for x-ray laser delay adjustment
        lxt=lxt
        txt=txt
        lxt_ttc=lxt_ttc
        lxt_fast=lxt_fast

with safe_load('create cryo scattering chamber object group'):
    class csc():
        th = IMS('XPP:USR:MMS:23', name='th')
        x = IMS('XPP:USR:MMS:22', name='x')
        y = IMS('XPP:USR:MMS:21', name='y')
        z = IMS('XPP:USR:MMS:20', name='z')
        rz = IMS('XPP:USR:MMS:24', name='rz')
        rx = IMS('XPP:USR:MMS:25', name='rx')
        pmx = IMS('XPP:USR:MMS:19', name='pmx')
        pmy = IMS('XPP:USR:MMS:17', name='pmy')
        pmz = IMS('XPP:USR:MMS:18', name='pmz')
        dx1 = IMS('XPP:USR:MMS:26', name='dx1')
        dx2 = PMC100('XPP:CRYO:MZM:01', name='dx2')
        dx3 = PMC100('XPP:CRYO:MZM:02', name='dx3')
        dz = PMC100('XPP:CRYO:MZM:03', name='dz')


#from pcdsdevices.attenuator import FeeAtt
#from pcdsdevices.attenuator import FEESolidAttenuator
#with safe_load('fee attenuators alias'):
#    fat1=FeeAtt()
#    fat2=FEESolidAttenuator()

with safe_load('enable scan table scientific notation'):
    from bluesky.callbacks.core import LiveTable
    LiveTable._FMT_MAP['number'] = 'g'


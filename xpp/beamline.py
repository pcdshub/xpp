from hutch_python.utils import safe_load
from pcdsdevices.device_types import Newport, PMC100, IMS, BeckhoffAxis
from xpp.delay_stage import FakeDelay
from xpp.db import scan_pvs
from pcdsdevices.lasers.shutters import LaserShutter
from pcdsdevices.lasers.shutters import LaserFlipper
from ophyd.sim import motor as fake_motor
from pcdsdevices.epics_motor import SmarAct, EpicsMotorInterface


scan_pvs.enable()

#with safe_load('Syringe_Pump'):
    #from xpp.devices import Syringe_PumpS
    #syringe_pump=Syringe_Pump()

with safe_load('pyami detectors'):
    from xpp.ami_detectors import *

# XPP has been assigned event sequencer 3 and 10. We largely use 10 for the laser dropped shots
# and 3 for pulse picker + other actions.
with safe_load('Event Sequencers'):
    from pcdsdevices.sequencer import EventSequencer
    seq = EventSequencer('ECS:SYS0:3', name='seq')
    seq2 = EventSequencer('ECS:SYS0:10', name='seq2')

# K monochromator in the FEE
with safe_load('K mono'):
    kmono_th = BeckhoffAxis('SP1L0:KMONO:MMS:XTAL_ANGLE', name='kmono_th')
    kmono_y = BeckhoffAxis('SP1L0:KMONO:MMS:XTAL_VERT.RBV', name='kmono_y')

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
                          prefix_phi = 'XPP:GON:MMS:11')
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
    from pcdsdevices.epics_motor import BeckhoffAxis as BeckhoffAxisOld
    from pcdsdevices.epics_motor import BeckhoffAxisPLC as BeckhoffAxisPLCOld
    from pcdsdevices.interface import BaseInterface

    class BeckhoffAxisPLC(BeckhoffAxisPLCOld):
        cmd_home = None

    class BeckhoffAxis(BeckhoffAxisOld):
        plc = Cpt(BeckhoffAxisPLC, ':PLC:', kind='normal',
              doc='PLC error handling.')


with safe_load('Noplot ascan'):
    from xpp.db import RE, daq, bp    
    def run_ascan_daq_noplot(mot, a, b, points, events_per_point, use_l3t=False):
        if RE.state != 'idle':
            RE.abort()
        daq.configure(events=events_per_point, use_l3t=use_l3t, controls=[mot])
        RE(bp.scan([daq], mot, a, b, points))

with safe_load('Mode change'):
    class bl():
        def mode_pink():
            ccm.remove()
            s2.vo.umv(0)
            print("s2 is moving to 0")
            s3.vo.umv(0)
            print("s3 is moving to 0")
            s4.vo.umv(0)
            print("s4 is moving to 0")
            ipm2.target(1)
            ipm3.target(1)
            ipm2.dy(0)
            print("ipm2 diode is moving to 0")
            ipm3.dy(0)
            print("ipm3 diode is moving to 0")
            tt_y.umv_YAG20um()
            print('Timetool target is now "20 um YAG" and CRL has not moved yet')
        def mode_ccm():
            ccm.insert()
            s2.vo.umv(7.5)
            print("s2 is moving to 0")
            s3.vo.umv(7.5)
            print("s3 is moving to 0")
            s4.vo.umv(7.5)
            print("s4 is moving to 0")
            ipm2.target(1)
            ipm2.ty.umvr(7.5)
            ipm3.target(1)
            ipm3.ty.umvr(7.5)
            ipm2.dy.umv(7.5)
            print("ipm2 diode is moving to 0")
            ipm3.dy.umv(7.5)
            print("ipm3 diode is moving to 0")
            tt_y.umv_YAG20um_CCM()
            print('Timetool target is now "20 um YAG ccm" and CRL has not moved yet')

with safe_load('FS11 & FS14 lxt & lxt_ttc'):
    import logging
    logging.getLogger('pint').setLevel(logging.ERROR)

    from pcdsdevices.device import ObjectComponent as OCpt
    from pcdsdevices.lxe import LaserTiming
    from pcdsdevices.pseudopos import SyncAxis
    from xpp.db import xpp_txt

    lxt_FS11 = LaserTiming('LAS:FS11', name='lxt')
    lxt_FS14 = LaserTiming('LAS:FS14', name='lxt')
    xpp_txt.name = 'txt'
    
    # pick which is the default
    #lxt = lxt_FS11
    lxt = lxt_FS14

    class LXTTTC(SyncAxis):
        lxt = OCpt(lxt)
        txt = OCpt(xpp_txt)

        tab_component_names = True
        scales = {'txt': -1}
        warn_deadband = 5e-14
        fix_sync_keep_still = 'lxt'
        sync_limits = (-10e-6, 10e-6)

    lxt_ttc = LXTTTC('', name='lxt_ttc')
    


# delay scan related scan plans and USB encoder object
with safe_load('Delay Scan'):
    from nabs.plans import delay_scan, daq_delay_scan
    from pcdsdevices.interface import BaseInterface
    from ophyd.device import Device
    from ophyd.signal import EpicsSignal
     

#Laser setup: standard XPP shutters.
with safe_load('Laser Shutters - cp, lp & ep'):
    cp = LaserShutter('XPP:USR:ao1:15', name='cp')
    lp = LaserShutter('XPP:USR:ao1:14', name='lp')
    ep = LaserShutter('XPP:USR:ao1:13', name='ep')
    vp = LaserFlipper('XPP:USR:ao1:12', name='vp')
    opa = LaserFlipper('XPP:USR:ao1:11', name='opa')
    def lp_close():
        lp('IN')
    def lp_open():
        lp('OUT')
    def cp_close():
        cp('IN')
    def cp_open():
        cp('OUT')
    def ep_open():
        ep('OUT')
    def ep_close():
        ep('IN')
    def vp_open():### To sample
        vp('OUT')
    def vp_close():### virual plane with the flipper mirror 
        vp('IN')
    def opa_open():### To sample
        opa('OUT')
    def opa_close():### virtutal plane with the flipper mirror 
        opa('IN')

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
    from xpp.db import xpp_lodcm as lom
    from xpp.db import xpp_ccm as ccm

    yag1.state.in_states = ['YAG', 'DIODE']
    yag2.state.in_states = ['YAG', 'DIODE']


with safe_load('add pp motors'):
    pp.x = EpicsMotorInterface('XPP:SB2:MMS:28', name='pp_x')
    pp.y = EpicsMotorInterface('XPP:SB2:MMS:16', name='pp_y')

with safe_load('add crl motors'):
    class crl():
        x = IMS('XPP:SB2:MMS:13', name='crl_x')
        y = IMS('XPP:SB2:MMS:14', name='crl_y')
        z = IMS('XPP:SB2:MMS:15', name='crl_z')


class LIB_SmarAct(BaseInterface, Device):
    tab_component_names = True
    mirr_x = Cpt(SmarAct, ':01:m1', kind='normal')
    mirr_y = Cpt(SmarAct, ':01:m2', kind='normal')
    mirr_dy = Cpt(SmarAct, ':01:m3', kind='normal')
    mirr_dx = Cpt(SmarAct, ':01:m4', kind='normal')
    mono_th = Cpt(SmarAct, ':01:m5', kind='normal')
    mono_x = Cpt(SmarAct, ':01:m6', kind='normal')

class lu():#lib unit
    tab_component_names = True
    with safe_load('LIB SmarAct'):
        lib = LIB_SmarAct('XPP:MCS2', name='lib_smaract')


    

with safe_load('add laser motor groups'):
    import numpy as np
    import json
    import sys
    import time
    from pcdsdevices.usb_encoder import UsDigitalUsbEncoder
    from xpp.db import xpp_txt
    from xpp.db import xpp_lxt_fast1, xpp_lxt_fast2
    from xpp.db import xpp_lens_h, xpp_lens_v, xpp_lens_f
    #from xpp.db import xpp_pol_wp as pol_wp # disconnected
    from xpp.db import xpp_com_wp, xpp_opa_wp

    class las():
        com_wp = xpp_com_wp # waveplate for the main compressor
        #pol_wp=pol_wp # disconnected, used to be the other waveplate
        opa_wp = xpp_opa_wp # for adjusting OPA output polarization
        opa_nd = Newport('XPP:LAS:MMN:09', name='opa_nd')
        opa_comp = Newport('XPP:LAS:MMN:10', name='opa_comp') # linear motor for OPA compressor
        pump_wp = Newport('XPP:USR:MMN:32', name='pump_wp')
        lens_h = xpp_lens_h # main pump beam lens horizontal motion
        lens_v = xpp_lens_v # main pump beam lens vertical motion
        lens_f = xpp_lens_f # main pump beam lens travel along the beam
        delayFast1 = Newport('XPP:LAS:MMN:02', name='delayFast1')
        delayFast2 = Newport('XPP:LAS:MMN:01', name='delayFast2')
         
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

        with safe_load('Fast delay encoders'):
            lxt_fast1_enc = UsDigitalUsbEncoder('XPP:GON:USDUSB4:01:CH0', name='lxt_fast_enc1', linked_axis=xpp_lxt_fast1)
            lxt_fast2_enc = UsDigitalUsbEncoder('XPP:GON:USDUSB4:01:CH1', name='lxt_fast_enc2', linked_axis=xpp_lxt_fast2)
        
        # timing virtual motors for x-ray laser delay adjustment
        lxt = lxt
        txt = xpp_txt
        lxt_ttc = lxt_ttc
        lxt_fast1 = xpp_lxt_fast1
        lxt_fast2 = xpp_lxt_fast2

        def tt_rough_FB(
            ttamp_th = 0.04, 
            ipm2_th = 2000, 
            ttfwhmhigh = 220,
            ttfwhmlow = 100,
            kp = 0.2,
            ki = 0.1,
            kd = 1
        ): #ttamp:timetool signal amplitude threshold, imp2 I0 value threshold, tt_window signal width
            fbvalue = 0 # for drift record
            ave_tt = np.zeros([2,])
            while(las.get_matlabPV_stat() == 0):
                print('\033[1;31m' +  "Please Turn On -----FS Timing Correction-----" + '\033[0m')
                time.sleep(0.5)
            while(1):
                tenshots_tt = np.zeros([1,])#for tt 
                dlen = 0#number of "good shots" for feedback
                pt = 0#time to get the good singal for PI"D"
                while(dlen < 121):
                    current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()
                    if(dlen%60 == 0):
                        #print("tt_value",current_tt,"ttamp",ttamp,"ipm2",ipm2val, dlen)
                        print("tt_value:%0.3f" %current_tt + "   ttamp:%0.3f " %ttamp +"   ipm2:%d" %ipm2val,"   good shot: %d" %dlen)
                    if (ttamp > ttamp_th)and(ipm2val > ipm2_th)and(ttfwhm < ttfwhmhigh)and(ttfwhm >  ttfwhmlow)and(current_tt != tenshots_tt[-1,])and(las.txt.moving == False):# for filtering the last one is for when DAQ is stopping
                        tenshots_tt = np.insert(tenshots_tt,dlen,current_tt)
                        dlen = np.shape(tenshots_tt)[0]
                    pt = pt + 1 
                    time.sleep(0.01)
                tenshots_tt = np.delete(tenshots_tt,0)
                ave_tt[1,] = ave_tt[0,]
                ave_tt[0,] = np.mean(tenshots_tt)
                print("Moving average of timetool value:", ave_tt)
                fb_val = las.pid_control(kp,ki,kd,ave_tt,pt)#calculate the feedback value
                if(round(lxt(),13)==-(round(las.txt(),13)) and (las.txt.moving == False)):#check not lxt or during motion of lxt_ttc and the feedback works only when lxt = -txt (lxt_ttc is ok)
                    ave_tt_second=-((fb_val)*1e-12)
                    las.matlabPV_FB(ave_tt_second)
                    print('\033[1;31m' +  "feedback %f ps"%fb_val + '\033[0m')
                    #fbvalue = ave_tt + fbvalue# for record
                    #drift_log(str(fbvalue))# for record
            return
        
        def pid_control(kp,ki,kd,ave_data,faketime):
            fd_value = kp*ave_data[0,] + ki*(np.sum(ave_data[:,]))+kd*((ave_data[1,]-ave_data[0,])/faketime)
            return fd_value

        def matlabPV_FB(feedbackvalue):#get and put timedelay signal
            #matPV = EpicsSignal('LAS:FS11:VIT:matlab:04')#for bay 1 laser
            matPV = EpicsSignal('LAS:FS14:VIT:matlab:04')#for bay 4 laser
            org_matPV = matPV.get()#the matlab PV value before FB
            fbvalns = feedbackvalue * 1e+9#feedback value in ns
            fbinput = org_matPV + fbvalns#relative to absolute value
            matPV.put(fbinput)
            return
        
        def get_ttall():#get timetool related signal
            #ttall = EpicsSignal('XPP:TIMETOOL:TTALL') #old TT PV
            ttall = EpicsSignal('XPP:TT:01:TTALL')
            ttdata = ttall.get()
            current_tt = ttdata[1,]
            ttamp = ttdata[2,]
            ipm2val = ttdata[3,]
            ttfwhm = ttdata[5,]
            ttintg = ttdata[6,]
            return current_tt, ttamp, ipm2val, ttfwhm, ttintg
        def get_correlation(numshots):##get timetool correlation from Event builder
            ttdataall = np.zeros([numshots,])
            ipm2values = np.zeros([numshots,])
            ii = 0
            while (ii < numshots):
                ttall = EpicsSignal('XPP:TT:01:EVENTBUILD.VALA')
                ttdata = ttall.get()
                ttamp = ttdata[2,]
                ipm2val = ttdata[1,]
                ttfwhm = ttdata[5,]
                ttintg = ttdata[11,]
                if(ipm2val > 200): 
                    ttdataall[ii,] = ttintg
                    ipm2values[ii,] = ipm2val
                    ii = ii + 1
                time.sleep(0.008)
            #print(ttdata,ipm2values)
            ttipmcorr = np.corrcoef(ttdataall,ipm2values) 
            return ttipmcorr[0,1]
        def get_matlabPV_stat():#get timetool related signal
            #mp_stat = EpicsSignal('LAS:FS11:VIT:TT_DRIFT_ENABLE')# for bay 1
            mp_stat = EpicsSignal('LAS:FS14:VIT:TT_DRIFT_ENABLE')
   
            mp_stat = mp_stat.get()
            return mp_stat

        def get_avettroi(numofshots):
            ii = 0
            while (ii < numshots):
                ttall = EpicsSignal('XPP:TT:01:EVENTBUILD.VALA')
                ttdata = ttall.get()
                ttamp = ttdata[2,]
                ipm2val = ttdata[1,]
                ttfwhm = ttdata[5,]
                ttintg = ttdata[11,]
                if(ipm2val > 200): 
                    ttdataall[ii,] = ttintg
                    ipm2values[ii,] = ipm2val
                    ii = ii + 1
                time.sleep(0.008)
            ttroi = np.mean(ttdataall)# average white ROI signal with X-rays
            return ttroi
        def tt_sigcount(numshots):#check the timetool signal quality
            for ii in range(numshots):
                current_tt, ttamp, ipm2val, ttfwhm,ttintg = las.get_ttall()#get 240 shots to find timetool signal
                if (ttamp > 0.03)and(ttfwhm < 130)and(ttfwhm >  70)and(ttamp<2):
                    ttdata[ii,] = ttamp
                    time.sleep(0.008)
                print(ttdata)
                if np.count_nonzero(ttdata[:,]) > 30:#1/4 shots have timetool signal
                    print("Found timetool signal and set current lxt to 0")
                    print(f"we will reset the current {lxt()} position to 0")
                    return 1
                else:
                    return 0
        
        def s3_status():
            s3stat = EpicsSignal('PPS:NEH1:1:S3INSUM')
            s3stat = s3stat.get()
            return s3stat# 0 is out, 4 is IN                  
        def timing_check():
            #tttime = EpicsSignal('LAS:FS11:VIT:FS_TGT_TIME')#target time for bay 1
            #tttact = EpicsSignal('LAS:FS11:VIT:FS_CTR_TIME')#actual control time for bay 1
            #tttphase = EpicsSignal('LAS:FS11:VIT:PHASE_LOCKED')#phase for bay 1
            tttime = EpicsSignal('LAS:FS14:VIT:FS_TGT_TIME')#target time for bay4
            tttact = EpicsSignal('LAS:FS14:VIT:FS_CTR_TIME')#actual control time for bay 4
            tttphase = EpicsSignal('LAS:FS14:VIT:PHASE_LOCKED')#phase for bay 4
            if(round(tttime.get(),1)==round(tttact.get(),1) and (tttphase.get() == 1)):
                return 1 ## lxt is ok for the target position
            elif(round(tttime.get(),1)!=round(tttact.get(),1) or (tttphase.get() != 1)):
                return 0

        def tt_recover(scanrange = 5e-12,stepsize = -0.5e-12,direction = "p",testshot = 240):#For tt_signal recover in 10 ps
            las.tt_y.umv(54.67)#LuAG to find tt signal
            originaldelay = lxt()
            if direction == "n":
                print("Search tt signal from positive to negative")
                lxt.mvr(scanrange)
                time.sleep(0.5)
            elif direction == "p":
                lxt.mvr(-1*scanrange)
                print("Search tt signal from negative to positive")
                stepsize = -1 * stepsize
                time.sleep(0.5)
            j = 0
            while(abs(stepsize * j) < abs(scanrange * 2) ):
                ttdata = np.zeros([testshot,])
                ii = 0
                for ii in range(testshot):
                    current_tt, ttamp, ipm2val, ttfwhm,ttintg = las.get_ttall()#get 240 shots to find timetool signal
                    if (ttamp > 0.03)and(ttfwhm < 130)and(ttfwhm >  70)and(ttamp<2):
                        ttdata[ii,] = ttamp
                    time.sleep(0.008)
                print(ttdata)
                if np.count_nonzero(ttdata[:,]) > 30:#1/4 shots have timetool signal
                    print("Found timetool signal and set current lxt to 0")
                    print(f"we will reset the current {lxt()} position to 0")
                    lxt.set_current_position(0)
                    las.tt_y.umv(67.1777)#Switch to YAG
                    print("Please run las.tt_rough_FB()")
                    ttfb = input("Turn on feedback? yes(y) or No 'any other' ")
                    if ((ttfb == "yes") or (ttfb == "y")):
                        print("feedback on")
                        las.tt_rough_FB(kp= 0.2,ki=0.1)
                    else:
                        print("No feedback yet")
                    return
                else:
                    lxt.umvr(stepsize)
                    time.sleep(0.5)
                    print(f"searching timetool signal {lxt()}")
                j = j + 1          
            print("The script cannot find the timetool signal in this range. Try las.autott_find()")        
          
        
            return
##################################################################################################################
        def tt_find(ini_delay = 10e-9):# old manual version to find tt signal the ini_delay is now input argument
            if lxt() != 0:
                print('\033[1m'+ "Set current position to 0 to search" + '\033[0m') 
                return
            elif lxt() ==0:
                las.tt_y.umv(54.67)#LuAG to find tt signal
                delayinput = ini_delay#Search window
                i = 0#iteration time
                while(1):#20ns search until finding the correlation switched
                    print('\033[1m'+ "Can you see 'The positive correlation(p)' or 'The negative correlation(n)?' p/n or quit this script q"+'\033[0m')
                    bs = input()#input the current correlation
                    if i == 0:# for the initialization
                        prebs = bs

                    if (i < 10)and(prebs == bs):#First search in 100 ns. 100 ns is too large. If cannot find in 10 iteration need to check the other side
                        if bs == "p":
                            delayttdic[ipm2sig.timestamp] = ipm2sig.valueinput = -1 * abs(delayinput)
                            lxt.mvr(delayinput)
                            i = i + 1
                            print(f"Searching the negative correlation with 10ns. Number of iteration:{i}")
                        elif bs == "n":#find non-correlation
                            delayinput = abs(delayinput)
                            lxt.mvr(delayinput)
                            i = i + 1
                            print(f"Searching the positive or no correlation with 10ns. Number of iteration:{i}")
                        elif bs == "q":
                            print("Quit")
                            return
                        else:
                            print('\033[1m'+"Can you see 'The positive correlation(p)'or'The negative correlation(n)?' p/n or quit this script q" + '\033[0m')
                    elif (prebs != bs):
                        print('\033[1m'+"Switch to binary search"+'\033[0m')
                        break
                    prebs = bs#the correlation change?
                  
##########################binary search part######################
                while(abs(delayinput) > 0.5e-12):#binary search from 10ns to 0.5ps
                    print('\033[1;32m'+"Can you see\n"+'The positive correlation(p)\n' + '\033[1;35m' + 'The negative correlation(n)?\n' + '\033[1;35m' +'(press p(ositive)/n(egative)),\n' + '\033[1;31m' +  "Find signal? or quit this script q(uit)\n" + '\033[1;34m' + 'Repeat the current step size (r)\n'+ 'Back onestep (b)' + '\033[0m')
                    bs = input()
                    if bs == "p":
                        delayinput = -1 * abs(delayinput)
                        lxt.mvr(delayinput)
                        print(f"Timewindow: {delayinput}")
                        delayinput = delayinput/2
                        i = i + 1
                        prebs = "p"
                        print(f"Number of iteration:{i}")
                        
                    elif bs == "n":
                        delayinput = abs(delayinput)
                        lxt.mvr(delayinput)
                        print(f"Timewindow: {delayinput}")
                        delayinput = delayinput/2
                        i = i + 1
                        prebs = "n"
                        print(f"Number of iteration:{i}")
                        
                    elif bs == "q":
                        print("Quit")
                        return
                    elif bs == "b":#back to previous position if making mistake 
                        if prebs == "n":
                            delayinput = -1 * abs(delayinput)*2#2 times since the previous step divde the input after the motion
                            lxt.mvr(delayinput)
                        elif prebs == "p":
                            delayinput = abs(delayinput)*2#2 times since the previous step divde the input after the motion
                            lxt.mvr(delayinput)
                    elif bs == "r":#Repeat to move the delay same amount with the previous step
                        if prebs == "n":
                            delayinput = 1 * abs(delayinput)*2
                            lxt.mvr(delayinput)
                            delayinput = delayinput/2
                            prebs == "n"
                        elif prebs == "p":
                            delayinput = -abs(delayinput)*2
                            lxt.mvr(delayinput)
                            delayinput = delayinput/2
                            prebs == "p"
                    else:
                        print('\033[1;32m'+"Can you see\n"+'The positive correlation(p)\n' + '\033[1;35m' + 'The negative correlation(n)?\n' + '\033[1;35m' +'(press p(ositive)/n(egative)),\n' + '\033[1;31m' +  "Find signal? or quit this script q(uit)\n" + '\033[1;34m' + 'Repeat the current step size (r)\n'+ 'Back onestep (b)' + '\033[0m')
                  
                ttdata = np.zeros([240,])#timetool signal search at the initial position
                for ii in range(240):
                    current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()
                    if (ttamp > 0.03)and(ttfwhm < 130)and(ttfwhm >  70)and(ttamp < 2):
                        ttdata[ii,] = ttamp
                    time.sleep(0.008)
                print(ttdata)
                if np.count_nonzero(ttdata[:,]) > 30:#If we have timetool signal more than 1/4 of 120 shots, this script is stopped
                    print("Found timetool signal and set current lxt to 0")
                    print(f"we will reset the current {lxt()} position to 0")
                    lxt.set_current_position(0)
                    las.tt_y.umv(67.1777)#Switch to YAG
                    ttfb = input("Turn on feedback? yes(y)")
                    if ((ttfb == "yes") or (ttfb == "y")):
                        print("feedback on")
                        las.tt_rough_FB(kp= 0.2,ki=0.1)
                    else:
                        print("No feedback yet")

                    return
                else: #scan from -1.0 to 1.0 ps to find timetool signal around here until finding timetool signal
                    lxt.mvr(-2.0e-12)
                    time.sleep(0.5)
                    jj = 0        
                    while(jj < 5):
                        ttdata = np.zeros([240,])
                        ii = 0
                        for ii in range(240):
                            current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()#scan from -1.5 to 1.5 ps to find timetool signal
                            if (ttamp > 0.03)and(ttfwhm < 130)and(ttfwhm >  70)and(ttamp<2):
                                ttdata[ii,] = ttamp
                            time.sleep(0.008)
                        print(ttdata)
                        if np.count_nonzero(ttdata[:,]) > 30:
                            break
                        else:
                            lxt.mvr(0.5e-12)
                            time.sleep(0.5)
                            jj = jj + 1
                            print(f"searching timetool signal {lxt()}")
                            if jj == 5:
                                print("No timetool signal. Something wrong....")  
                                return
                    
                print("Found timetool signal and set current lxt to 0")
                print(f"we will reset the current {lxt()} position to 0")
                lxt.set_current_position(0)
                las.tt_y.umv(67.1777)#Switch to YAG
                print("Please run las.tt_rough_FB()")
                ttfb = input("Turn on feedback? yes(y)")
                if ((ttfb == "yes") or (ttfb == "y")):
                    print("feedback on")
                    las.tt_rough_FB(kp= 0.2,ki=0.1)
                else:
                    print("No feedback yet")
            return


        def autott_find(ini_delay = 50e-9, testshot = 360, ttsiglevel = -0.2, calic = 1.1, inisearch = 25, lxttimeout = 4):
        #"""
        #tt signal find tool the ini_delay is now input argument maybe for pink beam, lxttimeout the time to wait for lxt motion, test shot: 
        #number of shots to accumulate for getting correlation, initial delay the step size of the initial large search. 
        #inisearch: scan range  for the initial big step search, 
        #ttsiglevel: correlation coeffcient. 
        #If there is correlation, typically the signal level is -0.9, which is relatively large so you don't need to care the signal level. 
        #"""
            if lxt() != 0:
                print('\033[1m'+ "Set current position to 0 to search" + '\033[0m') 
                return
            elif lxt() ==0:
                las.tt_y.umv(54.67)#LuAG to find tt signal
                delayinput = ini_delay#Search window
                i = 0#iteration time
                print('\033[1m'+ "Checking white light Bg level"+'\033[0m')
                #lom.yag.insert()#insert the YAG to block X-rays before the timetool target
                #while(lom.yag.inserted == False ):
                #    time.sleep(1)
                #    print('Waiting for YAG getting in')
                ttdata = np.zeros([testshot,])
                ii = 0
                print("Getting the white light Bg level")
                
               

                #######Finding the initial correlation switching point####################

            
                print('\033[1m'+ "Searching the correlation switch point first"+'\033[0m')
                ttcorr = las.get_correlation(testshot)
                    #print(ii)
                
                print(ttcorr)
          
                while(1):#20ns search until finding the correlation switched
                    bs = (ttcorr < ttsiglevel)  #input the current correlation
                    print(i)
                    if i == 0:# for the initialization
                        prebs = bs
                       
                       
                    if ((i < inisearch)and(prebs == bs)):
                    #First search in 100 ns. 100 ns is too large. 
                    #If cannot find in 10 iteration need to check the other side
                        print(bs)
                        if bs == False:
                            delayinput = -1 * abs(delayinput)
                            lxt.mvr(delayinput)
                            while(lxt.moving == True):
                                time.sleep(0.01)
                            i = i + 1
                          
                            #time.sleep(lxttimeout)
                            print(f"Searching the negative correlation with 10ns. Number of iteration:{i}")
                        elif bs == True:#find non-correlation
                            delayinput = abs(delayinput)
                            lxt.mvr(delayinput)
                            while(lxt.moving == True):
                                time.sleep(0.01)
                            i = i + 1
                            #time.sleep(lxttimeout)
                            print(f"Searching the positive or no correlation with 10ns. Number of iteration:{i}")
                        while(las.timing_check() != 1):### waiting for the lxt motion compledted
                            time.sleep(0.1)
                        time.sleep(0.1)
                        ttcorr = las.get_correlation(testshot)
                        bs = (ttcorr < ttsiglevel) #input the current correlation
                        #print(bs,(ttcorr-ttsiglevel))
                    elif( i >= inisearch)and(prebs == bs):
                        print('\033[1m'+"the tt signal is far from 500 ns range, please search 100 ns range"+'\033[0m')  
                        return
                    elif(prebs != bs):
                        print('\033[1m'+"Switch to binary search"+'\033[0m')
                        break
                    #the correlation change?
                  
##########################binary search part######################
                while(abs(delayinput) > 1.0e-12):#binary search from 10ns to 5ps
                    print('\033[1m'+"Binary search"+'\033[0m')
                    time.sleep(0.1)
                    ttcorr = las.get_correlation(testshot)
                    bs = (ttcorr < ttsiglevel) #input the current correlation:True negative, False positive
                    if bs == False:
                        delayinput = -1 * abs(delayinput)
                        delayinput = delayinput/2
                        lxt.mvr(delayinput)
                        while(lxt.moving == True):
                            time.sleep(0.01)
                        while(las.timing_check() != 1):### waiting for the lxt motion compledted
                            time.sleep(0.01)
                        print(f"Timewindow: {delayinput}")
                        #delayinput = delayinput/2
                        i = i + 1
                        prebs = False
                        inidirection = "n"
                        print(f"Number of iteration:{i}")
                        
                    elif bs == True:
                        delayinput = abs(delayinput)
                        delayinput = delayinput/2
                        lxt.mvr(delayinput)
                        while(lxt.moving == True):
                            time.sleep(0.01)
                        while(las.timing_check() != 1):### waiting for the lxt motion compledted
                            time.sleep(0.01)
                        print(f"Timewindow: {delayinput}")
                        #delayinput = delayinput/2
                        i = i + 1
                        prebs = True
                        inidirection = "p"
                        print(f"Number of iteration:{i}")
                las.tt_recover(scanrange = 10e-12,stepsize = -0.5e-12,direction = inidirection,testshot = 240)  
            return


        def autott_find_pink(ini_delay = 10e-9, testshot = 360, ttsiglevel = 0.95, calic = 1.1):#tt signal find tool the ini_delay is now input argument maybe for pink beam
            if lxt() != 0:
                print('\033[1m'+ "Set current position to 0 to search" + '\033[0m') 
                return
            elif lxt() ==0:
                las.tt_y.umv(54.67)#LuAG to find tt signal
                delayinput = ini_delay#Search window
                i = 0#iteration time
                print('\033[1m'+ "Checking white light Bg level"+'\033[0m')
                lom.yag.insert()#insert the YAG to block X-rays before the timetool target
                while(lom.yag.inserted == False ):
                    time.sleep(1)
                    print('Waiting for YAG getting in')
                ttdata = np.zeros([testshot,])
                ii = 0
                print("Getting the white light Bg level")
                for ii in range(testshot):###Get the white light Bg level without X-rays
                    current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()#get 240 shots to find timetool signal
                    ttdata[ii,] = ttintg
                    time.sleep(0.008)
                ttbg = np.mean(ttdata)# average white ROI signal without X-rays
                lom.yag.remove()
                while(lom.yag.removed == False ):####Removing lom YAG
                    time.sleep(1)
                    print('Waiting for lom YAG removed')
                
                
                for ii in range(testshot):###Get the white light Bg level without X-rays
                    current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()#get 240 shots to find timetool signal
                    ttdata[ii,] = ttintg
                    time.sleep(0.008)
                    
                ttbg = np.mean(ttdata)# average white ROI signal without X-rays

                #######Finding the initial correlation switching point####################

            
                print('\033[1m'+ "Searching the correlation switch point first"+'\033[0m')
                for ii in range(testshot):###Get the white light intensity with X-rays
                    current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()#get 240 shots to find timetool signal
                    ttdata[ii,] = ttintg
                    time.sleep(0.008)
                    #print(ii)
                ttroi = np.mean(ttdata)# average white ROI signal with X-rays
                print(ttroi)
                while(1):#20ns search until finding the correlation switched
                    bs = ((ttroi - ttbg * ttsiglevel) < 0) #input the current correlation
                    print(i)
                    if i == 0:# for the initialization
                        prebs = bs
                       
                        print((i < 10)and(prebs == bs))
                    if ((i < 10)and(prebs == bs)):#First search in 100 ns. 100 ns is too large. If cannot find in 10 iteration need to check the other side
                        print(bs)
                        if bs == False:
                            delayinput = -1 * abs(delayinput)
                            lxt.mvr(delayinput)
                            print("test")
                            i = i + 1
                            print(f"Searching the negative correlation with 10ns. Number of iteration:{i}")
                        elif bs == True:#find non-correlation
                            delayinput = abs(delayinput)
                            lxt.mvr(delayinput)
                            i = i + 1
                            print(f"Searching the positive or no correlation with 10ns. Number of iteration:{i}")
                        while(las.timing_check() != 1):### waiting for the lxt motion compledted
                            time.sleep(0.1)
                        for ii in range(testshot):###Get the white light intensity with X-rays
                            current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()#get 240 shots to find timetool signal
                            ttdata[ii,] = ttintg
                            time.sleep(0.008)
                        ttroi = np.mean(ttdata)# average white ROI signal with X-rays
                        bs = ((ttroi - ttbg * ttsiglevel) < 0) #input the current correlation
                        print(bs,ttroi-ttbg*ttsiglevel)
                    elif( i >= 10)and(prebs == bs):
                        print('\033[1m'+"the tt signal is far from 100 ns range, please search 100 ns range"+'\033[0m')  
                        return
                    elif(prebs != bs):
                        print('\033[1m'+"Switch to binary search"+'\033[0m')
                        break
                    #the correlation change?
                  
##########################binary search part######################
                while(abs(delayinput) > 2e-12):#binary search from 10ns to 5ps
                    print('\033[1m'+"Binary search"+'\033[0m')
                    for ii in range(testshot):###Get the white light intensity with X-rays
                        current_tt, ttamp, ipm2val, ttfwhm, ttintg = las.get_ttall()#get 240 shots to find timetool signal
                        ttdata[ii,] = ttintg
                        time.sleep(0.008)
                    ttroi = np.mean(ttdata)# average white ROI signal with X-rays
                    bs = ((ttroi - ttbg * ttsiglevel) < 0) #input the current correlation
                    if bs == False:
                        delayinput = -1 * abs(delayinput)
                        delayinput = delayinput/2
                        lxt.mvr(delayinput)
                        print(f"Timewindow: {delayinput}")
                        
                        i = i + 1
                        prebs = False
                        inidirection = "n"
                        print(f"Number of iteration:{i}")
                        
                    elif bs == True:
                        delayinput = abs(delayinput)
                        delayinput = delayinput/2
                        lxt.mvr(delayinput)
                        print(f"Timewindow: {delayinput}")
                        
                        i = i + 1
                        prebs = True
                        inidirection = "p"
                        print(f"Number of iteration:{i}")
                    while(las.timing_check() != 1):### waiting for the lxt motion compledted
                        time.sleep(0.1)
                las.tt_recover(scanrange = 10e-12,stepsize = -0.5e-12,direction = inidirection,testshot = 360) 
                
                
              
                #print("Found timetool signal and set current lxt to 0")
                #print(f"we will reset the current {lxt()} position to 0")
                #lxt.set_current_position(0)
                #las.tt_y.umv(67.1777)#Switch to YAG
                #print("Please run las.tt_rough_FB()")
                ttfb = input("Turn on feedback? yes(y)")
                if ((ttfb == "yes") or (ttfb == "y")):
                    print("feedback on")
                    las.tt_rough_FB(kp= 0.2,ki=0.1)
                else:
                    print("No feedback yet")
            return





##################################################################################################
#with safe_load('create cryo scattering chamber object group'):
    #class csc():
        #th = IMS('XPP:USR:MMS:17', name='th')
        #x = IMS('XPP:USR:MMS:18', name='x')
        #y = IMS('XPP:USR:MMS:25', name='y')
        #z = IMS('XPP:USR:MMS:24', name='z')
        #rz = IMS('XPP:USR:MMS:20', name='rz')
        #rx = IMS('XPP:USR:MMS:19', name='rx')
        #pmx = IMS('XPP:USR:MMS:23', name='pmx')
        #pmy = IMS('XPP:USR:MMS:22', name='pmy')
        #pmz = IMS('XPP:USR:MMS:21', name='pmz')
        #pmrot = SmarAct('XPP:MCS2:01:m10', name='pmrot')
        #dx = PMC100('XPP:USR:MMC:05', name='dx')
        #dy = PMC100('XPP:USR:MMC:06', name='dy')
        #dz = PMC100('XPP:USR:MMC:04', name='dz')


#from pcdsdevices.attenuator import FeeAtt
#from pcdsdevices.attenuator import FEESolidAttenuator
#with safe_load('fee attenuators alias'):
#    fat1=FeeAtt()
#    fat2=FEESolidAttenuator()

with safe_load('enable scan table scientific notation'):
    from bluesky.callbacks.core import LiveTable
    LiveTable._FMT_MAP['number'] = 'g'


with safe_load('Time tool target'):
    tt_x = IMS('XPP:SB2:MMS:30', name='tt_x')
    tt_y = IMS('XPP:SB2:MMS:31', name='tt_y')

with safe_load('Liquid Jet'):
   from pcdsdevices.jet import BeckhoffJet
   ljh = BeckhoffJet('XCS:LJH', name='ljh') 

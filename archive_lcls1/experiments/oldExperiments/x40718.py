from subprocess import check_output

import json
import sys
import time
import os

import numpy as np
from hutch_python.utils import safe_load
from ophyd import EpicsSignalRO
from ophyd import EpicsSignal
from bluesky import RunEngine
from bluesky.plans import scan
from bluesky.plans import list_scan
from ophyd import Component as Cpt
from ophyd import Device
from pcdsdevices.interface import BaseInterface
from pcdsdevices.areadetector import plugins
from xpp.db import daq
from xpp.db import camviewer
from xpp.db import RE
from xpp.db import at2l0
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.device_types import Trigger
#move this to beamline with the most typical detectors.
from pcdsdaq.ami import AmiDet


class ImagerStats3():

    def __init__(self, imager=None):
        try:
            self.imager = imager
            self.prefix = imager.prefix

        except AttributeError:
            self.imager = camviewer.im1l0
            self.prefix = 'IM1L0:XTES:CAM:'
            print('defaulting to IM1L0')
       
        self.initialize()

    def initialize(self):
        self.imager_name = self.prefix[:5]
        self.image_stream = self.prefix + 'IMAGE3:'
        self.image3 = plugins.ImagePlugin(prefix=self.image_stream,
                name=self.imager_name+'_image3', parent=self.imager)
        self.roi = plugins.ROIPlugin(prefix=self.image_stream+'ROI:',
                name=self.imager_name+'_roi', parent=self.image3)
        self.proc = plugins.ProcessPlugin(prefix=self.image_stream+'Proc:',
                name=self.imager_name+'_proc', parent=self.image3)
        self.stats = self.imager.stats3
        self.binX = EpicsSignal(self.image_stream+'ROI:BinX', name='omitted')
        self.binY = EpicsSignal(self.image_stream+'ROI:BinY', name='omitted')
        self.saveBackground = EpicsSignal(self.image_stream+'Proc:SaveBackground', name='omitted') 

    def setImager(self, imager):
        try:
            self.prefix = imager.prefix
        except AttributeError:
            print('Imager not set')

        self.initialize()

    def setup_binning(self, binning):
        self.binX.set(binning)
        self.binY.set(binning)
        self.roi.scale.set(binning**2)

    def prepare(self, take_background=False):

        # set up ports
        self.proc.nd_array_port.set('CAM')
        self.roi.nd_array_port.set('IMAGE3:Proc')
        self.image3.nd_array_port.set('IMAGE3:ROI')
        self.stats.nd_array_port.set('IMAGE3:ROI')

        # set default binning to 2
        self.setup_binning(2)

        # enable all the things
        self.image3.enable.set(1)
        self.roi.enable.set(1)
        self.proc.enable.set(1)

        # make sure camera is acquiring
        self.imager.cam.acquire.put(0, wait=True)
        self.imager.cam.acquire.put(1)

        if take_background:
            self.take_background()

        # apply background
        self.proc.enable_background.set(1)

        # enable stats
        self.stats.compute_statistics.set(1)
        self.stats.compute_centroid.set(1)
        self.stats.enable.set(1)

        # get noise level
        time.sleep(.1)
        sigma = self.stats.sigma.get()

        # set offset to negative sigma
        print(sigma)
        #self.proc.offset.set(-sigma)
        # set threshold to one sigma
        self.stats.centroid_threshold.set(sigma)
        self.stats.bgd_width.put(sigma)

        # switch stats over to ROI stream
        #self.stats.nd_array_port.set('IMAGE3:ROI')


        # set scale and limits
        self.proc.scale.set(1)
        self.proc.low_clip.set(0)
        # disable high clipping for now, but enable low clipping
        self.proc.enable_low_clip.set(1)
        self.proc.enable_high_clip.set(0)
        # apply scale and offset
        self.proc.enable_offset_scale.set(1)

    def get_centroids(self):

        centroids = self.stats.centroid.get()
        centroid_x = centroids.x
        centroid_y = centroids.y

        return centroid_x, centroid_y

    def disable_background(self):
        self.proc.enable_background.set(0)
        self.proc.enable_offset_scale.set(0)
        self.proc.enable_low_clip.set(0)
        self.proc.enable_high_clip.set(0)

    def stop(self):
        self.stats.enable.set(0)

    def take_background(self, num_images=100):
        
        # set minimum number of images to 20
        if num_images <= 20:
            num_images = 20
        
        # turn off background subtraction
        self.proc.enable_background.set(0)
        self.proc.enable_offset_scale.set(0)
        self.proc.enable_low_clip.set(0)
        self.proc.enable_high_clip.set(0)
        
        # turn on averaging
        self.proc.filter_type.set('RecursiveAve')
        self.proc.num_filter.set(num_images)
        # following sets to array n only
        self.proc.filter_callbacks.set(1)
        self.proc.auto_reset_filter.set(1)
        self.proc.enable_filter.set(1)

        # wait until we have at least one averaged image
        print('waiting for averaging to finish...')
        if self.proc.num_filtered.get() < 10:
            while self.proc.num_filtered.get() <= 10:
                time.sleep(.1)
                #print(self.proc.num_filtered.get())
            while self.proc.num_filtered.get() > 10:
                time.sleep(.1)
                #print(self.proc.num_filtered.get())
        else:
            while self.proc.num_filtered.get() > 10:
                time.sleep(.1)
                #print(self.proc.num_filtered.get())
        print('finished acquiring')
        # save background
        #self.proc.save_background.set(1)
        self.saveBackground.set(1)

        # turn off averaging
        self.proc.enable_filter.set(0)


class ImagerHdf5():
    def __init__(self, imager=None):
        try:
            self.imagerh5 = imager.hdf51
            self.imager = imager.cam
        except:
            self.imagerh5 = None
            self.imager = None
            
    def setImager(self, imager):
        self.imagerh5 = imager.hdf51
        self.imager = imager.cam
        
    def stop(self):
        self.imagerh5.enable.set(0)

    def status(self):
        print('Enabled',self.imagerh5.enable.get())
        print('File path',self.imagerh5.file_path.get())
        print('File name',self.imagerh5.file_name.get())
        print('File template (should be %s%s_%d.h5)',self.imagerh5.file_template.get())

        print('File number',self.imagerh5.file_number.get())
        print('Frame to capture per file',self.imagerh5.num_capture.get())
        print('autoincrement ',self.imagerh5.auto_increment.get())
        print('file_write_mode ',self.imagerh5.file_write_mode.get())
        #IM1L0:XTES:CAM:HDF51:Capture_RBV 0: done, 1: capturing
        print('captureStatus ',self.imagerh5.capture.get())

    def prepare(self, baseName=None, pathName=None, nImages=None, nSec=None):
        if self.imagerh5.enable.get() != 'Enabled':
            self.imagerh5.enable.put(1)
        iocdir=self.imager.prefix.split(':')[0].lower()
        if pathName is not None:
            self.imagerh5.file_path.set(pathName)
        elif len(self.imagerh5.file_path.get())==0:
            #this is a terrible hack.
            iocdir=self.imager.prefix.split(':')[0].lower()
            camtype='opal'
            if (self.imager.prefix.find('PPM')>0): camtype='gige'
            self.imagerh5.file_path.put('/reg/d/iocData/ioc-%s-%s/images/'%(iocdir, camtype))
        if baseName is not None:
            self.imagerh5.file_name.put(baseName)
        else:
            expname = check_output('get_curr_exp').decode('utf-8').replace('\n','')
            try:
                lastRunResponse = check_output('get_lastRun').decode('utf-8').replace('\n','')
                if lastRunResponse == 'no runs yet': 
                    runnr=0
                else:
                    runnr = int(check_output('get_lastRun').decode('utf-8').replace('\n',''))
            except:
                runnr = 0
            self.imagerh5.file_name.put('%s_%s_Run%03d'%(iocdir,expname, runnr+1))

        self.imagerh5.file_template.put('%s%s_%d.h5')
        #check that file to be written does not exist
        already_present = True
        while (already_present):
            fnum = self.imagerh5.file_number.get()
            fname = self.imagerh5.file_path.get() + self.imagerh5.file_name.get() + \
                    '_%d'%fnum + '.h5'
            if os.path.isfile(fname):
                print('File %s already exists'%fname)
                self.imagerh5.file_number.put(1 + fnum)
                time.sleep(0.2)
            else:
                already_present = False

        self.imagerh5.auto_increment.put(1)
        self.imagerh5.file_write_mode.put(2)
        if nImages is not None:
            self.imagerh5.num_capture.put(nImages)
        if nSec is not None:
            if self.imager.acquire.get() > 0:
                rate = self.imager.array_rate.get()
                self.imagerh5.num_capture.put(nSec*rate)
            else:
                print('Imager is not acquiring, cannot use rate to determine number of recorded frames')

    def write(self, nImages=None):
        if nImages is not None:
            self.imagerh5.num_capture.put(nImages)
        if self.imager.acquire.get() == 0:
            self.imager.acquire.put(1)
        self.imagerh5.capture.put(1)

    def write_wait(self, nImages=None):
        while (self.imagerh5.num_capture.get() > 
               self.imagerh5.num_captured.get()):
            time.sleep(0.25)

    def write_stop(self):
        self.imagerh5.capture.put(0)

class ImagerStats():
    def __init__(self, imager=None):
        try:
            self.imager = imager.cam
            self.imgstat = imager.stats1
        except:
            self.imager = None
            self.imgstat = None
            
    def setImager(self, imager):
        self.imager = imager.cam
        self.imgstat = imager.stats1

    def stop(self):
        self.imgstat.enable.set(0)

    def setThreshold(self, inSigma=1):
        self.imgstat.enable.set(1)
        computeStat = self.imgstat.compute_statistics.get()
        self.imgstat.compute_statistics.set(1)
        mean = self.imgstat.mean_value.get()
        sigma = self.imgstat.sigma.get()
        self.imgstat.centroid_threshold.set(mean+sigma*nSigma)
        self.imgstat.compute_statistics.set(computeStat)

    def prepare(self, threshold=None, thresholdSigma=None):
        self.imager.acquire.set(1)
        if self.imgstat.enable.get() != 'Enabled':
            self.imgstat.enable.set(1)
        if thresholdSigma is not None:
            self.setThreshold(inSigma=thresholdSigma)
            self.imgstat.centroid_threshold.set(threshold)
        elif threshold is not None:
            if self.imgstat.compute_centroid.get() != 'Yes':
                self.imgstat.compute_centroid.set(1)
            self.imgstat.centroid_threshold.set(threshold)
        self.imgstat.compute_profiles.set(1)
        self.imgstat.compute_centroid.set(1)

    def status(self):
        print('enabled:', self.imgstat.enable.get())
        if self.imgstat.enable.get() == 'Enabled':
            if self.imgstat.compute_statistics.get() == 'Yes':
                #IM1L0:XTES:CAM:Stats1:MeanValue_RBV
                #IM1L0:XTES:CAM:Stats1:SigmaValue_RBV
                print('Mean', self.imgstat.mean_value.get())
                print('Sigma', self.imgstat.sigma.get())
            if self.imgstat.compute_centroid.get() == 'Yes':
                print('Threshold', self.imgstat.centroid_threshold.get())
                #IM1L0:XTES:CAM:Stats1:CentroidX_RBV
                #IM1L0:XTES:CAM:Stats1:CentroidY_RBV
                #IM1L0:XTES:CAM:Stats1:SigmaX_RBV
                #IM1L0:XTES:CAM:Stats1:SigmaY_RBV
                print('X,y', self.imgstat.centroid.get())
                print('sigma x', self.imgstat.sigma_x.get())
                print('sigma y', self.imgstat.sigma_y.get())
            if self.imgstat.compute_profile.get() == 'Yes':
                #IM1L0:XTES:CAM:Stats1:CursorX
                #IM1L0:XTES:CAM:Stats1:CursorY
                print('profile cursor values: ',self.imgstat.cursor.get())
                #IM1L0:XTES:CAM:Stats1:ProfileAverageX_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileAverageY_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileThresholdX_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileThresholdY_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileCentroidX_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileCentroidY_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileCursorX_RBV
                #IM1L0:XTES:CAM:Stats1:ProfileCursorY_RBV
                print('profile cursor: ',self.imgstat.profile_cursor.get())
                print('profile centroid: ',self.imgstat.profile_centroid.get())
                if self.imgstat.compute_centroid.get() == 'Yes':
                    print('profile threshold: ',self.imgstat.profile_threshold.get())
                    print('profile avergage: ',self.imgstat.profile_average.get())

class User():
    def __init__(self):
        self.t0=894756
        try:
            self.im1l0_h5 = ImagerHdf5(camviewer.im1l0)
            self.im2l0_h5 = ImagerHdf5(camviewer.im2l0)
            self.im3l0_h5 = ImagerHdf5(camviewer.im3l0)
            self.im4l0_h5 = ImagerHdf5(camviewer.im4l0)
            self.gige13_h5 = ImagerHdf5(camviewer.xpp_gige_13)
            self.im1l0_stats = ImagerStats(camviewer.im1l0)
            self.im2l0_stats = ImagerStats(camviewer.im2l0)
            self.im3l0_stats = ImagerStats(camviewer.im3l0)
            self.im4l0_stats = ImagerStats(camviewer.im4l0)
            self.im1l0_stats3 = ImagerStats3(camviewer.im1l0)
            self.im2l0_stats3 = ImagerStats3(camviewer.im2l0)
            self.im3l0_stats3 = ImagerStats3(camviewer.im3l0)
            self.im4l0_stats3 = ImagerStats3(camviewer.im4l0)
        except:
            self.im1l0_h5 = None
            self.im2l0_h5 = None
            self.im3l0_h5 = None
            self.im4l0_h5 = None
            self.im1l0_stats = None
            self.im2l0_stats = None
            self.im3l0_stats = None
            self.im4l0_stats = None
            self.im1l0_stats3 = None
            self.im3l0_stats3 = None
            self.im4l0_stats3 = None
        with safe_load('op_x'):
            self.op_x = Newport('XPP:USR:PRT:MMN:07', name='op_x')
        with safe_load('op_y'):
            self.op_y = IMS('XPP:USR:MMS:25', name='op_y')
        with safe_load('op_focus'):
            self.op_focus = IMS('XPP:USR:MMS:30', name='op_focus')
        with safe_load('op_rot'):
            self.op_rot = Newport('XPP:USR:PRT:MMN:04', name='op_rot')
        with safe_load('grating_xyz'):
            self.grating_x = Newport('XPP:USR:PRT:MMN:06', name='grating_x')
            self.grating_y = Newport('XPP:USR:PRT:MMN:05', name='grating_y')
            self.grating_z = Newport('XPP:USR:PRT:MMN:08', name='grating_z')
        with safe_load('lom_th2'):
            self.lom_th2 = IMS('XPP:MON:MMS:13', name='lom_th2')
        with safe_load('Be_motors'):
            self.Be_xpos = IMS('XPP:SB2:MMS:13', name='Be_xpos')
            self.Be_ypos = IMS('XPP:SB2:MMS:14', name='Be_ypos')
            self.Be_zpos = IMS('XPP:SB2:MMS:15', name='Be_zpos')
        with safe_load('jjho'):
            self.jjho = IMS('XPP:USR:MMS:31', name='jjho')
        with safe_load('jjhg'):
            self.jjhg = IMS('XPP:USR:MMS:22', name='jjhg')
        with safe_load('jjvo'):
            self.jjvo = IMS('XPP:USR:MMS:29', name='jjvo')
        with safe_load('jjvg'):
            self.jjvg = IMS('XPP:USR:MMS:30', name='jjvg')


    def takeRun(self, nEvents, record=True):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    # dscan & ascan kludge for x421 evr delay scan, as the evr object does not have the wm and mv attributes
    def evrascan(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.get()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.set(currPos)

    def evrdscan(self, motor, start, end, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.get()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.set(currPos)

    def ascan(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.mv(currPos)

    def ascanXCS(self, motor, start, end, nsteps, nEvents, record=None):
        currPos = motor.wm()
        if record is None:
            daq.configure(nEvents, controls=[motor])
        else:
            daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.mv(currPos)

    def listscan(self, motor, posList, nEvents, record=None):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(list_scan([daq], motor, posList))
        motor.mv(currPos)

    def dscan(self, motor, start, end, nsteps, nEvents, record=None):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.wm()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.mv(currPos)

    def a2scan(self, m1, a1, b1, m2, a2, b2, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[m1, m2])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, nsteps))

    def a3scan(self, m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[m1, m2, m3])
        RE(scan([daq], m1, a1, b1, m2, a2, b2, m3, a3, b3, nsteps))

    def ascan_wimagerh5(self, imagerh5, motor, start, end, nsteps, nEvents, record=True):
        plan_duration = nsteps*nEvents/120.+0.3*(nsteps-1)+4
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        #we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)
        imagerh5.write_wait()

    def ascan_wimagerh5_slow(self, imagerh5, motor, start, end, nsteps, nEvents, record=True):
        plan_duration = (nsteps*nEvents/120.+0.3*(nsteps-1)+4)*10
        try:
            imagerh5.prepare(nSec=plan_duration)
        except:
            print('imager preparation failed')
            return
        daq.configure(nEvents, record=record, controls=[motor])
        this_plan = scan([daq], motor, start, end, nsteps)
        #we assume DAQ runs at 120Hz (event code 40 or 140)
        #       a DAQ transition time of 0.3 seconds
        #       a DAQ start time of about 1 sec
        #       two extra seconds.
        #       one extra second to wait for hdf5 file to start being written
        imagerh5.write()
        time.sleep(1)
        RE(this_plan)
        
        imagerh5.write_stop()



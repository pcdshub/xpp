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

import sys
sys.path.append('/reg/neh/home/seaberg/Python/lcls_beamline_toolbox/')
from lcls_beamline_toolbox.xrayinteraction import interaction
from lcls_beamline_toolbox.xraybeamline2d import optics

class PPM_Record():
    def __init__(self, pvname='IM3L0:PPM:SPM:VOLT_BUFFER_RBV',time=1, 
                   filename=None):
        self.collection_time = time
        self.arr = []
        self.pvname = pvname
        self.sig = EpicsSignalRO(pvname)
        try:
            self.sig.wait_for_connection(timeout=3.0)
        except TimeoutError:
            print(f'Could not connect to data PV {pvname}, timed out.')
            print('Either on wrong subnet or the ioc is off.')
        if filename is not None:
            self.filename = filename
        else:
            self.setFilename()

    def cb10(self, value, **kwargs):
        #print('value ',value)
        # Downsample to 10Hz from 1000Hz
        for i in range(10):
            self.arr.append(np.mean(value[100*i:100*(i+1)]))
        #print('{} values collected'.format(len(self.arr)))


    def cb100(self, value, **kwargs):
        # Downsample to 100Hz from 1000Hz
        for i in range(100):
            self.arr.append(np.mean(value[10*i:10*(i+1)]))

    def cb(self, value, **kwargs):
        self.arr.append(value)

    def setCollectionTime(self, ctime=None):
        if ctime is not None:
            self.collection_time = ctime

    def collectData(self, rate=10):
        if rate==100:
            cbid = self.sig.subscribe(self.cb100)
        elif rate==10:
            cbid = self.sig.subscribe(self.cb10)
        else:
            cbid = self.sig.subscribe(self.cb)
        time.sleep(self.collection_time)
        self.sig.unsubscribe(cbid)

    def setFilename(self, basename=None, useTime=True):
        dirname='/reg/neh/operator/xppopr/experiments/xppx43118/powermeterData/'
        if basename is None:
            basename = dirname + self.pvname.split(':')[0]+'_powermeter_data'
        if useTime:
            self.filename = basename+'_{}'.format(int(time.time()))+'.data'
        else:
            self.filename = basename
        
    def writeFile(self):
        #print('saving to {}'.format(self.filename))
        with open(self.filename, 'w') as fd:
            for value in self.arr:
                print(value, file=fd)
        #if len(self.arr) == 0:
        #    print('Warning: no data points collected! File is empty!')
        self.arr = []

    def saveData(self, ctime=None, rate=10, basename=None, useTime=True):
        self.setFilename(basename=basename, useTime=useTime)
        self.setCollectionTime(ctime=ctime)
        self.collectData(rate=rate)
        self.writeFile()

class FEEAlign:
    def __init__(self, im1, im2, im3, im4, mr1, mr2):
        pass


class AT2L0:

    def __init__(self, att):
        self.att = att
        self.blades = {}
        self.blades[2] = {'material': 'diamond', 'thickness': 1280}
        self.blades[4] = {'material': 'diamond', 'thickness': 640}
        self.blades[3] = {'material': 'diamond', 'thickness': 320}
        self.blades[5] = {'material': 'diamond', 'thickness': 160}
        self.blades[6] = {'material': 'diamond', 'thickness': 80}
        self.blades[7] = {'material': 'diamond', 'thickness': 40}
        self.blades[8] = {'material': 'diamond', 'thickness': 20}
        self.blades[9] = {'material': 'diamond', 'thickness': 10}
        self.blades[10] = {'material': 'silicon', 'thickness': 10240}
        self.blades[11] = {'material': 'silicon', 'thickness': 5120}
        self.blades[12] = {'material': 'silicon', 'thickness': 2560}
        self.blades[13] = {'material': 'silicon', 'thickness': 1280}
        self.blades[14] = {'material': 'silicon', 'thickness': 640}
        self.blades[15] = {'material': 'silicon', 'thickness': 320}
        self.blades[16] = {'material': 'silicon', 'thickness': 160}
        self.blades[17] = {'material': 'silicon', 'thickness': 80}
        self.blades[18] = {'material': 'silicon', 'thickness': 40}
        self.blades[19] = {'material': 'silicon', 'thickness': 20}
        self.silicon = interaction.Device('silicon', range='HXR', material='Si', thickness=0)
        self.diamond = interaction.Device('diamond', range='HXR', material='CVD', thickness=0)

        self.max_diamond = 2550
        self.max_silicon = 20460

        self.blade_motors = {}
        for i in range(2,20):
            if i < 10:
                bladeNum = '0%d' % i
            else:
                bladeNum = '%d' % i
            blade = getattr(self.att, 'blade_%s' % bladeNum)

            self.blade_motors[i] = blade


    def get_diamond_thickness(self):

        total_thickness = 0

        for i in range(2, 10):
            # check if inserted

            if self.blade_motors[i]() < 1:
                total_thickness += self.blades[i]['thickness']

        return total_thickness

    def get_silicon_thickness(self):
        total_thickness = 0

        for i in range(10, 20):
            # check if inserted

            if self.blade_motors[i]() < 1:
                total_thickness += self.blades[i]['thickness']

        return total_thickness


    def _get_thickness_both(self, transmission, E):
        """
        Calculate silicon thickness in microns to achieve the desired transmission
        """
        diamond_thickness = self.diamond.get_thickness(transmission, E*1e3)*1e6
        if diamond_thickness > self.max_diamond:
            diamond_thickness = self.max_diamond

        Td = self.diamond.transmission(thickness=diamond_thickness*1e-6)

        energy = self.diamond.energy
        Td = np.interp(E*1e3, energy, Td)
        
        Ts = transmission / Td

        silicon_thickness = self.silicon.get_thickness(Ts, E*1e3)*1e6

        return diamond_thickness, silicon_thickness

    def _get_thickness(self, transmission, E):
        """
        Calculate silicon thickness in microns to achieve the desired transmission
        """
        thickness = self.silicon.get_thickness(transmission, E*1e3)*1e6

        return thickness

    def blade_insertions(self, transmission, E):
        d_thickness, s_thickness = self._get_thickness_both(transmission, E)

        # figure out binary representation of transmission with powers of 2
        d_multiplier = d_thickness/10
        d_multiplier = int(d_multiplier)
        print(np.binary_repr(int(d_multiplier), width=8))

        d_blade_insertions = np.binary_repr(d_multiplier, width=8)
        
        # figure out binary representation of transmission with powers of 2
        s_multiplier = s_thickness/20
        s_multiplier = int(s_multiplier)
        print(s_multiplier)
        print(np.binary_repr(int(s_multiplier), width=10))

        s_blade_insertions = np.binary_repr(s_multiplier, width=10)

        return d_blade_insertions, s_blade_insertions

    def set_silicon_thickness(self, thickness):
        """
        Insert silicon blades

        :param thickness: total thickness in microns
        """
        # figure out binary representation of transmission with powers of 2
        s_multiplier = thickness/20
        s_multiplier = int(s_multiplier)
        print(np.binary_repr(int(s_multiplier), width=10))
        print('closest available thickness: %d \u03BCm' % (s_multiplier*20))

        s_blade_insertions = np.binary_repr(s_multiplier, width=10)

        # insert silicon
        for i in range(10):
            index = i+10
            if s_blade_insertions[i] == '1':
                print('blade %s should be in' % index)
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(0)
            else:
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(24)
                print('blade %s should be out' % index)
            #if self.blade_motors[index]()>23:
            #    print('blade %s is out' % index)
            #elif self.blade_motors[index]()<1:
            #    print('blade %s is in' % index)

    def set_diamond_thickness(self, thickness):
        """
        Insert diamond blades

        :param thickness: total thickness in microns
        """

        # figure out binary representation of transmission with powers of 2
        d_multiplier = thickness/10
        d_multiplier = int(d_multiplier)
        print(np.binary_repr(int(d_multiplier), width=8))
        print('closest available thickness: %d \u03BCm' % (d_multiplier*10))

        d_blade_insertions = np.binary_repr(d_multiplier, width=8)
        
        # insert diamond
        for i in range(8):
            index = i+2
            if d_blade_insertions[i] == '1':
                print('blade %s should be in' % index)
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(0)
            else:
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(24)
                print('blade %s should be out' % index)
            #if self.blade_motors[index]()>23:
            #    print('blade %s is out' % index)
            #elif self.blade_motors[index]()<1:
            #    print('blade %s is in' % index)


    def set_transmission(self, transmission, E): 
        """
        Function to set the transmission of AT2L0 using both diamond and silicon
        """

        tic = time.perf_counter()
        d_thickness, s_thickness = self._get_thickness_both(transmission, E)

        # figure out binary representation of transmission with powers of 2
        d_multiplier = d_thickness/10
        d_multiplier = int(d_multiplier)
        print(np.binary_repr(int(d_multiplier), width=8))

        d_blade_insertions = np.binary_repr(d_multiplier, width=8)
        
        # figure out binary representation of transmission with powers of 2
        s_multiplier = s_thickness/20
        s_multiplier = int(s_multiplier)
        print(s_multiplier)
        print(np.binary_repr(int(s_multiplier), width=10))

        s_blade_insertions = np.binary_repr(s_multiplier, width=10)

        toc = time.perf_counter()
        print('took %.4f seconds to calculate configuration' % (toc-tic))

        # insert diamond
        for i in range(8):
            index = i+2
            if d_blade_insertions[i] == '1':
                print('blade %s should be in' % index)
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(0)
            else:
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(24)
                print('blade %s should be out' % index)
            #if self.blade_motors[index]()>23:
            #    print('blade %s is out' % index)
            #elif self.blade_motors[index]()<1:
            #    print('blade %s is in' % index)
        
        # insert silicon
        for i in range(10):
            index = i+10
            if s_blade_insertions[i] == '1':
                print('blade %s should be in' % index)
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(0)
            else:
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(24)
                print('blade %s should be out' % index)
            #if self.blade_motors[index]()>23:
            #    print('blade %s is out' % index)
            #elif self.blade_motors[index]()<1:
            #    print('blade %s is in' % index)

    def set_Si_transmission(self, transmission, E):
        """
        Function to set the transmission of AT2L0
        """
        thickness = self._get_thickness(transmission, E)

        # figure out binary representation of transmission with powers of 2
        multiplier = thickness/20
        multiplier = int(multiplier)
        print(np.binary_repr(int(multiplier), width=10))

        blade_insertions = np.binary_repr(multiplier, width=10)

        for i in range(10):
            index = i+10
            if blade_insertions[i] == '1':
                print('blade %s should be in' % index)
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(0)
            else:
                self.blade_motors[index].user_offset_dir.set(0)
                self.blade_motors[index].user_offset.set(0)
                self.blade_motors[index].user_setpoint.set(24)
                print('blade %s should be out' % index)
            #if self.blade_motors[index]()>23:
            #    print('blade %s is out' % index)
            #elif self.blade_motors[index]()<1:
            #    print('blade %s is in' % index)

    def get_transmission(self, E):
        """
        total transmission through solid attenuator

        :param E: float
            photon energy to calculate for in keV
        :return transmission: float
            total transmission
        """
        # get silicon thickness
        total_silicon = self.get_silicon_thickness()
        # get diamond thickness
        total_diamond = self.get_diamond_thickness()

        Ts = self.silicon.transmission(thickness=total_silicon*1e-6)
        Td = self.diamond.transmission(thickness=total_diamond*1e-6)

        T = Ts*Td
        # get energy array
        energy = self.silicon.energy
        # interpolate
        T_E = np.interp(E*1e3, energy, T)
        T_2 = np.interp(E*1e3*2, energy, T)
        T_3 = np.interp(E*1e3*3, energy, T)

        print('Fundamental transmission: %.2e' % T_E)
        print('2nd harmonic transmission: %.2e' % T_2)
        print('3rd harmonic transmission: %.2e' % T_3)
        
        return T_E


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

class AT1L0(Device, BaseInterface):
    energy = EpicsSignalRO('SATT:FEE1:320:ETOA.E', kind='config')
    attenuation = EpicsSignalRO('SATT:FEE1:320:RACT', kind='hinted')
    transmission = EpicsSignalRO('SATT:FEE1:320:TACT', name='normal')
    r_des = EpicsSignal('SATT:FEE1:320:RDES', name='normal')
    r_floor = EpicsSignal('SATT:FEE1:320:R_FLOOR', name='omitted')
    r_ceiling = EpicsSignal('SATT:FEE1:320:R_CEIL', name='omitted')
    trans_floor = EpicsSignal('SATT:FEE1:320:T_FLOOR', name='omitted')
    trans_ceiling = EpicsSignal('SATT:FEE1:320:T_CEIL', name='omitted')
    go = EpicsSignal('SATT:FEE1:320:GO', name='omitted')
    
    def setR(self, att_des, ask=False, wait=True):
        self.att_des.put(att_des)
        if ask:
            print('possible ratios: %g (F) -  %g (C)'%(self.r_floor, self.r_ceiling))
            answer=raw_input('F/C? ')
        if answer=='C':
            self.go.put(2)
            if wait: time.sleep(5)
        else:
            self.go.put(3)
            if wait: time.sleep(5)        

class User():
    def __init__(self):
        self.im3l0_ppm_record = PPM_Record()
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
            self.at2l0 = AT2L0(at2l0)
            with safe_load('op_x'):
                self.op_x = Newport('XPP:USR:PRT:MMN:07', name='op_x')
            with safe_load('op_y'):
                self.op_y = IMS('XPP:USR:MMS:25', name='op_y')
            with safe_load('op_focus'):
                self.op_focus = IMS('XPP:USR:MMS:30', name='op_focus')
            with safe_load('op_rot'):
                self.op_rot = Newport('XPP:USR:PRT:MMN:04', name='op_rot')
            with safe_load('grating_x'):
                self.grating_x = Newport('XPP:USR:PRT:MMN:06', name='grating_x')
            with safe_load('grating_y'):
                self.grating_y = Newport('XPP:USR:PRT:MMN:05', name='grating_y')
            with safe_load('grating_z'):
                self.grating_z = Newport('XPP:USR:PRT:MMN:08', name='grating_z')
            with safe_load('lom_th2'):
                self.lom_th2 = IMS('XPP:MON:MMS:13', name='lom_th2')
            with safe_load('Be_xpos'):
                self.Be_xpos = IMS('XPP:SB2:MMS:13', name='Be_xpos')
            with safe_load('Be_ypos'):
                self.Be_ypos = IMS('XPP:SB2:MMS:14', name='Be_ypos')
            with safe_load('Be_zpos'):
                self.Be_zpos = IMS('XPP:SB2:MMS:15', name='Be_zpos')
            with safe_load('Triggers'):
                self.evr_R30E26 = Trigger('XPP:R30:EVR:26:TRIGB', name='evr_R30E26')
                self.evr_R30E28 = Trigger('XPP:R30:EVR:28:TRIGB', name='evr_R30E28')
                self.evr_R30E26_ticks = EpicsSignal('XPP:R30:EVR:26:CTRL.DGBD', name='evr_R30E26_ticks')
                self.evr_R30E28_ticks = EpicsSignal('XPP:R30:EVR:28:CTRL.DGBD', name='evr_R30E28_ticks')
            with safe_load('bodX'):
                self.bodX = IMS('XPP:USR:MMS:28', name='bodX')
            with safe_load('bodY'):
                self.bodY = IMS('XPP:USR:MMS:01', name='bodY')
            with safe_load('CC1_x'):
                self.CC1_x = IMS('XPP:USR:MMS:07', name='CC1_x')
            with safe_load('CC1_th'):
                self.CC1_th = IMS('XPP:USR:MMS:29', name='CC1_th')
            with safe_load('CC2_x'):
                self.CC2_x = IMS('XPP:USR:MMS:09', name='CC2_x')
            with safe_load('CC2_th'):
                self.CC2_th = IMS('XPP:USR:MMS:20', name='CC2_th')
            with safe_load('zyla_x'):
                self.zyla_x = IMS('XPP:USR:MMS:25', name='zyla_x')
            with safe_load('zyla_y'):
                self.zyla_y = IMS('XPP:USR:MMS:08', name='zyla_y')
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
            self.at2l0 = None
        self.at1l0 = AT1L0(name='at1l0')



    def savePowermeter(self, pwm=None, colltime=None, rate=None, filename=None):
        if pwm is None: pwm = self.im3l0_ppm_record
        if colltime is not None:
            pwm.setCollectionTime(colltime)
        if filename is not None:
            pwm.setFilename(filename)
        else:
            basename = pwm.pvname.split(':')[0]+'_powermeter'
            expname = check_output('get_curr_exp').decode('utf-8').replace('\n','')
            try:
                runnr = int(check_output('get_lastRun').decode('utf-8').replace('\n',''))
            except:
                runnr=0
            dirname = '/reg/neh/operator/%sopr/experiments/%s'%(expname[:3], expname)
            pwm.setFilename('%s/powermeterData/%s_Run%03d_%s.data'%(dirname,expname, runnr+1, basename))
        pwm.collectData(rate=rate)
        pwm.writeFile()
        print('Wrote %d seconds of powermeter data to %s'%(pwm.collection_time,pwm.filename))

    def takeRun(self, nEvents, record=True):
        daq.configure(events=120, record=record)
        daq.begin(events=nEvents)
        daq.wait()
        daq.end_run()

    def get_ascan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        return scan([daq], motor, start, end, nsteps)

    def get_dscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record)
        currPos = motor.wm()
        return scan([daq], motor, currPos+start, currPos+end, nsteps)

    def ascan(self, motor, start, end, nsteps, nEvents, record=True):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.mv(currPos)

    def listscan(self, motor, posList, nEvents, record=True):
        currPos = motor.wm()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(list_scan([daq], motor, posList))
        motor.mv(currPos)

    def dscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.wm()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.mv(currPos)

    # dscan & ascan kludge for x421 evr delay scan, as the evr object does not have the wm and mv attributes
    def evrascan(self, motor, start, end, nsteps, nEvents, record=True):
        currPos = motor.get()
        daq.configure(nEvents, record=record, controls=[motor])
        RE(scan([daq], motor, start, end, nsteps))
        motor.set(currPos)

    def evrdscan(self, motor, start, end, nsteps, nEvents, record=True):
        daq.configure(nEvents, record=record, controls=[motor])
        currPos = motor.get()
        RE(scan([daq], motor, currPos+start, currPos+end, nsteps))
        motor.set(currPos)

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

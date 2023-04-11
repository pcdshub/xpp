from ophyd import (Device, EpicsSignal, EpicsSignalRO, Component as Cpt,
                   FormattedComponent as FCpt)
from ophyd.signal import AttributeSignal, Signal

import pcdsdevices.device_types
from pcdsdevices.inout import InOutPositioner
from subprocess import check_output


import time



class ShutterSequencerDoublePump():
    """ Class to control double pump shutters and set according sequences 
        
    Workflow for shutter and sequence configurations:
    1. Stop sequence (no event code are being fired)
    2. Open / close shutters
    3. Configure new sequence
    4. Wait 0.03s to make sure shutters are in position
    5. Start sequence
    """
    def __init__(
        self, 
        shutter1 = lp, 
        shutter2 = ep, 
        code1_on = 92, 
        code1_off = 93, 
        code2_on = 97, 
        code2_off = 98
        ):
        """
        Parameters
        ----------
        shutter1:   LaserShutter instance for pump 1
        shutter2:   LaserShutter instance for pump 2
        code1_on:   Event code for pump 1 on
        code1_off:  Event code for pump 1 off
        code2_on:   Event code for pump 2 on
        code2_off:  Event code for pump 2 off
        """
        self.s1 = shutter1
        self.s2 = shutter2
        self.c1_on = code1_on
        self.c1_off = code1_off
        self.c2_on = code2_on
        self.c2_off = code2_off
        return

    def __repr__(self):
        if self.s1.inserted:
            s1_status = 'Close'
        else:
            s1_status = 'Open'
        if self.s2.inserted:
            s2_status = 'Close'
        else:
            s2_status = 'Open'

        curr_seq = seq.sequence.get_seq()
        s = ''
        for el in curr_seq:
            s+=f'{el}\n'

        r = f"""
Pump 1 shutter: {s1_status}
Pump 2 shutter: {s2_status}\n
Sequence:
{s}
        """
        return r

    def print_status(self):
        print(self)

    def l1_on_l2_on(self):
        """ Both pumps on """
        seq.stop()
        self.s1('OUT')
        self.s2('OUT')
        shot_seq = []
        shot_seq.append([self.c1_on, 1, 0, 0])
        shot_seq.append([self.c2_on, 0, 0, 0])
        seq.sequence.put_seq(shot_seq)
        time.sleep(0.03)
        self.print_status()
        seq.start()
        return

    def l1_on_l2_off(self):
        """ Pump 1 on, pump 2 off """
        seq.stop()
        self.s1('OUT')
        self.s2('IN')
        shot_seq = []
        shot_seq.append([self.c1_on, 1, 0, 0])
        shot_seq.append([self.c2_on, 0, 0, 0])
        seq.sequence.put_seq(shot_seq)
        time.sleep(0.03)
        self.print_status()
        seq.start()
        return

    def l1_off_l2_on(self):
        """ Pump 1 off, pump 2 on """
        seq.stop()
        self.s1('IN')
        self.s2('OUT')
        shot_seq = []
        shot_seq.append([self.c1_on, 1, 0, 0])
        shot_seq.append([self.c2_on, 0, 0, 0])
        seq.sequence.put_seq(shot_seq)
        time.sleep(0.03)
        self.print_status()
        seq.start()
        return

    def l1_off_l2_off(self):
        """ Both pump off """
        seq.stop()
        self.s1('IN')
        self.s2('IN')
        shot_seq = []
        shot_seq.append([self.c1_off, 1, 0, 0])
        shot_seq.append([self.c2_off, 0, 0, 0])
        seq.sequence.put_seq(shot_seq)
        time.sleep(0.03)
        self.print_status()
        seq.start()
        return



#class PPM_Record():
#    def __init__(self, pvname='IM3L0:PPM:SPM:VOLT_BUFFER_RBV',time=1, 
#                   filename=None):
#        self.collection_time = time
#        self.arr = []
#        self.pvname = pvname
#        self.sig = EpicsSignalRO(pvname)
#        try:
#            self.sig.wait_for_connection(timeout=3.0)
#        except TimeoutError:
#            print(f'Could not connect to data PV {pvname}, timed out.')
#            print('Either on wrong subnet or the ioc is off.')
#        if filename is not None:
#            self.filename = filename
#        else:
#            self.setFilename()
#
#    def cb10(self, value, **kwargs):
#        #print('value ',value)
#        # Downsample to 10Hz from 1000Hz
#        for i in range(10):
#            self.arr.append(np.mean(value[100*i:100*(i+1)]))
#        #print('{} values collected'.format(len(self.arr)))
#
#
#    def cb100(self, value, **kwargs):
#        # Downsample to 100Hz from 1000Hz
#        for i in range(100):
#            self.arr.append(np.mean(value[10*i:10*(i+1)]))
#
#    def cb(self, value, **kwargs):
#        self.arr.append(value)
#
#    def setCollectionTime(self, ctime=None):
#        self.collection_time = ctime
#
#    def collectData(self, rate=10):
#        if rate==100:
#            cbid = self.sig.subscribe(self.cb100)
#        elif rate==10:
#            cbid = self.sig.subscribe(self.cb10)
#        else:
#            cbid = self.sig.subscribe(self.cb)
#        time.sleep(self.collection_time)
#        self.sig.unsubscribe(cbid)
#
#    def setFilename(self, basename=None, useTime=False):
#        if basename is None:
#            basename = self.pvname.split(':')[0]+'_powermeter_data'
#        if useTime:
#            self.filename = basename+'_{}'.format(int(time.time()))
#        else:
#            self.filename = basename
#        
#    def writeFile(self):
#        #print('saving to {}'.format(self.filename))
#        with open(self.filename, 'w') as fd:
#            for value in self.arr:
#                print(value, file=fd)
#        #if len(self.arr) == 0:
#        #    print('Warning: no data points collected! File is empty!')
#        self.arr = []
#
#
#class ImagerStats3():
#
#    def __init__(self, imager=None):
#        try:
#            self.imager = imager
#            self.prefix = imager.prefix
#
#        except AttributeError:
#            self.imager = camviewer.im1l0
#            self.prefix = 'IM1L0:XTES:CAM:'
#            print('defaulting to IM1L0')
#       
#        self.initialize()
#
#    def initialize(self):
#        self.imager_name = self.prefix[:5]
#        self.image_stream = self.prefix + 'IMAGE3:'
#        self.image3 = plugins.ImagePlugin(prefix=self.image_stream,
#                name=self.imager_name+'_image3', parent=self.imager)
#        self.roi = plugins.ROIPlugin(prefix=self.image_stream+'ROI:',
#                name=self.imager_name+'_roi', parent=self.image3)
#        self.proc = plugins.ProcessPlugin(prefix=self.image_stream+'Proc:',
#                name=self.imager_name+'_proc', parent=self.image3)
#        self.stats = self.imager.stats3
#        self.binX = EpicsSignal(self.image_stream+'ROI:BinX', name='omitted')
#        self.binY = EpicsSignal(self.image_stream+'ROI:BinY', name='omitted')
#        self.saveBackground = EpicsSignal(self.image_stream+'Proc:SaveBackground', name='omitted') 
#
#    def setImager(self, imager):
#        try:
#            self.prefix = imager.prefix
#        except AttributeError:
#            print('Imager not set')
#
#        self.initialize()
#
#    def setup_binning(self, binning):
#        self.binX.set(binning)
#        self.binY.set(binning)
#        self.roi.scale.set(binning**2)
#
#    def prepare(self, take_background=False):
#
#        # set up ports
#        self.proc.nd_array_port.set('CAM')
#        self.roi.nd_array_port.set('IMAGE3:Proc')
#        self.image3.nd_array_port.set('IMAGE3:ROI')
#        self.stats.nd_array_port.set('IMAGE3:Proc')
#
#        # set default binning to 2
#        self.setup_binning(2)
#
#        # enable all the things
#        self.image3.enable.set(1)
#        self.roi.enable.set(1)
#        self.proc.enable.set(1)
#
#        if take_background:
#            self.take_background()
#
#        # apply background
#        self.proc.enable_background.set(1)
#
#        # enable stats
#        self.stats.compute_statistics.set(1)
#        self.stats.compute_centroid.set(1)
#        self.stats.enable.set(1)
#
#        # get noise level
#        time.sleep(.1)
#        sigma = self.stats.sigma.get()
#
#        # set offset to negative sigma
#        print(sigma)
#        self.proc.offset.set(-sigma)
#
#        # switch stats over to ROI stream
#        self.stats.nd_array_port.set('IMAGE3:ROI')
#
#        # set scale and limits
#        self.proc.scale.set(1)
#        self.proc.low_clip.set(0)
#        # disable high clipping for now, but enable low clipping
#        self.proc.enable_low_clip.set(1)
#        self.proc.enable_high_clip.set(0)
#        # apply scale and offset
#        self.proc.enable_offset_scale.set(1)
#
#    def get_centroids(self):
#
#        centroids = self.stats.centroid.get()
#        centroid_x = centroids.x
#        centroid_y = centroids.y
#
#        return centroid_x, centroid_y
#
#    def disable_background(self):
#        self.proc.enable_background.set(0)
#        self.proc.enable_offset_scale.set(0)
#        self.proc.enable_low_clip.set(0)
#        self.proc.enable_high_clip.set(0)
#
#    def stop(self):
#        self.stats.enable.set(0)
#
#    def take_background(self, num_images=100):
#        
#        # set minimum number of images to 20
#        if num_images <= 20:
#            num_images = 20
#        
#        # turn off background subtraction
#        self.proc.enable_background.set(0)
#        self.proc.enable_offset_scale.set(0)
#        self.proc.enable_low_clip.set(0)
#        self.proc.enable_high_clip.set(0)
#        
#        # turn on averaging
#        self.proc.filter_type.set('RecursiveAve')
#        self.proc.num_filter.set(num_images)
#        # following sets to array n only
#        self.proc.filter_callbacks.set(1)
#        self.proc.auto_reset_filter.set(1)
#        self.proc.enable_filter.set(1)
#
#        # wait until we have at least one averaged image
#        print('waiting for averaging to finish...')
#        if self.proc.num_filtered.get() < 10:
#            while self.proc.num_filtered.get() <= 10:
#                time.sleep(.1)
#                #print(self.proc.num_filtered.get())
#            while self.proc.num_filtered.get() > 10:
#                time.sleep(.1)
#                #print(self.proc.num_filtered.get())
#        else:
#            while self.proc.num_filtered.get() > 10:
#                time.sleep(.1)
#                #print(self.proc.num_filtered.get())
#        print('finished acquiring')
#        # save background
#        #self.proc.save_background.set(1)
#        self.saveBackground.set(1)
#
#        # turn off averaging
#        self.proc.enable_filter.set(0)


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
            self.imagerh5.enable.set(1)
        if pathName is not None:
            self.imagerh5.file_path.set(pathName)
        elif len(self.imagerh5.file_path.get())==0:
            #this is a terrible hack.
            iocdir=self.imager.prefix.split(':')[0].lower()
            camtype='opal'
            if (self.imager.prefix.find('PPM')>0): camtype='gige'
            self.imagerh5.file_path.set('/reg/d/iocData/ioc-%s-%s/images/'%(iocdir, camtype))
        if baseName is not None:
            self.imagerh5.file_name.set(baseName)
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
            self.imagerh5.file_name.set('%s_Run%03d'%(expname, runnr+1))

        self.imagerh5.file_template.set('%s%s_%d.h5')
        self.imagerh5.auto_increment.set(1)
        self.imagerh5.file_write_mode.set(2)
        if nImages is not None:
            self.imagerh5.num_capture.set(nImages)
        if nSec is not None:
            if self.imager.acquire.get() > 0:
                rate = self.imager.array_rate.get()
                self.imagerh5.num_capture.set(nSec*rate)
            else:
                print('Imager is not acquiring, cannot use rate to determine number of recorded frames')

    def write(self, nImages=None):
        if nImages is not None:
            self.imagerh5.num_capture.set(nImages)
        if self.imager.acquire.get() == 0:
            self.imager.acquire.set(1)
        self.imagerh5.capture.set(1)

    def write_wait(self, nImages=None):
        while (self.imagerh5.num_capture.get() > 
               self.imagerh5.num_captured.get()):
            time.sleep(0.25)
#            print(self.imagerh5.num_captured.get())
#            print(self.imager.num_exposures_counter.get())
#            print(self.imager.num_exposures.get())

#class ImagerStats():
#    def __init__(self, imager=None):
#        try:
#            self.imgstat = imager.stats1
#        except:
#            self.imgstat = None
#            
#    def setImager(self, imager):
#        self.imgstat = imager.stats1
#
#    def stop(self):
#        self.imgstat.enable.set(0)
#
#    def setThreshold(self, inSigma=1):
#        self.imgstat.enable.set(1)
#        computeStat = self.imgstat.compute_statistics.get()
#        self.imgstat.compute_statistics.set(1)
#        mean = self.imgstat.mean_value.get()
#        sigma = self.imgstat.sigma.get()
#        self.imgstat.centroid_threshold.set(mean+sigma*nSigma)
#        self.imgstat.compute_statistics.set(computeStat)
#
#    def prepare(self, threshold=None):
#        self.imager.acquire.set(1)
#        if self.imgstat.enable.get() != 'Enabled':
#            self.imgstat.enable.set(1)
#        if threshold is not None:
#            if self.imgstat.compute_centroid.get() != 'Yes':
#                self.imgstat.compute_centroid.set(1)
#            self.imgstat.centroid_threshold.set(threshold)
#        self.imgstat.compute_profile.set(1)
#        self.imgstat.compute_centroid.set(1)
#
#    def status(self):
#        print('enabled:', self.imgstat.enable.get())
#        if self.imgstat.enable.get() == 'Enabled':
#            if self.imgstat.compute_statistics.get() == 'Yes':
#                #IM1L0:XTES:CAM:Stats1:MeanValue_RBV
#                #IM1L0:XTES:CAM:Stats1:SigmaValue_RBV
#                print('Mean', self.imgstat.mean_value.get())
#                print('Sigma', self.imgstat.sigma.get())
#            if self.imgstat.compute_centroid.get() == 'Yes':
#                print('Threshold', self.imgstat.centroid_threshold.get())
#                #IM1L0:XTES:CAM:Stats1:CentroidX_RBV
#                #IM1L0:XTES:CAM:Stats1:CentroidY_RBV
#                #IM1L0:XTES:CAM:Stats1:SigmaX_RBV
#                #IM1L0:XTES:CAM:Stats1:SigmaY_RBV
#                print('X,y', self.imgstat.centroid.get())
#                print('sigma x', self.imgstat.sigma_x.get())
#                print('sigma y', self.imgstat.sigma_y.get())
#            if self.imgstat.compute_profile.get() == 'Yes':
#                #IM1L0:XTES:CAM:Stats1:CursorX
#                #IM1L0:XTES:CAM:Stats1:CursorY
#                print('profile cursor values: ',self.imgstat.cursor.get())
#                #IM1L0:XTES:CAM:Stats1:ProfileAverageX_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileAverageY_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileThresholdX_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileThresholdY_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileCentroidX_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileCentroidY_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileCursorX_RBV
#                #IM1L0:XTES:CAM:Stats1:ProfileCursorY_RBV
#                print('profile cursor: ',self.imgstat.profile_cursor.get())
#                print('profile centroid: ',self.imgstat.profile_centroid.get())
#                if self.imgstat.compute_centroid.get() == 'Yes':
#                    print('profile threshold: ',self.imgstat.profile_threshold.get())
#                    print('profile avergage: ',self.imgstat.profile_average.get())


# Syringe pump setup
from pcdsdevices.analog_signals import Acromag

class Syringe_Pump():
    def __init__(self):
        self.signals = Acromag('XPP:USR', name='syringe_pump_channels')
        self.base = self.signals.ao1_0
        self.ttl = self.signals.ao1_1
    def on(self):
        ttl = self.ttl.get()
        self.base.put(5)
        if ttl == 5:
            self.ttl.put(0)
            print('Initialized and on')
        if ttl == 0:
            self.ttl.put(5)
            sleep(1)
            self.ttl.put(0)
            print("Syringe pump is on")
    def off(self):
        ttl = self.ttl.get()
        self.base.put(5)
        if ttl == 0:
            self.ttl.put(5)
            sleep(1)
            self.ttl.put(0)
            print("Syringe pump is off")
        if ttl == 5:
            self.ttl.put(0)

#RS-232 operation
from telnetlib import Telnet
import re

class SyringePumpSerial():
    status_dict = {
        'I': 'Infusing',
        'W': 'Withdrawing',
        'S': 'Program Stopped',
        'P': 'Program Paused',
        'T': 'Timed Pause Phase',
        'U': 'Waiting for Trigger',
        'X': 'Purging',
    }

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def cmd(self, command):
       print(self.send_command(command))

    def send_command(self, command):
        with Telnet(self.host,self.port) as t:
            t.write(command.encode()+b'\r')
            msg = t.read_some().decode('ascii')
            regex = re.search('\x0200(\D)(.*)\x03', msg)
            status = self.status_dict[regex.group(1)]
            return f"""\
Command:\t{command}
Response:\t{regex.group(2)}
Status:\t\t{status}
"""

    def run(self):
        self.cmd('RUN')

    def stop(self):
        self.cmd('STP')

    def __call__(self, command):
        self.cmd(command)

    def __repr__(self):
        return self.send_command('')

    def timed(self, seconds):
        self.run()
        sleep(seconds)
        self.stop()

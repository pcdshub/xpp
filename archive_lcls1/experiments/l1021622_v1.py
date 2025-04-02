import numpy as np
from ophyd import FormattedComponent as FCpt
from ophyd.device import Component as Cpt
from ophyd.status import DeviceStatus
from prettytable import PrettyTable
from hutch_python.utils import safe_load
from pcdsdevices.device_types import Newport, PMC100, IMS, BeckhoffAxis
from xpp.delay_stage import FakeDelay
from xpp.db import scan_pvs
from xpp.db import daq, pp
from pcdsdevices.lasers.shutters import LaserShutter
from pcdsdevices.lasers.shutters import LaserFlipper
from ophyd.sim import motor as fake_motor
from ophyd import EpicsMotor
from pcdsdevices.epics_motor import SmarAct, EpicsMotorInterface
from pcdsdevices.device import GroupDevice
from pcdsdevices.epics_motor import IMS
from pcdsdevices.interface import BaseInterface
from pcdsdevices.pseudopos import (PseudoPositioner, PseudoSingleInterface,
                        pseudo_position_argument, real_position_argument)

ana_distance = 1000


class Ixsspec(BaseInterface, PseudoPositioner):
    tab_component_names = True
    #eta = FCpt(IMS, '{self._prefix_eta}', kind='normal')
    #kappa = FCpt(IMS, '{self._prefix_kappa}', kind='normal')
    #phi = FCpt(IMS, '{self._prefix_phi}', kind='normal')
    v_ana_chi = Cpt(PseudoSingleInterface, kind='normal', name='virtual_ana_chi')
    v_ana_z = Cpt(PseudoSingleInterface, kind='normal', name='virtual_ana_z')
    v_ana_y = Cpt(PseudoSingleInterface, kind='normal', name='virtual_ana_y')
    v_det_chi = Cpt(PseudoSingleInterface, kind='normal', name='virtual_det_chi')
    v_ana_th = Cpt(PseudoSingleInterface, kind='normal', name='virtual_ana_th')
    v_ana_y = Cpt(PseudoSingleInterface, kind='normal', name='virtual_ana_y')
    v_det_x = Cpt(PseudoSingleInterface, kind='normal', name='virtual_det_x')
    v_det_y = Cpt(PseudoSingleInterface, kind='normal', name='virtual_det_y')
    v_det_rot = Cpt(PseudoSingleInterface, kind='normal', name='virtual_det_rot')
    v_det_tth = Cpt(PseudoSingleInterface, kind='normal', name='virtual_det_tth')
    v_ana_E = Cpt(PseudoSingleInterface, kind='normal', name='virtual_analyzer_energy')
    v_ana_tth = Cpt(PseudoSingleInterface, kind='normal', name='virtual_analyzer_twotheta')



    ana_z = Cpt(IMS, 'HXR:PRT:01:MMS:01', name='ana_z')
    ana_y = Cpt(IMS, 'HXR:PRT:01:MMS:02', name='ana_y')
    ana_th = Cpt(IMS, 'HXR:PRT:01:MMS:04', name='ana_th')
    ana_chi = Cpt(IMS, 'HXR:PRT:01:MMS:03', name='ana_chi')
    spe_det_x = Cpt(Newport, 'XPP:USR:PRT:MMN:01', name='spe_det_x')
    spe_det_y = Cpt(IMS, 'XPP:USR:MMS:02', name='spe_det_y')
    spe_det_z = Cpt(IMS, 'XPP:USR:MMS:18', name='spe_det_z')
    spe_det_chi = Cpt(IMS, 'XPP:USR:MMS:29', name='spe_det_chi')
    spe_det_tth = Cpt(IMS, 'XPP:USR:MMS:17', name=' spe_det_tth')
    spe_det_rot = Cpt(IMS, 'XPP:USR:MMS:19', name='spe_det_rot')
    def __init__(self):
        self.ana_z = ana_z
        self.ana_y = ana_y
        self.ana_th = ana_th
        self.ana_chi = ana_chi
        self.spe_det_x = spe_det_x
        self.spe_det_y = spe_det_y
        self.spe_det_z = spe_det_z
        self.spe_det_chi = spe_det_chi
        self.spe_det_tth = spe_det_tth
        self.spe_det_rot = spe_det_rot

    ana_E = 11.215
    radius = 1000

    @property
    def v_ana_z_coord(self):
        """Get the azimuthal angle, an offset from eta."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_ana_z

    @property
    def v_ana_chi_coord(self):
        """Get the elevation (polar) angle, a composition of eta and kappa."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_ana_chi

    @property
    def v_ana_y_coord(self):
        """Get the sample rotation angle, an offset from phi to keep it."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_ana_y

    def v_ana_th_coord(self):
        """Get the azimuthal angle, an offset from eta."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_ana_th

    @property
    def v_det_x_coord(self):
        """Get the elevation (polar) angle, a composition of eta and kappa."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_det_x

    @property
    def v_det_y_coord(self):
        """Get the sample rotation angle, an offset from phi to keep it."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_det_x

    @property
    def v_ana_E_coord(self):
        """Get the sample rotation angle, an offset from phi to keep it."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_ana_E  

    @property
    def v_ana_tth_coord(self):
        """Get the sample rotation angle, an offset from phi to keep it."""
        v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth = self.r_to_spe()
        return v_ana_tth
    
    def e_to_r():
        return
    
    def spe_to_r(self,v_ana_chi = None,v_ana_z = None, v_ana_y = None, v_ana_th = None,v_det_chi = None, v_det_x = None, v_det_y = None, v_det_tth = None, v_ana_E = None,v_ana_tth = None):
        if v_ana_chi is None:
            v_ana_chi = self.v_ana_chi_coord
        if v_ana_z is None:
            v_ana_z = self.v_ana_z_coord
        if v_ana_y is None:
            v_ana_y = self.v_ana_y_coord
        if v_ana_th is None:
            v_ana_th = self.v_ana_th_coord
        if v_det_x is None:
            v_det_x = self.v_det_x_coord
        if v_det_y is None:
            v_det_y = self.v_det_y_coord
        if v_det_chi is None:
            v_det_chi = self.v_det_chi_coord
        if v_det_tth is None:
            v_det_tth = self.v_det_tth_coord

        ana_th = np.arcsin(11179.82/v_ana_E)/np.pi*180
        ana_y = 2*radius * np.sin(ana_th/180*np.pi)
        ana_z = v_ana_z
        ana_chi = v_ana_chi
        spe_det_y = 4*radius*np.cos(ana_th/180*np.pi)*(np.sin(ana_th/180*np.pi))**2
        spe_det_x = 4*radius*np.sin(ana_th/180*np.pi)*(np.cos(ana_th/180*np.pi))**2
        spe_det_rot = v_det_chi
        spe_det_tth = v_det_tth
        return ana_z,ana_y,ana_th,ana_chi,spe_det_x, det_spe_y,spe_det_z,spe_det_chi,spe_det_tth,spe_det_rot

    def r_to_spe(self,ana_chi = None,ana_z = None, ana_y = None,ana_th = None, spe_det_tth = None, spe_det_chi = None, spe_det_x = None, spe_det_y = None):
        if ana_chi is None:
            ana_chi = self.ana_chi.position
        if ana_z is None:
            ana_z = self.ana_z.position
        if ana_y is None:
            ana_y = self.ana_y.position
        if ana_th is None:
            ana_th = self.ana_th.position
        if spe_det_x is None:
            spe_det_x = self.spe_det_x.position
        if spe_det_y is None:
            spe_det_y = self.spe_det_y.position
        if spe_det_chi is None:
            spe_det_chi = self.spe_det_chi.position
        if spe_det_tth is None:
            spe_det_tth = self.spe_det_tth.position
        v_ana_chi = 2*ana_th-90
        v_ana_z = ana_z
        v_ana_y = radius + ana_y 
        v_ana_th = ana_th
        v_det_tth = spe_det_tth
        v_det_chi = spe_det_chi
        v_det_x = spe_det_x#+offset for COR issue
        v_det_y = spe_det_y# +offset for COR issue  
        v_ana_E = 11183.75/np.sin(ana_th/180*np.pi)  
        v_ana_tth = 2*ana_chi
        return v_ana_chi,v_ana_z, v_ana_y, v_ana_th, v_det_tth, v_det_chi, v_det_x, v_det_y, v_ana_E,v_ana_tth


    def forward(self,pseudo_pos):

        return self.RealPosition()
    def inverse(self,real_pos):
        return self.RealPosition()
    def move(self, position, wait=True, timeout=None, moved_cb=None):
        """
        Move to a specified position, optionally waiting for motion to
        complete.

        Checks for the motor step, and ask the user for confirmation if
        movement step is greater than default one.
        """
        
        return super().move(position, wait=wait, timeout=timeout,
                                moved_cb=moved_cb)
       
class User():
    userdevice = 0    


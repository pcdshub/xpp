import numpy as np

from ophyd import FormattedComponent as FCpt
from ophyd import Component as Cpt

from pcdsdevices.device import Device
from pcdsdevices.device_types import Newport, IMS
from pcdsdevices.interface import BaseInterface, FltMvInterface
from pcdsdevices.pseudopos import (PseudoPositioner, PseudoSingleInterface,
        pseudo_position_argument, real_position_argument)

hc_over_2d = 11184.161

class Ixs_spectrometer_energy(FltMvInterface, PseudoPositioner):
    # Real axis
    analyzer_th = Cpt(IMS, 'HXR:PRT:01:MMS:04', name='ana_th')
    analyzer_y = Cpt(IMS, 'HXR:PRT:01:MMS:02', name='ana_y')
    detector_tth = Cpt(Newport, 'XPP:USR:MMS:17', name='spe_det_tth')
    detector_x = Cpt(Newport, 'XPP:USR:PRT:MMN:01', name='spe_det_x')
    detector_y = Cpt(IMS, 'XPP:USR:MMS:02', name='spe_det_y')

    # Pseudo axis
    energy = Cpt(PseudoSingleInterface, name='energy',
                 egu='eV', limits=(11210, 11225))

    tab_component_names = True

    def __init__(self,
                 analyzer_d0=1000,
                 detector_d0=1000,
                 analyzer_radius=1000,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.analyzer_d0 = analyzer_d0
        self.analyzer_radius = analyzer_radius
        self.detector_d0 = detector_d0
        return

    def energy_to_real(self, energy):
        radius = self.analyzer_radius
        analyzer_th = np.arcsin(hc_over_2d/energy)
        analyzer_y = radius * np.sin(analyzer_th)
        analyzer_y = analyzer_y - self.analyzer_d0

        detector_tth = 2 * (np.pi/2-analyzer_th)
        detector_y = analyzer_th * (1-np.cos(analyzer_th))
        detector_x = detector_y * np.sin(detector_tth)

        analyzer_th = np.rad2deg(analyzer_th)
        detector_tth = np.rad2deg(detector_tth)

        """
        Canonical calculation, but does not apply here because the det_x and
        det_y are not cartesian with the way the motors are assembled.
        """
        #detector_x = 2 * radius * np.cos(analyzer_th) * np.sin(analyzer_th)**2
        #detector_y = 2 * radius * np.sin(analyzer_th) * np.cos(analyzer_th)**2
        #detector_y = detector_y - self.detector_d0 # needs to be computed
        return analyzer_th, analyzer_y, detector_x, detector_y, detector_tth

    def analyzer_th_to_energy(self, analyzer_th):
        analyzer_th = np.deg2rad(analyzer_th)
        energy = hc_over_2d / np.sin(analyzer_th)
        return energy

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        analyzer_th, analyzer_y, detector_x, detector_y, detector_tth = \
            self.energy_to_real(pseudo_pos.energy)
        return self.RealPosition(analyzer_th = analyzer_th,
                                 analyzer_y = analyzer_y,
                                 detector_x = detector_x,
                                 detector_y = detector_y,
                                 detector_tth = detector_tth)

    @real_position_argument
    def inverse(self, real_pos):
        energy = self.analyzer_th_to_energy(real_pos.analyzer_th)
        return self.PseudoPosition(energy=energy)



class Ixs_spectrometer_tth(FltMvInterface, PseudoPositioner):
    """
    Note : 2-theta computations are not complete with respect to
    the current setup. But we realized that the current configuration
    does not allow to go to large enough 2-theta. Some axis, in
    particular analyzer_y would need much longer travel range.
    """
    # Real axis
    analyzer_th = Cpt(IMS, 'HXR:PRT:01:MMS:04', name='ana_th')
    analyzer_chi = Cpt(IMS, 'HXR:PRT:01:MMS:03', name='ana_chi')
    analyzer_y = Cpt(IMS, 'HXR:PRT:01:MMS:02', name='ana_y')
    analyzer_z = Cpt(IMS, 'HXR:PRT:01:MMS:01', name='ana_z')
    detector_chi = Cpt(Newport, 'XPP:USR:MMS:29', name='spe_det_chi')

    # Pseudo axis
    tth = Cpt(PseudoSingleInterface, name='two_theta',
              egu='deg', limits=(-180,180))

    tab_component_names = True

    def __init__(self,
                 analyzer_d0=1000,
                 detector_d0=1000,
                 analyzer_radius=1000,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.analyzer_d0 = analyzer_d0
        self.analyzer_radius = analyzer_radius
        self.detector_d0 = detector_d0
        return

    def tth_to_real(self, tth, analyzer_th):
        tth = np.deg2rad(tth)

        self.analyzer_d0 = (1 + np.abs(np.cos(tth))) * radius

        # ##############
        analyzer_th = np.deg2rad(analyzer_th)
        radius = self.analyzer_radius
        analyzer_chi = tth - np.pi/2

        #analyzer_y = radius * np.sin(analyzer_th) * (1-np.sin(analyzer_chi))
        analyzer_y = radius * np.sin(analyzer_th)
        analyzer_y = analyzer_y - self.analyzer_d0
        analyzer_z = -radius * np.sin(analyzer_th) * np.cos(analyzer_chi)
        detector_chi = tth - np.pi/2

        analyzer_th = np.rad2deg(analyzer_th)
        analyzer_chi = np.rad2deg(analyzer_chi)
        detector_chi = np.rad2deg(detector_chi)
        return analyzer_th, analyzer_chi, analyzer_y, analyzer_z, detector_chi

    def analyzer_chi_to_tth(self, analyzer_chi):
        return analyzer_chi + 90

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        analyzer_th, analyzer_chi, analyzer_y, analyzer_z, detector_chi = \
            self.tth_to_real(pseudo_pos.tth, self.analyzer_th.position)
        return self.RealPosition(analyzer_th = analyzer_th,
                                 analyzer_chi = analyzer_chi,
                                 analyzer_y = analyzer_y,
                                 analyzer_z = analyzer_z,
                                 detector_chi = detector_chi)

    @real_position_argument
    def inverse(self, real_pos):
        tth = self.analyzer_chi_to_tth(real_pos.analyzer_chi)
        return self.PseudoPosition(tth=tth)


class Ixs_spectrometer(BaseInterface, Device):
    # twotheta = FCpt(Ixs_spectrometer_tth, '')
    energy = FCpt(Ixs_spectrometer_energy, '')

    tab_component_names = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.E = self.energy.energy
        #self.tth = self.twotheta.tth

        self.energy.analyzer_d0 = 1000
        self.energy.detector_d0 = 1000
        #self.twotheta.analyzer_d0 = 1000
        #self.twotheta.detector_d0 = 1000


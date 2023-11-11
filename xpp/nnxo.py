from time import sleep
from types import SimpleNamespace
import sys
sys.path.append('/cds/group/pcds/pyps/apps/hutch-python/xpp/xpp')

from pcdsdevices.device_types import IMS
import aerotech_ensemble as aerotech



class Nnxo(SimpleNamespace):
    def __init__(self, ax_names, ensemble_ip):
        self._ensemble_ip = ensemble_ip
        self._ax_names = ax_names

        self.load_motors()
        return

    def connect(self, set_default=True):
        self.ens = aerotech.Ensemble(
            self._ensemble_ip,
            ax_names=self._ax_names
        )
        sleep(1)
        if set_default:
            self.set_default_params()


    def set_default_params(self):
        if not hasattr(self, 'ens'):
            print('Must connect to the ensemble first. Run nnxo.connect()')
            return

        # axis velocities
        self.ens.z1.velocity = 0.1
        self.ens.z2.velocity = 0.1
        self.ens.x2.velocity = 0.1
        self.ens.th1.velocity = 0.05
        self.ens.th2.velocity = 0.05
        self.ens.th3.velocity = 0.05
        
        # axis accelerations
        self.ens.z1.accel = 0.01
        self.ens.z2.accel = 0.01
        self.ens.x2.accel = 0.01
        self.ens.th1.accel = 0.001
        self.ens.th2.accel = 0.001
        self.ens.th3.accel = 0.001
        
        # combined motion acceleration
        self.ens.accel = 0.002
        return


    def disconnect(self):
        nnxo.ens.comm.sock.close()
        return


    def load_motors(self):
        self.m3x = IMS('XPP:USR:PRT:MMS:25', name='m3x')
        self.m2chi = IMS('XPP:USR:PRT:MMS:26', name='m2chi')
        self.m1chi = IMS('XPP:USR:PRT:MMS:27', name='m1chi')
        self.crlx = IMS('XPP:USR:PRT:MMS:28', name='crlX')
        self.crly = IMS('XPP:USR:PRT:MMS:29', name='crlY')





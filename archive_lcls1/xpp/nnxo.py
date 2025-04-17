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


    def connect(self, set_default=True, run_sentinel=True):
        if hasattr(self, 'ens'):
            self.disconnect()
            sleep(2)

        self.ens = aerotech.Ensemble(
            self._ensemble_ip,
            ax_names = self._ax_names,
            sentinel = True
        )
        sleep(1)
        
        if set_default:
            self.set_default_params()
        
        if run_sentinel:
            self.ens.sentinel.run()
        return


    def set_default_params(self):
        if not hasattr(self, 'ens'):
            print('Must connect to the ensemble first. Run nnxo.connect()')
            return

        # axis velocities
        self.ens.z1.velocity = 0.1
        self.ens.z2.velocity = 0.1
        self.ens.x2.velocity = 0.1
        self.ens.th1.velocity = 0.02
        self.ens.th2.velocity = 0.02
        self.ens.th3.velocity = 0.02
        
        # axis accelerations
        self.ens.z1.accel = 0.05
        self.ens.z2.accel = 0.05
        self.ens.x2.accel = 0.05
        self.ens.th1.accel = 0.005
        self.ens.th2.accel = 0.005
        self.ens.th3.accel = 0.005
        
        # combined motion acceleration
        self.ens.accel = 0.002

        # scurve
        self.ens.scurve = 50
        return


    def set_high_speed(self):
        # axis velocities
        self.ens.z1.velocity = 0.5
        self.ens.z2.velocity = 0.5
        self.ens.x2.velocity = 0.5
        self.ens.th1.velocity = 0.1
        self.ens.th2.velocity = 0.1
        self.ens.th3.velocity = 0.1
        
        # axis accelerations
        self.ens.z1.accel = 0.5
        self.ens.z2.accel = 0.5
        self.ens.x2.accel = 0.5
        self.ens.th1.accel = 0.1
        self.ens.th2.accel = 0.1
        self.ens.th3.accel = 0.1
        return


    def disconnect(self):
        self.ens.comm.sock.close()
        return


    def load_motors(self):
        self.x3 = IMS('XPP:USR:PRT:MMS:25', name='x3')
        self.chi2 = IMS('XPP:USR:PRT:MMS:26', name='chi2')
        self.chi1 = IMS('XPP:USR:PRT:MMS:27', name='ch1i')
        self.crlx = IMS('XPP:USR:PRT:MMS:28', name='crlx')
        self.crly = IMS('XPP:USR:PRT:MMS:29', name='crly')





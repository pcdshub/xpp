import numpy as np
import sys
sys.path.append('/cds/group/pcds/pyps/apps/hutch-python/xpp/experiments')

import ixs_spec


class User():
    spec = ixs_spec.Ixs_spectrometer(name='ixs_spec')

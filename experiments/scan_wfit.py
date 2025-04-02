import numpy as np
import matplotlib.pyplot as plt
import lmfit 
from bluesky.callbacks import LiveFit
from bluesky.callbacks.mpl_plotting import LivePlot, LiveFitPlot


def gaussian(x, A, sigma, x0):
    return A*np.exp(-(x - x0)**2/(2 * sigma**2))

def dscan_gaussian(det,motor, start, end, nsteps, nEvents, records=None):
    model = lmfit.Model(gaussian)
    init_guess = {'A': 2,'sigma': lmfit.Parameter('sigma', 3, min=0),'x0': 21.2}
    detname=det.name+'_mean'
    motorname=motor.description.parent.name    
    lvf = LiveFit(model, detname, {'x': motorname}, init_guess)
    fig, ax = plt.subplots() 
    lfp = LiveFitPlot(lvf, ax=ax, color='r')
    lp = LivePlot(detname, motor, ax=ax, marker='o', linestyle='none')
    RE(bp.daq_dscan([det], motor,start,end,nsteps,events=nEvents,record=records ),[lp,lfp])
    return lvf


    def dscan_gaussian(self,det,motor, start, end, nsteps, nEvents, records=None):
        import numpy as np
        import matplotlib.pyplot as plt
        import lmfit 
        from bluesky import RunEngine
        from hutch_python import plan_defaults
        from bluesky.callbacks import LiveFit
        from bluesky.callbacks.mpl_plotting import LivePlot, LiveFitPlot
        RE = RunEngine({})
        bp = plan_defaults.plans

        def gaussian(x, A, sigma, x0):
            return A*np.exp(-(x - x0)**2/(2 * sigma**2))

        model = lmfit.Model(gaussian)
        init_guess = {'A': 2,'sigma': lmfit.Parameter('sigma', 3, min=0),'x0': 21.2}
        detname=det.name+'_mean'
        motorname=motor.description.parent.name    
        lvf = LiveFit(model, detname, {'x': motorname}, init_guess)
        fig, ax = plt.subplots() 
        lfp = LiveFitPlot(lvf, ax=ax, color='r')
        lp = LivePlot(detname, motor, ax=ax, marker='o', linestyle='none')
        RE(bp.daq_dscan([det], motor,start,end,nsteps,events=nEvents,record=records ),[lp,lfp])
  
        return lvf ,m, detname


#ask Leland if issues.
import time
import numpy as np
def build_energies(parms):
    energies=np.array([parms[0]])
    for i in np.arange(1,len(parms),2):
        energies=np.hstack([energies,np.arange(energies[-1]+parms[i+1],parms[i],parms[i+1])])
    return np.sort(energies)
def continuous_scan(energies,pointTime=1,ccm=None):
    i=0
    j=1
    #energies=np.divide(energies,1000)
    initial_energy=ccm.calc.energy_with_vernier.position
    try:
        
        while 1==1:
            #print(str(energies[i]))
            ccm.calc.energy_with_vernier.mv(energies[i])
            time.sleep(pointTime)
            if i==len(energies)-1:
                j=-1
            elif i==0:
                j=1
            i=i+j
    except KeyboardInterrupt:
        print('Scan end signal received. Returning ccm to energy before scan: '+ str(initial_energy))
        ccm.calc.energy_with_vernier.mv(initial_energy)
        
def continuous_gscan(ccm,*argv):
    """
    This function behaves like the spec version of gscan.
    Arguments are formatted (in keV!) as: starting energy, second energy, point spacing, third energy, point spacing... time per point.
    e.g. gscan(7.105,7.115,0.0001,7.125,0.0005,7.130,0.001,1.5)
    will make a scan from 7105 to 7115 by 0.1 then to 7125 by 0.5 then 7130 by 1eV. All measured for 1.5 seconds.
    """
    energies=build_energies(argv[:-1])
    time=argv[-1]
    continuous_scan(energies,time,ccm)
def continuous_gscan_from_file(file,ccm,pointTime):
    """
    This function recieves comma-delimited file of energies and uses those energies for a CCM vernier scan.
    Arguments are filename, ccm, time per point.
    """
    
    energies=np.loadtxt(file,delimiter=',')
    time=pointTime
    continuous_scan(energies,time,ccm)
    
 
        

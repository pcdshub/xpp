"""
General imports and setup
"""
import numpy as np
from statistics import mean
import pandas as pd
from functools import partial
from scipy.stats import pearsonr
import logging 
import random
from random import randint

import matplotlib.pyplot as plt
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.plan_stubs import open_run, close_run, subscribe, unsubscribe
from bluesky.plans import *
from bluesky.preprocessors import run_wrapper
from bluesky.plan_stubs import mv, trigger_and_read 
from bluesky.utils import install_qt_kicker
from bluesky.simulators import summarize_plan
from bluesky.callbacks import LiveScatter, LivePlot, LiveTable
from ophyd import Device, Component as Cpt 
from ophyd.sim import SynAxis, SynSignal
from ophyd.sim import det1, noisy_det

from ophyd.device import Device, Component as Cpt
from ophyd.signal import EpicsSignalRO, AttributeSignal

import pcdsdevices

"""
Creates a RunEngine, and uses BestEffortCallback for nice visualizations during the scan
"""
RE = RunEngine()
bec = BestEffortCallback()
RE.subscribe(bec)
install_qt_kicker()


# Create the motor
x = SynAxis(name='x')


def basic_event_builder(*args,**kwargs):
    """
    Pass any number of pandas Series and return an event built pandas
    DataFrame.  Kwargs can be used to name the columns of the returned
    DataFrame.
    """
    data_table = dict()
    [data_table.setdefault(col,args[col]) for col in range(len(args))]
    [data_table.setdefault(col,kwargs[col]) for col in kwargs]
    full_frame = pd.DataFrame(data_table)
    return full_frame.dropna()


class FakeBeam(Device):
    """
    Create a Fake Beam 
    """
    fake_ipm2 = Cpt(EpicsSignalRO, 'HX2:SB1:BMMON:_peakA_8')
    fake_ipm3 = Cpt(EpicsSignalRO, 'HX2:SB1:BMMON:_peakA_9')
    def __init__(self, prefix='', name='fake_beam', **kwargs):
        super().__init__(prefix=prefix, name=name, **kwargs)
    @property
    def hints(self):
        return {'fields': [self.mj.name]}

    
# class CorrSignal(SynSignal):
"""
The main goal for this class was to find the correlation signal between the two ipms. I have not implemented this class. 
"""
#     def __init__(self, *args, beam, **kwargs):
#         super().__init__(*args, beam, **kwargs)
#         self.beam = beam
#     def trigger(self):
#         c1 = self.beam.ipm2.subscribe(self.basic_event_builder)
#         c2 = self.beam.ipm2.subscribe(self.basic_event_builder)
#         corr = Cpt(SynSignal)
#         self.put(corr)
#         return super().trigger()
#     def best_fit_slope(events1_list,events2_list):
#         slope = (((np.mean(events1_list)*np.mean(events2_list))-mean(events1_list*events2_list))/((mean(events1_list)**2)-mean(events1_list*events1_list)))
#         return slope


    
def new_data(*args, **kwargs): 
    """
    Append data into data containers
    
    """
    kwargs['in_value'].append(kwargs['value'])
    kwargs['in_time'].append(kwargs['timestamp'])


"""
Get data
"""
beam = FakeBeam()
ipm2List = list()
ipm3List = list()
ipm2TimeStamp = list()
ipm3TimeStamp = list()
beam.fake_ipm2.subscribe(
    partial(new_data, in_value=ipm2List, in_time=ipm2TimeStamp)
)
beam.fake_ipm3.subscribe(
    partial(new_data, in_value=ipm3List, in_time=ipm3TimeStamp)
)


def gen_scatter_plan(noisy_det, x):
    """
    Goal for this function is to plot a user-defined number of events from both ipms, find the correlation, and plot the correlation point relavant to motor movement. 
    """

    """
    Logic:
        Loop  continuously after asking how many points needed to calculate correlation
        After getting points, scan to next step
        Plot the correlation point versus motor location in range
    """
    
    #User Entered Values
    #Enter the lower bound of the motor movement, ex:10
    Min_target = int(input('Enter lower bound of the range '))
    #Enter the upper bound of the motor movement, ex:100
    Max_target = int(input('Enter upper bound of the range '))
   #Enter the step size of the motor, preferably, over 2 and less than 10
    #Once it reaches over 60 scans, it doesn't plot anymore
    step = int(input('Enter step value '))
    #Enter the number of events you want to calculate the correlation to, for each step
    number_of_events1 =  int(input('Enter how many events '))
    counter = 0
    number_of_events = 0
    number_of_events2 = number_of_events1
    
    #Sets up the plot. This does not use liveplot however. 
    fig = plt.gcf()
    fig.show()
    fig.canvas.draw()
    fig.suptitle('Motor Position vs Correlation')
    plt.xlabel('Motor Position')
    plt.ylabel('Correlation')
    
    #This is the plan
    #When you are in the motor's range
    for p in range(Min_target, Max_target):
        #If the location * step are less than Max_target
        if (p*step) < Max_target:
            #If the location/step has no remainders
            if p % step == 0:
                #If the amount of events that user entered is greater than 0
                if number_of_events1>0:
                    #Increase a counter value
                    counter+=1
#                     print(counter)
                    #Multiply the number of events with counter
                    #This will be the index value at that iteration
                    number_of_events = number_of_events1*counter
#                     print(number_of_events)
                    #Create a list by slicing the ipm2List
                    #Indices go from [user entered number of events: index value at the iteration + user entered number of events
                    #This will always start at user entered number of events, not 0
                    #STILL NEED TO FIGURE OUT HOW TO DO THAT
                    events1_list = ipm2List[number_of_events1:number_of_events1+number_of_events]
#                     print(len(events1_list))
                    #Create a list by slicing the ipm3List
                    #Same information as above
                    events2_list = ipm3List[number_of_events1:number_of_events1+number_of_events]
#                     print(len(events2_list))
                #This gives the correlation of the two lists
                correlation_coef= np.corrcoef(events1_list, events2_list)[0, 1]  
                print('Your Correlation at this location is:')
                print(correlation_coef)
                #This scans the motor based on user preferences
                #STILL NEED TO FIGURE OUT HOW TO SCAN WITH JUST STEP VALUE
                yield from scan([noisy_det], x, (Min_target+(p*step)), (Max_target-((p-1)*step)), 1)
                #This plots the points, 
                plt.scatter(Min_target+(p*step), correlation_coef)
                #Continously updates the points
                fig.canvas.draw()

    else:
        #At the end, let's user know that the destination has been met
        print('Reached Destination')
        plt.show()
        
RE(gen_scatter_plan(noisy_det, x), md={'plan_name': 'special'})      

# def gen_plan(CorrSignal, x, number_of_events1= None, number_of_events2 = None):
"""
If using the CorrSignal Class, this function uses that signal to find the correlation and move the motor, read, the location

"""    

#     corr_signal = CorrSignal(beam)
#     c1 = self.beam.ipm2.subscribe(self.basic_event_builder)
#     c2 = self.beam.ipm2.subscribe(self.basic_event_builder)
    
#     first_point_target = int(input('Enter the first point to where the motor should move '))
    
#     while True:
#         yield from mv(x, first_point_target)
#         yield from trigger_and_read(x)
#         number_of_events2 = number_of_events1
#         if number_of_events1 is None:
#             number_of_events1 = int(input('Enter the number of events '))

#             events1_list = ipm2List[:number_of_events1]
#             print(*events1_list)
#             events2_list = ipm3List[:number_of_events2]
#             print(*events2_list)
#         slope = CorrSignal.best_fit_slope(events1_list,events2_list)
#         print(slope)
      
    
# #     self.beam.ipm3.unsubscribe(c2)
# #     self.beam.ipm2.unsubscribe(c1)
# #     yield from trigger_read
  
# RE(gen_plan(CorrSignal, x))


# def wrong_logic_but_update_live_plot(det1, x):
"""
This is completely wrong, but is implementing live plot.
"""

#     Min_target = int(input('Enter lower bound of the range '))
#     Max_target = int(input('Enter upper bound of the range '))
#     step = int(input('Enter how much you would like to step per scan '))
#     number_of_events1 = None
#     number_of_events2 = None

#     if number_of_events1 is None:
#         number_of_events1 = int(input('Enter the number of events '))
#         number_of_events2 = number_of_events1

#         events1_list = ipm2List[:number_of_events1]
#         events2_list = ipm3List[:number_of_events2]
#     correlation_coef= np.corrcoef(events1_list, events2_list)[0, 1]
#     sorted_events1_list = sorted(events1_list)
#     sorted_events2_list = sorted(events2_list)
#     print('Your Correlation at this location is:')
#     print(correlation_coef)
#     while True:    
#         table = LiveTable([x])
#         if not np.isclose(Max_target, sorted_events1_list[-1], atol=20):
#             plan2 = scan([det1], x, Min_target, Max_target,number_of_events1, per_step = None, md =None)
            
# #             plot2 = LivePlot('det1', 'x')
# #             run_wrapper(plot2)
#             yield from run_wrapper(plan2,md={'detectors': [det1.name],
#                                              'motors': [x.name],
#                                              'hints': {'dimensions': [(x.hints['fields'], 'primary')]}})
#         elif not np.isclose(Min_target, sorted_events2_list[0], atol=20):
#             plan1 = scan([det1], x, Min_target, Max_target,number_of_events1, per_step = None, md = None)
# #             plot1 = LivePlot('det1', 'x')
# #             run_wrapper(plot1)
#             yield from run_wrapper(plan1,md={'detectors': [det1.name],
#                                              'motors': [x.name],
#                                              'hints': {'dimensions': [(x.hints['fields'], 'primary')]}})
# #         plt.scatter(events1_list, events2_list)
# #         plt.show()  
#         else:
#             break

# #     yield from close_run()
# #     yield from unsubscribe(token_pl)
    
# #     yield from unsubscribe(token_test_plot)
# #     yield from close_run()

# RE(wrong_logic_but_update_live_plot(det1,x),  md={'plan_name': 'special'})



# -*- coding: utf-8 -*-
"""
Created on Wed Apr 20 15:47:58 2022

@author: MichaelBarbour


https://nspyre.readthedocs.io/en/latest/guides/ni-daqmx.html#some-helpful-resources-when-working-with-nidaqmx

well apparently the myDAQ doesn't support an analog trigger'
https://forums.ni.com/t5/Example-Code/Analog-Acquisition-with-Software-Analog-Reference-Trigger/ta-p/3492361?profile.language=en



more on software trigger

"""

import nidaqmx  as ni
import numpy as np
import plotly.graph_objects as go


#%% explore and config system
system = ni.system.System.local()

for device in system.devices:
    print(device)

daq = system.devices['myDAQ1']

# get list of ai voltage channels
ai_channels = [ci.name for ci in daq.ai_physical_chans]
ao_channels = [co.name for co in daq.ao_physical_chans]
print(ai_channels, ao_channels)

#%% try creating a scale
dV = 5
dP = 10
slope = dP / dV

scale = ni.scale.Scale.create_lin_scale('scaleTest', slope, y_intercept=0.0, scaled_units='Pa')

#%% simple read task


# create task
task = ni.Task()

# add voltage measurement
task.ai_channels.add_ai_voltage_chan(ai_channels[0], 
                                     name_to_assign_to_channel="Pressure (Pa)", 
                                     terminal_config=ni.constants.TerminalConfiguration(10106), # RSE = 10083
                                     custom_scale_name='scaleTest',
                                     units=ni.constants.VoltageUnits(10065), # custom
                                     min_val=0,
                                     max_val=5) # can also assign a scale

task.ai_channels.add_ai_voltage_chan(ai_channels[1], 
                                     name_to_assign_to_channel="Flow (Pa)", 
                                     terminal_config=ni.constants.TerminalConfiguration(10106), # RSE = 10083
                                     min_val=0,
                                     max_val=5) # can also assign a scale


task.start()

value = task.read(number_of_samples_per_channel=50)

task.stop()
task.close()


#%% functions

def readdaq_single():
    # create task
    task = ni.Task()

    task.ai_channels.add_ai_voltage_chan("MyDaQ1/ai0", 
                                         name_to_assign_to_channel="Pressure (Pa)", 
                                         terminal_config=ni.constants.TerminalConfiguration(10106), # RSE = 10083
                                         min_val=0,
                                         max_val=5) # can also assign a scale

    task.start()
    value = task.read()
    task.stop()
    task.close()
    
    return value

# def readdaq_multiple()

#%% Examples from https://nspyre.readthedocs.io/en/latest/guides/ni-daqmx.html#some-helpful-resources-when-working-with-nidaqmx


system = ni.system.System.local()

for device in system.devices:
    print(device)

daq = system.devices['myDAQ1']

# get list of ai voltage channels
ai_channels = [ci.name for ci in daq.ai_physical_chans]
ao_channels = [co.name for co in daq.ao_physical_chans]
print(ai_channels, ao_channels)

#%%

with ni.Task() as task:
    task.ai_channels.add_ai_voltage_chan(ai_channels[0],
                                         name_to_assign_to_channel="Pressure (Pa)", 
                                         terminal_config=ni.constants.TerminalConfiguration(10106), # RSE = 10083
                                         min_val=0,
                                         max_val=5)
    sampleRate = 100
    # not sure about continuous vs finite - why set the number of samples?
    task.timing.cfg_samp_clk_timing(sampleRate, 
                                    sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                                    samps_per_chan=1000)
    task.triggers.start_trigger.cfg_anlg_edge_start_trig(ai_channels[1],
                                                         trigger_slope=ni.constants.Slope.RISING,
                                                         trigger_level=0.0)
    



#%% create an output channel
from nidaqmx.stream_writers import AnalogSingleChannelWriter

with ni.Task() as ao_task:
    
    
    #create analog output task
    ao_task.ao_channels.add_ao_voltage_chan(ao_channels[0])
    ao_task.timing.cfg_samp_clk_timing(rate=100,
                                       sample_mode = ni.constants.AcquisitionType.FINITE,
                                       samps_per_chan=50)
    
    # specify an analog writer
    writer = AnalogSingleChannelWriter(ao_task.out_stream,auto_start=True)
    samples = np.append(5*np.ones(25), np.zeros(25))

    writer.write_many_sample(samples)
    ao_task.wait_until_done()
    
    
#%% create a read task, 


with ni.Task() as task:
    task.ai_channels.add_ai_voltage_chan(ai_channels[0],
                                         name_to_assign_to_channel="Pressure (Pa)", 
                                         terminal_config=ni.constants.TerminalConfiguration(10106), # RSE = 10083
                                         min_val=0,
                                         max_val=5)
    sampleRate = 100
    # not sure about continuous vs finite - why set the number of samples?
    task.timing.cfg_samp_clk_timing(sampleRate, 
                                    sample_mode=ni.constants.AcquisitionType.FINITE,
                                    samps_per_chan=1000)

    # read a set number of samples
    data = task.read(number_of_samples_per_channel=100)



#%% create an output trigger
from nidaqmx.stream_writers import AnalogSingleChannelWriter

# pulse frequency s defined by rate
# samps per chan sets the size of the buffer

freq = 100

buffer = 50
wavehalf = int(buffer / 2)

ao_task = ni.Task()

#create analog output task
ao_task.ao_channels.add_ao_voltage_chan(ao_channels[0])
ao_task.timing.cfg_samp_clk_timing(rate = int(buffer * freq),
                                   sample_mode = ni.constants.AcquisitionType.CONTINUOUS,
                                   samps_per_chan=buffer)

# specify an analog writer
writer = AnalogSingleChannelWriter(ao_task.out_stream,auto_start=True)
samples = np.append(5*np.ones(wavehalf), np.zeros(wavehalf))

writer.write_many_sample(samples, timeout = 100 ) # returns after writing all samples
#%%

# ao_task.wait_until_done(timeout=20)
ao_task.stop()
ao_task.close()





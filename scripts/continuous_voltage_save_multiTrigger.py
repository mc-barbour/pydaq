from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import nidaqmx
import numpy as np
from nidaqmx.stream_writers import AnalogSingleChannelWriter

import tkinter as tk
from tkinter import ttk
import time

import matplotlib
matplotlib.use("TkAgg")


class voltageContinuousInput(tk.Frame):

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        # Configure root tk class
        self.master = master
        self.master.title("Voltage - Single Input, Camera Trigger, Continuous")
        self.master.iconbitmap("Voltage - Continuous Input.ico")
        self.master.geometry("1100x600")

        self.create_widgets()
        self.pack()
        self.run = False

    def create_widgets(self):
        # The main frame is made up of three subframes
        self.channelSettingsFrame = channelSettings(
            self, title="Channel Settings")
        self.channelSettingsFrame.grid(
            row=0, column=1, sticky="ew", pady=(20, 0), padx=(20, 20), ipady=10)

        self.inputSettingsFrame = inputSettings(self, title="Input Settings")
        self.inputSettingsFrame.grid(
            row=1, column=1, pady=(20, 0), padx=(20, 20), ipady=10)

        self.graphDataFrame = graphData(self)
        self.graphDataFrame.grid(
            row=0, rowspan=2, column=2, pady=(20, 0), ipady=10)

    def writeDataFile(self, vals):

        filename = self.inputSettingsFrame.saveFileName.get()
        
        with open(filename, 'a') as f:  
            for count,val in enumerate(vals):
                line_num = self.sampleCount + count
                f.write('{:g}, {:10.6f} \n'.format(line_num, val))
                
    def cameraTriggerStart(self):
        
        # generate a pule wave for the camera
        buffer = 50
        
        sampleRate = int(self.inputSettingsFrame.sampleRateEntry.get())
        
        self.task_ao = nidaqmx.Task()
        self.task_ao.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
        self.task_ao.timing.cfg_samp_clk_timing(rate = int(sampleRate * buffer),
                                           sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                           samps_per_chan = buffer)
        
        self.ao_stream = AnalogSingleChannelWriter(self.task_ao.out_stream, auto_start=True)
        wave = np.append(np.zeros(int(buffer / 2)), np.ones(int(buffer / 2))*5)
        
        self.ao_stream.write_many_sample(wave)
   
    def channelScale(self):
        
        sensorUnits = self.channelSettingsFrame.sensorUnitsEntry.get()
        maxVoltage = int(self.channelSettingsFrame.maxVoltageEntry.get())
        minVoltage = int(self.channelSettingsFrame.minVoltageEntry.get())
        
        maxValue = int(self.channelSettingsFrame.maxSensorEntry.get())
        minValue = int(self.channelSettingsFrame.minSensorEntry.get())
        
        voltageRange = maxVoltage - minVoltage
        sensorRange = maxValue - minValue
        slope = sensorRange / voltageRange

        nidaqmx.scale.Scale.create_lin_scale('channelScale', slope, y_intercept=0.0,
                                             scaled_units=sensorUnits)
        

    def startTask(self):
        
        # Prevent user from starting task a second time
        self.inputSettingsFrame.startButton['state'] = 'disabled'

        # Shared flag to alert task if it should stop
        self.continueRunning = True

        # Get task settings from the user
        physicalChannel = self.channelSettingsFrame.physicalChannelEntry.get()
        maxVoltage = int(self.channelSettingsFrame.maxVoltageEntry.get())
        minVoltage = int(self.channelSettingsFrame.minVoltageEntry.get())
        sampleRate = int(self.inputSettingsFrame.sampleRateEntry.get())
        
        # Have to share number of samples with runTask
        self.numberOfSamples = int(
            self.inputSettingsFrame.numberOfSamplesEntry.get())
        
        # Initialize scale
        self.channelScale()

        # Create and start task
        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_voltage_chan(
            physicalChannel, min_val=minVoltage, max_val=maxVoltage,
            custom_scale_name='channelScale',
            units=nidaqmx.constants.VoltageUnits(10065))
        self.task.timing.cfg_samp_clk_timing(
            sampleRate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.numberOfSamples*3)
        
        
        self.task.start()
        self.cameraTriggerStart()
        
        # could use start time, dt and number of samples to save time
        startTime = time.time()
        self.sampleCount = 0

        # spin off call to check
        self.master.after(10, self.runTask)

    def runTask(self):

        # Check if task needs to update the graph
        samplesAvailable = self.task._in_stream.avail_samp_per_chan
        if(samplesAvailable >= self.numberOfSamples):
            vals = self.task.read(self.numberOfSamples)
            self.graphDataFrame.ax.cla()
            self.graphDataFrame.ax.set_title("Acquired Data")
            self.graphDataFrame.ax.plot(vals)
            self.graphDataFrame.graph.draw()

            self.writeDataFile(vals)
            self.sampleCount = self.sampleCount + self.numberOfSamples


        # check if the task should sleep or stop
        if(self.continueRunning):
            self.master.after(10, self.runTask)
        else:
            self.task.stop()
            self.task.close()
            self.task_ao.stop()
            self.task_ao.close()
            self.inputSettingsFrame.startButton['state'] = 'enabled'

    def stopTask(self):
        # call back for the "stop task" button
        self.continueRunning = False


class channelSettings(tk.LabelFrame):

    def __init__(self, parent, title):
        tk.LabelFrame.__init__(self, parent, text=title, labelanchor='n')
        self.parent = parent
        self.grid_columnconfigure(0, weight=1)
        self.xPadding = (30, 30)
        self.create_widgets()

    def create_widgets(self):

        self.physicalChannelLabel = ttk.Label(self, text="Physical Channel")
        self.physicalChannelLabel.grid(
            row=0, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.physicalChannelEntry = ttk.Entry(self)
        self.physicalChannelEntry.insert(0, "myDAQ1/ai0")
        self.physicalChannelEntry.grid(row=1, sticky="ew", padx=self.xPadding)

        self.maxVoltageLabel = ttk.Label(self, text="Max Voltage")
        self.maxVoltageLabel.grid(
            row=2, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.maxVoltageEntry = ttk.Entry(self)
        self.maxVoltageEntry.insert(0, "5")
        self.maxVoltageEntry.grid(row=3, sticky="ew", padx=self.xPadding)

        self.minVoltageLabel = ttk.Label(self, text="Min Voltage")
        self.minVoltageLabel.grid(
            row=4,  sticky='w', padx=self.xPadding, pady=(10, 0))

        self.minVoltageEntry = ttk.Entry(self)
        self.minVoltageEntry.insert(0, "0")
        self.minVoltageEntry.grid(
            row=5, sticky="ew", padx=self.xPadding, pady=(0, 10))

        
        self.maxSensorLabel = ttk.Label(self, text="Max Sensor Value")
        self.maxSensorLabel.grid(
            row=2, column=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.maxSensorEntry = ttk.Entry(self)
        self.maxSensorEntry.insert(0, "5")
        self.maxSensorEntry.grid(row=3, column=1, sticky="ew", padx=self.xPadding)

        self.minSensorLabel = ttk.Label(self, text="Min Sensor Value")
        self.minSensorLabel.grid(
            row=4, column=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.minSensorEntry = ttk.Entry(self)
        self.minSensorEntry.insert(0, "0")
        self.minSensorEntry.grid(
            row=5,column=1, sticky="ew", padx=self.xPadding, pady=(0, 10))
        
        self.sensorUnitsLabel = ttk.Label(self, text="Sensor Units")
        self.sensorUnitsLabel.grid(
            row=0, column=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.sensorUnitsEntry = ttk.Entry(self)
        self.sensorUnitsEntry.insert(0, "Pa")
        self.sensorUnitsEntry.grid(
            row=1,column=1, sticky="ew", padx=self.xPadding, pady=(0, 10))


class inputSettings(tk.LabelFrame):

    def __init__(self, parent, title):
        tk.LabelFrame.__init__(self, parent, text=title, labelanchor='n')
        self.parent = parent
        self.xPadding = (30, 30)
        self.create_widgets()

    def create_widgets(self):
        self.sampleRateLabel = ttk.Label(self, text="Sample Rate")
        self.sampleRateLabel.grid(
            row=0, column=0, columnspan=2, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.sampleRateEntry = ttk.Entry(self)
        self.sampleRateEntry.insert(0, "1000")
        self.sampleRateEntry.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=self.xPadding)

        self.numberOfSamplesLabel = ttk.Label(self, text="Number of Samples")
        self.numberOfSamplesLabel.grid(
            row=2, column=0, columnspan=2, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.numberOfSamplesEntry = ttk.Entry(self)
        self.numberOfSamplesEntry.insert(0, "100")
        self.numberOfSamplesEntry.grid(
            row=3, column=0, columnspan=2, sticky='ew', padx=self.xPadding)

        self.saveFileLabel = ttk.Label(self, text="File Name")
        self.saveFileLabel.grid(
            row=4, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.saveFileName = ttk.Entry(self)
        self.saveFileName.insert(0, "C:/tmp/test.txt")
        self.saveFileName.grid(row=5, sticky="ew", padx=self.xPadding)

        self.startButton = ttk.Button(
            self, text="Start Task", command=self.parent.startTask)
        self.startButton.grid(row=6, column=0, sticky='w',
                              padx=self.xPadding, pady=(10, 0))

        self.stopButton = ttk.Button(
            self, text="Stop Task", command=self.parent.stopTask)
        self.stopButton.grid(row=6, column=1, sticky='e',
                             padx=self.xPadding, pady=(10, 0))


class graphData(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.create_widgets()

    def create_widgets(self):
        

        self.graphTitle = ttk.Label(self, text="Voltage Input")
        self.fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.set_title("Acquired Data")
        self.graph = FigureCanvasTkAgg(self.fig, self)
        self.graph.draw()
        self.graph.get_tk_widget().pack()


# Creates the tk class and primary application "voltageContinuousInput"
root = tk.Tk()
app = voltageContinuousInput(root)

# start the application
app.mainloop()

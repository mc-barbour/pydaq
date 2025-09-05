from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import nidaqmx
import numpy as np
from nidaqmx.stream_writers import AnalogSingleChannelWriter

import tkinter as tk
from tkinter import ttk
import time
from datetime import date



import matplotlib
matplotlib.use("TkAgg")


class voltageContinuousInput(tk.Frame):

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        # Configure root tk class
        self.master = master
        self.master.title("Voltage - Two Input, Camera Trigger, Continuous")
        self.master.iconbitmap("Voltage - Continuous Input.ico")
        self.master.geometry("1280x700")

        self.create_widgets()
        self.pack()
        self.run = False

    def create_widgets(self):
        # The main frame is made up of three subframes
        self.channelSettingsFrame = channelSettings(
            self, title="Channel Settings")
        self.channelSettingsFrame.grid(
            row=0, column=1, sticky='ew', pady=(20, 0), padx=(20, 20), ipady=10)

        self.inputSettingsFrame = inputSettings(self, title="Input Settings")
        self.inputSettingsFrame.grid(
            row=1, column=1, pady=(10, 0), padx=(20, 20), ipady=10)

        self.graphDataFrame1 = graphData1(self)
        self.graphDataFrame1.grid(
            row=0, rowspan=2,column=2, sticky='n', pady=(20, 0), ipady=10)
        
        self.graphDataFrame2 = graphData2(self)
        self.graphDataFrame2.grid(
            row=1, rowspan=2, column=2, pady=(20, 0), ipady=10)
        
        self.lightFrame = lightIndicator(self, title='Recording')
        self.lightFrame.grid(
            row=0, rowspan=1, column=4, pady=(20, 0),padx=(20, 20), ipady=10)
        
        self.channelAverageFrame = averageData(self, title='Channel Moving Averages')
        self.channelAverageFrame.grid(
            row=1, rowspan=1, column=4, pady=(20, 0),padx=(20, 20), ipady=10)
        
    def createFileName(self):
        today = date.today()
        formatted_date = today.strftime("%Y%m%d")
        mrn = self.inputSettingsFrame.patientMRNEntry.get()
        directoryName = self.inputSettingsFrame.saveDirName.get()
        
        self.filename = directoryName + "cannPressure_" + mrn + "_" + formatted_date + ".txt"

        

    def writeDataFile(self, vals):
        chan1 = vals[0]
        chan2 = vals[1]
        
        
        with open(self.filename, 'a') as f:  
            for count,(val1,val2) in enumerate(zip(chan1,chan2)):
                line_num = self.sampleCount + count
                f.write('{:g}, {:10.6f}, {:10.6f} \n'.format(line_num, val1, val2))
    
    def averageData(self, vals):
        chan1 = np.mean(vals[0])
        chan2 = np.mean(vals[1])
        
        self.channelAverageFrame.channel1AverageValue.delete(0, 'end')
        self.channelAverageFrame.channel1AverageValue.insert(0, '{:4.3f}'.format(chan1))
        
        self.channelAverageFrame.channel2AverageValue.delete(0, 'end')
        self.channelAverageFrame.channel2AverageValue.insert(0, '{:4.3f}'.format(chan2))

                
    def cameraTriggerStart(self):
        
        # generate a pule wave for the camera
        buffer = 50
        
        sampleRate = int(self.inputSettingsFrame.sampleRateEntry.get())
        
        self.task_ao = nidaqmx.Task()
        self.task_ao.ao_channels.add_ao_voltage_chan('Dev1/ao0')
        self.task_ao.timing.cfg_samp_clk_timing(rate = int(sampleRate * buffer),
                                           sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                           samps_per_chan = buffer)
        
        self.ao_stream = AnalogSingleChannelWriter(self.task_ao.out_stream, auto_start=True)
        wave = np.append(np.zeros(int(buffer / 2)), np.ones(int(buffer / 2))*5)
        
        self.ao_stream.write_many_sample(wave)

    def scaleChan1(self):
        sensorUnits = self.channelSettingsFrame.sensorUnitsEntry1.get()

        maxVoltage1 = int(self.channelSettingsFrame.maxVoltageEntry1.get())
        minVoltage1 = int(self.channelSettingsFrame.minVoltageEntry1.get())
        
        maxValue1 = int(self.channelSettingsFrame.maxSensorEntry1.get())
        minValue1 = int(self.channelSettingsFrame.minSensorEntry1.get())
        
        voltageRange = maxVoltage1 - minVoltage1
        sensorRange = maxValue1 - minValue1
        slope = sensorRange / voltageRange

        nidaqmx.scale.Scale.create_lin_scale('scaleChan1', slope, y_intercept=0.0,
                                             scaled_units=sensorUnits)
    
    def scaleChan2(self):
        sensorUnits = self.channelSettingsFrame.sensorUnitsEntry2.get()

        maxVoltage1 = int(self.channelSettingsFrame.maxVoltageEntry2.get())
        minVoltage1 = int(self.channelSettingsFrame.minVoltageEntry2.get())
        
        maxValue1 = int(self.channelSettingsFrame.maxSensorEntry2.get())
        minValue1 = int(self.channelSettingsFrame.minSensorEntry2.get())
        
        voltageRange = maxVoltage1 - minVoltage1
        sensorRange = maxValue1 - minValue1
        slope = sensorRange / voltageRange

        nidaqmx.scale.Scale.create_lin_scale('scaleChan2', slope, y_intercept=0.0,
                                             scaled_units=sensorUnits)
        
        

    def startTask(self):
        
        # Prevent user from starting task a second time
        self.inputSettingsFrame.startButton['state'] = 'disabled'

        # Shared flag to alert task if it should stop
        self.continueRunning = True
        
        #create filename
        self.createFileName()
        print(self.filename)

        # Get task settings from the user
        physicalChannel1 = self.channelSettingsFrame.physicalChannelEntry1.get()
        maxVoltage1 = int(self.channelSettingsFrame.maxVoltageEntry1.get())
        minVoltage1 = int(self.channelSettingsFrame.minVoltageEntry1.get())
        
        physicalChannel2 = self.channelSettingsFrame.physicalChannelEntry2.get()
        maxVoltage2 = int(self.channelSettingsFrame.maxVoltageEntry2.get())
        minVoltage2 = int(self.channelSettingsFrame.minVoltageEntry2.get())
        
        sampleRate = int(self.inputSettingsFrame.sampleRateEntry.get())
        # cameraTrigger = self.inputSettingsFrame.triggerFlagEntry.get()
        # assert (cameraTrigger == 'yes') or (cameraTrigger == 'no'), 'Error, camera trigger flag unknown, recieved {:s}'.format(cameraTrigger)
        
        # create channel scales
        self.scaleChan1()
        self.scaleChan2()
        
        # Have to share number of samples with runTask
        self.numberOfSamples = int(
            self.inputSettingsFrame.numberOfSamplesEntry.get())

        # Create and start task
        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_voltage_chan(
            physicalChannel1, min_val=minVoltage1, max_val=maxVoltage1,
            custom_scale_name='scaleChan1',
            units=nidaqmx.constants.VoltageUnits(10065))
        
        self.task.ai_channels.add_ai_voltage_chan(
            physicalChannel2, min_val=minVoltage2, max_val=maxVoltage2,
            custom_scale_name='scaleChan2',
            units=nidaqmx.constants.VoltageUnits(10065))
        
        
        self.task.timing.cfg_samp_clk_timing(
            sampleRate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.numberOfSamples*3) # in continuous_mode, samps per chan is the buffer size
        
        self.task.start()
        # if cameraTrigger == 'yes':
        #     self.cameraTriggerStart()
        
        # could use start time, dt and number of samples to save time
        startTime = time.time()
        self.sampleCount = 0

        # spin off call to check
        self.master.after(10, self.runTask)
        
        self.lightFrame.set_light_color("green")

    def runTask(self):

        # Check if task needs to update the graph
        samplesAvailable = self.task._in_stream.avail_samp_per_chan
        if(samplesAvailable >= self.numberOfSamples):
            vals = self.task.read(self.numberOfSamples)
            
            # self.graphDataFrame1.ax.cla()
            # self.graphDataFrame1.ax.set_title("Acquired Data")
            # self.graphDataFrame1.ax.plot(vals[0])
            # self.graphDataFrame1.graph.draw()
            self.graphDataFrame1.update_plot(vals[0])
            self.graphDataFrame2.update_plot(vals[1])
            
            # self.graphDataFrame2.ax.cla()
            # self.graphDataFrame2.ax.set_title("Acquired Data")
            # self.graphDataFrame2.ax.plot(vals[1])
            # self.graphDataFrame2.graph.draw()

            self.writeDataFile(vals)
            self.averageData(vals)
            self.sampleCount = self.sampleCount + self.numberOfSamples


        # check if the task should sleep or stop
        if(self.continueRunning):
            self.master.after(10, self.runTask)
        else:
            self.task.stop()
            self.task.close()
            # self.task_ao.stop()
            # self.task_ao.close()
            self.inputSettingsFrame.startButton['state'] = 'enabled'

    def stopTask(self):
        # call back for the "stop task" button
        self.continueRunning = False
        self.lightFrame.set_light_color("gray")


class channelSettings(tk.LabelFrame):

    def __init__(self, parent, title):
        tk.LabelFrame.__init__(self, parent, text=title, labelanchor='n')
        self.parent = parent
        self.grid_columnconfigure(0, weight=1)
        self.xPadding = (30, 30)
        self.create_widgets()

    def create_widgets(self):

        
        # Channel 1
        
        self.physicalChannelLabel1 = ttk.Label(self, text="Physical Channel 1")
        self.physicalChannelLabel1.grid(
            row=0, column=0, sticky='w',padx=self.xPadding, pady=(10, 0))

        self.physicalChannelEntry1 = ttk.Entry(self)
        self.physicalChannelEntry1.insert(0, "Dev1/ai0")
        self.physicalChannelEntry1.grid(row=1,column=0, sticky="ew", padx=self.xPadding)

        self.maxVoltageLabel1 = ttk.Label(self, text="Max Voltage")
        self.maxVoltageLabel1.grid(
            row=2, column=0, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.maxVoltageEntry1 = ttk.Entry(self)
        self.maxVoltageEntry1.insert(0, "5")
        self.maxVoltageEntry1.grid(row=3, column=0, sticky="ew", padx=self.xPadding)

        self.minVoltageLabel1 = ttk.Label(self, text="Min Voltage")
        self.minVoltageLabel1.grid(
            row=4, column=0, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.minVoltageEntry1 = ttk.Entry(self)
        self.minVoltageEntry1.insert(0, "0")
        self.minVoltageEntry1.grid(
            row=5,column=0, sticky="ew", padx=self.xPadding)
        
        self.maxSensorLabel1 = ttk.Label(self, text="Max Sensor Value")
        self.maxSensorLabel1.grid(
            row=6, column=0, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.maxSensorEntry1 = ttk.Entry(self)
        self.maxSensorEntry1.insert(0, "5")
        self.maxSensorEntry1.grid(row=7, column=0, sticky="ew", padx=self.xPadding)

        self.minSensorLabel1 = ttk.Label(self, text="Min Sensor Value")
        self.minSensorLabel1.grid(
            row=8, column=0, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.minSensorEntry1 = ttk.Entry(self)
        self.minSensorEntry1.insert(0, "0")
        self.minSensorEntry1.grid(
            row=9,column=0, sticky="ew", padx=self.xPadding)
        
        self.sensorUnitsLabel1 = ttk.Label(self, text="Sensor Units")
        self.sensorUnitsLabel1.grid(
            row=10, column=0, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.sensorUnitsEntry1 = ttk.Entry(self)
        self.sensorUnitsEntry1.insert(0, "PSI")
        self.sensorUnitsEntry1.grid(
            row=11,column=0, sticky="ew", padx=self.xPadding, pady=(0, 5))
        


        # Channel 2
        
        
        self.physicalChannelLabel2 = ttk.Label(self, text="Physical Channel 2")
        self.physicalChannelLabel2.grid(
            row=0, column=1, sticky='w',padx=self.xPadding, pady=(10, 0))

        self.physicalChannelEntry2 = ttk.Entry(self)
        self.physicalChannelEntry2.insert(0, "Dev1/ai1")
        self.physicalChannelEntry2.grid(row=1, column=1,sticky="ew", padx=self.xPadding)

        self.maxVoltageLabel2 = ttk.Label(self, text="Max Voltage")
        self.maxVoltageLabel2.grid(
            row=2, column=1,sticky='w', padx=self.xPadding, pady=(5, 0))

        self.maxVoltageEntry2 = ttk.Entry(self)
        self.maxVoltageEntry2.insert(0, "5")
        self.maxVoltageEntry2.grid(row=3,column=1, sticky="ew", padx=self.xPadding)

        self.minVoltageLabel2 = ttk.Label(self, text="Min Voltage")
        self.minVoltageLabel2.grid(
            row=4, column=1, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.minVoltageEntry2 = ttk.Entry(self)
        self.minVoltageEntry2.insert(0, "-5")
        self.minVoltageEntry2.grid(
            row=5, column=1, sticky="ew", padx=self.xPadding)
        
        self.maxSensorLabel2 = ttk.Label(self, text="Max Sensor Value")
        self.maxSensorLabel2.grid(
            row=6, column=1, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.maxSensorEntry2 = ttk.Entry(self)
        self.maxSensorEntry2.insert(0, "5")
        self.maxSensorEntry2.grid(row=7, column=1, sticky="ew", padx=self.xPadding)

        self.minSensorLabel2 = ttk.Label(self, text="Min Sensor Value")
        self.minSensorLabel2.grid(
            row=8, column=1, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.minSensorEntry2 = ttk.Entry(self)
        self.minSensorEntry2.insert(0, "-5")
        self.minSensorEntry2.grid(
            row=9,column=1, sticky="ew", padx=self.xPadding)
        
        self.sensorUnitsLabel2 = ttk.Label(self, text="Sensor Units")
        self.sensorUnitsLabel2.grid(
            row=10, column=1, sticky='w', padx=self.xPadding, pady=(5, 0))

        self.sensorUnitsEntry2 = ttk.Entry(self)
        self.sensorUnitsEntry2.insert(0, "cmH20")
        self.sensorUnitsEntry2.grid(
            row=11,column=1, sticky="ew", padx=self.xPadding, pady=(0, 5))
        
        

class inputSettings(tk.LabelFrame):

    def __init__(self, parent, title):
        tk.LabelFrame.__init__(self, parent, text=title, labelanchor='n')
        self.parent = parent
        self.xPadding = (30, 30)
        self.create_widgets()

    def create_widgets(self):
        self.sampleRateLabel = ttk.Label(self, text="Sample Rate")
        self.sampleRateLabel.grid(
            row=0, column=0, columnspan=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.sampleRateEntry = ttk.Entry(self)
        self.sampleRateEntry.insert(0, "100")
        self.sampleRateEntry.grid(
            row=1, column=0, columnspan=1, sticky='ew', padx=self.xPadding)
        
        
        # self.triggerFlagLabel = ttk.Label(self, text="Trigger Camera (yes / no)")
        # self.triggerFlagLabel.grid(
        #     row=0, column=1, columnspan=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        # self.triggerFlagEntry = ttk.Entry(self)
        # self.triggerFlagEntry.insert(0, "yes")
        # self.triggerFlagEntry.grid(
        #     row=1, column=1, columnspan=1, sticky='ew', padx=self.xPadding)


        self.numberOfSamplesLabel = ttk.Label(self, text="Number of Samples")
        self.numberOfSamplesLabel.grid(
            row=0, column=1, columnspan=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.numberOfSamplesEntry = ttk.Entry(self)
        self.numberOfSamplesEntry.insert(0, "25")
        self.numberOfSamplesEntry.grid(
            row=1, column=1, columnspan=1, sticky='ew', padx=self.xPadding)
        
        self.patientMRNLabel = ttk.Label(self, text="Patient MRN")
        self.patientMRNLabel.grid(
            row=2, column=0, columnspan=1, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.patientMRNEntry = ttk.Entry(self)
        self.patientMRNEntry.insert(0, "999999")
        self.patientMRNEntry.grid(
            row=3, column=0, columnspan=1, sticky='ew', padx=self.xPadding)
        

        self.saveDirLabel = ttk.Label(self, text="Directory Name")
        self.saveDirLabel.grid(
            row=4, column=0, columnspan=2, sticky='w', padx=self.xPadding, pady=(10, 0))

        self.saveDirName = ttk.Entry(self)
        self.saveDirName.insert(0, "C://Users/mbarb1/pressure_can_data/")
        self.saveDirName.grid(row=5, column=0, columnspan=2, sticky="ew", padx=self.xPadding)

        self.startButton = ttk.Button(
        self, text="Start Task", command=self.parent.startTask)
        self.startButton.grid(row=6, column=0, sticky='w',
                              padx=self.xPadding, pady=(10, 0))

        self.stopButton = ttk.Button(
            self, text="Stop Task", command=self.parent.stopTask)
        self.stopButton.grid(row=6, column=1, sticky='e',
                             padx=self.xPadding, pady=(10, 0))



class graphData1(tk.Frame):

    def __init__(self, parent, title="Light"):
        super().__init__(parent)
        self.title = title
        self.max_points = 1000  # Number of points to show at once
        self.ydata = np.zeros(self.max_points)
        self.xdata = np.arange(self.max_points)
        self.create_widgets()
        self.init_plot()

    def create_widgets(self):
        self.graphTitle = ttk.Label(self, text=self.title)
        self.graphTitle.pack()
        self.fig = Figure(figsize=(6, 3), dpi=100, tight_layout=True)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.graph = FigureCanvasTkAgg(self.fig, self)
        self.graph.get_tk_widget().pack()

    def init_plot(self):
        self.line, = self.ax.plot(self.xdata, self.ydata, color='blue')
        self.ax.set_title(self.title)
        self.ax.set_xlim(0, self.max_points)
        # self.ax.set_ylim(-10, 10)  # Adjust based on expected range
        self.graph.draw()

    def update_plot(self, new_data):
        num_new = len(new_data)
        if num_new >= self.max_points:
            self.ydata[:] = new_data[-self.max_points:]  # just take the latest
        else:
            self.ydata = np.roll(self.ydata, -num_new)
            self.ydata[-num_new:] = new_data

        self.line.set_ydata(self.ydata)
        
        self.ax.relim()
        self.ax.autoscale_view(scalex=False, scaley=True)
        self.graph.draw_idle()




class graphData2(tk.Frame):

    def __init__(self, parent, title="Pressure"):
        super().__init__(parent)
        self.title = title
        self.max_points = 1000  # Number of points to show at once
        self.ydata = np.zeros(self.max_points)
        self.xdata = np.arange(self.max_points)
        self.create_widgets()
        self.init_plot()

    def create_widgets(self):
        self.graphTitle = ttk.Label(self, text=self.title)
        self.graphTitle.pack()
        self.fig = Figure(figsize=(6, 3), dpi=100, tight_layout=True)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.graph = FigureCanvasTkAgg(self.fig, self)
        self.graph.get_tk_widget().pack()

    def init_plot(self):
        self.line, = self.ax.plot(self.xdata, self.ydata, color='blue')
        self.ax.set_title(self.title)
        self.ax.set_xlim(0, self.max_points)
        # self.ax.set_ylim(-10, 10)  # Adjust based on expected range
        self.graph.draw()

    def update_plot(self, new_data):
        num_new = len(new_data)
        if num_new >= self.max_points:
            self.ydata[:] = new_data[-self.max_points:]  # just take the latest
        else:
            self.ydata = np.roll(self.ydata, -num_new)
            self.ydata[-num_new:] = new_data

        self.line.set_ydata(self.ydata)
        
        self.ax.relim()
        self.ax.autoscale_view(scalex=False, scaley=True)
        self.graph.draw_idle()


# class graphData1(tk.Frame):

#     def __init__(self, parent):
#         tk.Frame.__init__(self, parent)

#         self.create_widgets()

#     def create_widgets(self):
#         self.graphTitle = ttk.Label(self, text="Channel 1")
#         self.fig = Figure(figsize=(6, 3.0), dpi=100, tight_layout=True)
#         self.ax = self.fig.add_subplot(1, 1, 1)
#         self.ax.set_title("Channel 1")
#         self.graph = FigureCanvasTkAgg(self.fig, self)
#         self.graph.draw()
#         self.graph.get_tk_widget().pack()
        
# class graphData2(tk.Frame):

#     def __init__(self, parent):
#         tk.Frame.__init__(self, parent)
#         self.create_widgets()

#     def create_widgets(self):
#         self.graphTitle = ttk.Label(self, text="Channel 2")
#         self.fig = Figure(figsize=(6, 3.0), dpi=100, tight_layout=True)
#         self.ax = self.fig.add_subplot(1, 1, 1)
#         self.ax.set_title("Channel 2")
#         self.graph = FigureCanvasTkAgg(self.fig, self)
#         self.graph.draw()
#         self.graph.get_tk_widget().pack()
        
class averageData(tk.Frame):
    def __init__(self, parent, title):
        tk.LabelFrame.__init__(self, parent, text=title, labelanchor='n')
        self.xPadding = (30,30)
        self.create_widgets()
        
    def create_widgets(self): 
       
        self.channel1AverageLabel = ttk.Label(self, text="Channel 1")
        self.channel1AverageLabel.grid(
        row=0, column=0, sticky='w',padx=self.xPadding, pady=(10, 0))

        self.channel1AverageValue = ttk.Entry(self)
        self.channel1AverageValue.insert(0, "0")
        self.channel1AverageValue.grid(row=1,column=0, sticky="ew", padx=self.xPadding)
        
        self.channel2AverageLabel = ttk.Label(self, text="Channel 2")
        self.channel2AverageLabel.grid(
        row=2, column=0, sticky='w',padx=self.xPadding, pady=(10, 0))

        self.channel2AverageValue = ttk.Entry(self)
        self.channel2AverageValue.insert(0, "0")
        self.channel2AverageValue.grid(row=3,column=0, sticky="ew", padx=self.xPadding)
        
       
class lightIndicator(tk.Frame):
    def __init__(self, parent, title):
        tk.LabelFrame.__init__(self, parent, text=title, labelanchor='n')
        self.xPadding = (30,30)
        self.create_widgets()
        
    def create_widgets(self): 
       
        self.canvas = tk.Canvas(self, width=60, height=60, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=self.xPadding, pady=(10, 0))
        self.light = self.canvas.create_oval(10, 10, 50 , 50, fill="gray")
        
    def set_light_color(self, color):
        self.canvas.itemconfig(self.light, fill=color)




# Creates the tk class and primary application "voltageContinuousInput"
root = tk.Tk()
app = voltageContinuousInput(root)

# start the application
app.mainloop()

from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
import copy
from scipy.signal import detrend
#importing a bunch of stuff


path = sys.path[0] + r"\Four Terminal Gate Sweep Probe Station"
sys.path.append(path + r'\FourTerminalGateSweepProbeStationSetting')

import FourTerminalGateSweepProbeStationSetting

FourTerminalGateSweepProbeStationWindowUI, QtBaseClass = uic.loadUiType(path + r"\FourTerminalGateSweepProbeStationWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way.
sys.path.append(sys.path[0]+'\Resources')
from DEMONSFormat import *

class Window(QtGui.QMainWindow, FourTerminalGateSweepProbeStationWindowUI):

    def __init__(self, reactor, DEMONS, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.parent = parent
        self.DEMONS = DEMONS
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.SettingWindow = FourTerminalGateSweepProbeStationSetting.Setting(self.reactor, self)
        self.pushButton_Setting.clicked.connect(lambda: openWindow(self.SettingWindow))

        self.serversList = { #Dictionary including toplevel server received from labrad connect
            'dv': False,
            'DACADC': False,
            'SR830': False,
            'SR860': False,
            'SIM900': False,
        }

        self.DeviceList = {}#self.DeviceList['Device Name'][Device Property]

        self.DeviceList['Voltage_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Voltage_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Voltage_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Voltage_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Voltage_LI_DeviceIndicator,
            'ServerNeeded': ['SR860', 'SR830'],
        }

        self.DeviceList['Current_LI_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_Current_LI_SelectServer,
            'ComboBoxDevice': self.comboBox_Current_LI_SelectDevice,
            'ServerIndicator': self.pushButton_Current_LI_ServerIndicator,
            'DeviceIndicator': self.pushButton_Current_LI_DeviceIndicator, 
            'ServerNeeded': ['SR830', 'SR860'],
        }

        self.DeviceList['DataAquisition_Device'] = {
            'DeviceObject': False,
            'ServerObject': False,
            'ComboBoxServer': self.comboBox_DataAquisition_SelectServer,
            'ComboBoxDevice': self.comboBox_DataAquisition_SelectDevice,
            'ServerIndicator': self.pushButton_DataAquisition_ServerIndicator,
            'DeviceIndicator': self.pushButton_DataAquisition_DeviceIndicator, 
            'ServerNeeded': ['SIM900'],
        }

        self.Parameter = {
            'DeviceName': 'Device Name',#This is related to the sample name like YS8
            'LI_Excitation': 'Read',
            'LI_Timeconstant': 'Read',
            'LI_Frequency': 'Read',
            'Voltage_LI_Gain': 1.0,
            'Current_LI_Gain': 1.0,
            'FourTerminal_StartVoltage': -1.0,
            'FourTerminal_EndVoltage': 1.0,
            'FourTerminal_Delay': 0.01,
            'FourTerminalSetting_Numberofsteps_Status': "Numberofsteps",
            'FourTerminal_Numberofstep': 101,
            'FourTerminal_GateChannel': 3,
            'Setting_RampDelay': 0.0001,
            'Setting_RampStepSize': 0.01,
            'Setting_WaitTime': 2.0,
        } 

        self.lineEdit = {
            'DeviceName': self.lineEdit_Device_Name,
            'LI_Excitation': self.lineEdit_LI_Excitation,
            'LI_Timeconstant': self.lineEdit_LI_Timeconstant,
            'LI_Frequency': self.lineEdit_LI_Frequency,
            'FourTerminal_StartVoltage': self.lineEdit_FourTerminal_StartVoltage,
            'FourTerminal_EndVoltage': self.lineEdit_FourTerminal_EndVoltage,
            'FourTerminal_Delay': self.lineEdit_FourTerminal_Delay,
            'FourTerminal_Numberofstep': self.lineEdit_FourTerminal_Numberofstep,
            'FourTerminal_GateChannel': self.lineEdit_DataAquisition_GateChannel,
            'Setting_RampDelay': self.SettingWindow.lineEdit_Setting_RampDelay,
            'Setting_RampStepSize': self.SettingWindow.lineEdit_Setting_RampStepSize,
            'Setting_WaitTime': self.SettingWindow.lineEdit_Setting_WaitTime,
        }

        for key in self.lineEdit:
            if not isinstance(self.Parameter[key], str):
                UpdateLineEdit_Bound(self.Parameter, key, self.lineEdit)

        self.DetermineEnableConditions()

        self.lineEdit_Device_Name.editingFinished.connect(lambda: UpdateLineEdit_String(self.Parameter, 'DeviceName', self.lineEdit))

        self.lineEdit_LI_Excitation.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Excitation', self.lineEdit))
        self.pushButton_LI_Excitation_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation']))
        self.pushButton_LI_Excitation_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation']))#Send to Voltage Lock in
        self.lineEdit_LI_Timeconstant.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Timeconstant', self.lineEdit))
        self.pushButton_LI_Timeconstant_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))
        self.pushButton_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))#Send to Voltage Lock in
        self.pushButton_LI_Timeconstant_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant']))#Send to Current Lock in
        self.lineEdit_LI_Frequency.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'LI_Frequency', self.lineEdit))
        self.pushButton_LI_Frequency_Read.clicked.connect(lambda: ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency']))
        self.pushButton_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency']))#Send to Voltage Lock in
        self.pushButton_LI_Frequency_Set.clicked.connect(lambda: SetEdit_Parameter(self.DeviceList['Current_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency']))#Send to Current Lock in

        self.comboBox_Voltage_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Voltage_LI_Device', self.serversList, str(self.DeviceList['Voltage_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Voltage_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Voltage_LI_Device', str(self.DeviceList['Voltage_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        

        self.comboBox_Current_LI_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'Current_LI_Device', self.serversList, str(self.DeviceList['Current_LI_Device']['ComboBoxServer'].currentText())))
        self.comboBox_Current_LI_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'Current_LI_Device', str(self.DeviceList['Current_LI_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))

        self.comboBox_DataAquisition_SelectServer.currentIndexChanged.connect(lambda: SelectServer(self.DeviceList, 'DataAquisition_Device', self.serversList, str(self.DeviceList['DataAquisition_Device']['ComboBoxServer'].currentText())))
        self.comboBox_DataAquisition_SelectDevice.currentIndexChanged.connect(lambda: SelectDevice(self.DeviceList, 'DataAquisition_Device', str(self.DeviceList['DataAquisition_Device']['ComboBoxDevice'].currentText()), self.Refreshinterface))
        self.lineEdit_DataAquisition_GateChannel.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_GateChannel', self.lineEdit, None, int))


        self.lineEdit_FourTerminal_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_StartVoltage', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_FourTerminal_StartVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_EndVoltage', self.lineEdit, [-10.0, 10.0]))
        self.lineEdit_FourTerminal_EndVoltage.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(lambda: UpdateLineEdit_NumberOfStep(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.lineEdit))
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(lambda: UpdateLineEdit_Bound(self.Parameter, 'FourTerminal_Delay', self.lineEdit))
        self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(lambda: Toggle_NumberOfSteps_StepSize(self.Parameter, 'FourTerminal_Numberofstep', 'FourTerminal_EndVoltage', 'FourTerminal_StartVoltage', 'FourTerminalSetting_Numberofsteps_Status', self.label_FourTerminalNumberofstep, 'Volt per Step', self.lineEdit))  

        self.pushButton_StartFourTerminalSweep.clicked.connect(self.StartMeasurement)
        self.pushButton_AbortFourTerminalSweep.clicked.connect(lambda: self.DEMONS.SetScanningFlag(False))

        self.SetupPlots()
        self.Refreshinterface()

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.lineEdit_Device_Name: True,
            self.pushButton_StartFourTerminalSweep: (self.DeviceList['DataAquisition_Device']['DeviceObject'] != False) and self.DEMONS.Scanning_Flag == False,
            self.pushButton_AbortFourTerminalSweep: self.DEMONS.Scanning_Flag == True,
            self.comboBox_DataAquisition_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_DataAquisition_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_DataAquisition_GateChannel: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_StartVoltage: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_EndVoltage: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Numberofstep: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_FourTerminal_Delay: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Timeconstant: self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Timeconstant_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Timeconstant_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Frequency: self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Frequency_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Frequency_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DeviceList['Current_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Voltage_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
            self.lineEdit_LI_Excitation: self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Excitation_Read: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.pushButton_LI_Excitation_Set: self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False and self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectServer: self.DEMONS.Scanning_Flag == False,
            self.comboBox_Current_LI_SelectDevice: self.DEMONS.Scanning_Flag == False,
        }

    @inlineCallbacks
    def StartMeasurement(self, c):
        try:
            self.DEMONS.SetScanningFlag(True)

            self.Refreshinterface()
            ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter, 'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])

            Multiplier = [self.Parameter['Voltage_LI_Gain'], self.Parameter['Current_LI_Gain']] #Voltage, Current

            ImageNumber, ImageDir = yield CreateDataVaultFile(self.serversList['dv'], 'FourTerminalGateSweep ' + str(self.Parameter['DeviceName']), ('Gate Index', 'Gate Voltage'), ('Voltage', 'Current', 'Resistance', 'Conductance'))

            self.lineEdit_ImageNumber.setText(ImageNumber)
            self.lineEdit_ImageDir.setText(ImageDir)
            yield AddParameterToDataVault(self.serversList['dv'], self.Parameter)
            ClearPlots(self.Plotlist)

            GateChannel = self.Parameter['FourTerminal_GateChannel']
            StartVoltage, EndVoltage = self.Parameter['FourTerminal_StartVoltage'], self.Parameter['FourTerminal_EndVoltage']
            NumberOfSteps, Delay = self.Parameter['FourTerminal_Numberofstep'], self.Parameter['FourTerminal_Delay']

            yield Ramp_SIM900_VoltageSource(self.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, 0.0, StartVoltage, self.Parameter['Setting_RampStepSize'], self.Parameter['Setting_RampDelay'], self.reactor)
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])

            Data = np.empty((0,6))
            GateVoltageSet = np.linspace(StartVoltage, EndVoltage, NumberOfSteps)
            for GateIndex in range(NumberOfSteps):
                if self.DEMONS.Scanning_Flag == False:
                    print 'Abort the Sweep'
                    yield self.FinishSweep(GateVoltageSet[GateIndex])
                    break #Break it outside of the for loop
                yield Set_SIM900_VoltageOutput(self.DeviceList['DataAquisition_Device']['DeviceObject'], GateChannel, GateVoltageSet[GateIndex])
                yield SleepAsync(self.reactor, Delay)
                Voltage = yield Get_SR_LI_R(self.DeviceList['Voltage_LI_Device']['DeviceObject'])
                Current = yield Get_SR_LI_R(self.DeviceList['Current_LI_Device']['DeviceObject'])
                Data_Line = np.array([Voltage, Current])
                Data_Line = Multiply(Data_Line, Multiplier)
                Data_Line = AttachData_Front(Data_Line, GateVoltageSet[GateIndex])
                Data_Line = AttachData_Front(Data_Line, GateIndex)
                Data_Line = Attach_ResistanceConductance(Data_Line, 2, 3)
                self.serversList['dv'].add(Data_Line)
                Data = np.append(Data, [Data_Line], axis = 0)
                XData, VoltageData, CurrentData, ResistanceData, ConductanceData = Data[:,1], Data[:,2], Data[:,3], Data[:,4], Data[:,5]
                ClearPlots(self.Plotlist)
                Plot1DData(XData, VoltageData, self.Plotlist['VoltagePlot'])
                Plot1DData(XData, CurrentData, self.Plotlist['CurrentPlot'])
                Plot1DData(XData, ResistanceData, self.Plotlist['ResistancePlot'])
                if GateIndex == NumberOfSteps - 1:
                    yield self.FinishSweep(GateVoltageSet[GateIndex])

        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    @inlineCallbacks
    def FinishSweep(self, currentvoltage):
        try:
            yield SleepAsync(self.reactor, self.Parameter['Setting_WaitTime'])
            yield Ramp_SIM900_VoltageSource(self.DeviceList['DataAquisition_Device']['DeviceObject'], self.Parameter['FourTerminal_GateChannel'], currentvoltage, 0.0, self.Parameter['Setting_RampStepSize'], self.Parameter['Setting_RampDelay'], self.reactor)
            self.serversList['dv'].add_comment(str(self.textEdit_Comment.toPlainText()))
            self.DEMONS.SetScanningFlag(False)
            self.Refreshinterface()
            saveDataToSessionFolder(self.winId(), self.sessionFolder, str(self.lineEdit_ImageDir.text()).replace('\\','_') + '_' + str(self.lineEdit_ImageNumber.text())+ ' - ' + 'Probe Station Screening ' + self.Parameter['DeviceName'])

        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def connectServer(self, key, server):
        try:
            self.serversList[str(key)] = server
            self.refreshServerIndicator()
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    '''
    When a server is disconnected, look up which device use the server and disconnect it
    '''
    def disconnectServer(self, ServerName):
        try:
            self.serversList[str(ServerName)] = False

            for key, DevicePropertyList in self.DeviceList.iteritems():
                if str(ServerName) == str(DevicePropertyList['ComboBoxServer'].currentText()):
                    DevicePropertyList['ServerObject'] = False
                    DevicePropertyList['DeviceObject'] = False
            self.refreshServerIndicator()
            self.Refreshinterface()
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def refreshServerIndicator(self):
        try:
            optional = []#This optional will reconstruct combobox multiple time when you disconnect/connect server individually
            flag = True
            for key in self.serversList:
                if self.serversList[str(key)] == False and not key in optional:
                    flag = False

            if flag:
                setIndicator(self.pushButton_Servers, 'rgb(0, 170, 0)')

                for key, DevicePropertyList in self.DeviceList.iteritems():#Reconstruct all combobox when all servers are connected
                    ReconstructComboBox(DevicePropertyList['ComboBoxServer'], DevicePropertyList['ServerNeeded'])

                self.Refreshinterface()
            else:
                setIndicator(self.pushButton_Servers, 'rgb(161, 0, 0)')
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def Refreshinterface(self):
        self.DetermineEnableConditions()
        RefreshButtonStatus(self.ButtonsCondition)

        for key, DevicePropertyList in self.DeviceList.iteritems():
            RefreshIndicator(DevicePropertyList['ServerIndicator'], DevicePropertyList['ServerObject'])
            RefreshIndicator(DevicePropertyList['DeviceIndicator'], DevicePropertyList['DeviceObject'])

        if self.DeviceList['Voltage_LI_Device']['DeviceObject'] != False:
            ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].sine_out_amplitude, self.Parameter, 'LI_Excitation', self.lineEdit['LI_Excitation'])
            ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].time_constant, self.Parameter,  'LI_Timeconstant', self.lineEdit['LI_Timeconstant'])
            ReadEdit_Parameter(self.DeviceList['Voltage_LI_Device']['DeviceObject'].frequency, self.Parameter, 'LI_Frequency', self.lineEdit['LI_Frequency'])

    def SetupPlots(self):
        self.Plotlist = {
            'VoltagePlot': pg.PlotWidget(parent = None),
            'CurrentPlot': pg.PlotWidget(parent = None),
            'ResistancePlot': pg.PlotWidget(parent = None),
        }
        Setup1DPlot(self.Plotlist['VoltagePlot'], self.Layout_FourTerminalPlot1, 'Voltage', 'Voltage', "V", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        Setup1DPlot(self.Plotlist['CurrentPlot'], self.Layout_FourTerminalPlot2, 'Current', 'Current', "A", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        Setup1DPlot(self.Plotlist['ResistancePlot'], self.Layout_FourTerminalPlot3, 'Resistance', 'Resistance', u"\u03A9", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

    def moveDefault(self):
        self.move(200,0)
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
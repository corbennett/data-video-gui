# -*- coding: utf-8 -*-
"""
Created on Tue Mar 05 18:48:48 2019

@author: svc_ccg
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 25 23:14:43 2017
@author: corbennett
"""

import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import cv2
import os
from datetime import datetime
from sync_dataset import Dataset
import json


def start():
    #QtGui.QApplication.setGraphicsSystem("raster")
    app = QtGui.QApplication.instance()
    if app is None:
        app = QtGui.QApplication([])
    lickVideoObj= lickVideo(app)
    app.exec_()
    
class lickVideo():
    
    def __init__(self, app):
        self.app = app
        self.vid = None
        self.lickStates = None
        self.annotationDataFile = None
        self.lastAnnotatedFrame = None
        self.videoFileName = None
        self.data_directory = None
        self.key_shortcuts = {}
        
        self.config_path = r"C:\Users\svc_ccg\Documents\GitHub\data-video-gui"
        self.load_config(default=True)
        
        self.sync_lick_frames = []
        self.frameIndex = 0
        self.mainWin = QtGui.QMainWindow()
        self.mainWidget = QtGui.QWidget()
        self.mainWin.setCentralWidget(self.mainWidget)
        self.mainWin.closeEvent = self.closeEvent
        self.mainLayout = QtGui.QGridLayout()
        
        self.createMenuBar()
        self.createControlPanel()
        
        self.mainWin.keyPressEvent = self.keyPressCallback
        
        self.plotLayout = pg.GraphicsLayoutWidget()
        self.plot1 = self.plotLayout.addPlot(0,0)
        self.plot1.setLimits(minYRange=2)
        self.plot1_infLine = pg.InfiniteLine(movable=True)
        self.plot1_infLine.sigDragged.connect(self.scrollFrame)
        self.plot1.addItem(self.plot1_infLine)

        self.mainLayout.addWidget(self.plotLayout, 2, 0)
        
        self.imageLayout = pg.GraphicsLayoutWidget()
        self.imageViewBox = self.imageLayout.addViewBox(lockAspect=1,invertY=True,enableMouse=True,enableMenu=True)
        self.imageItem = pg.ImageItem()
        self.imageViewBox.addItem(self.imageItem)   
        self.mainLayout.addWidget(self.imageLayout, 1, 0)
        self.mainLayout.setRowMinimumHeight(1, 500)
        self.mainWidget.setLayout(self.mainLayout)
        
        self.mainWin.show()

        self.annotationDataSaved = False
    
    def getVideoFile(self):
        
        videoChange = False
        if self.vid is not None:
            self.vid.release()
            videoChange = True
        
        videoFileName = self.get_file('Load Video File', '*.avi')

        if videoFileName=='':
            return
        
        self.videoFileName = videoFileName 
        self.data_directory = os.path.dirname(self.videoFileName)
        
        self.vid = cv2.VideoCapture(self.videoFileName)
        _, self.frame = self.vid.read()
        self.updatePlot()

        self.totalVidFrames = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
        
        self.plot1.setXRange(0, 18000, padding=0)
        self.plot1.setLimits(xMin=0, xMax=self.totalVidFrames, yMin=0, yMax=2)
        self.plot1_infLine.setBounds((0, self.totalVidFrames))
        
        self.frameRate = self.vid.get(cv2.CAP_PROP_FPS)
        self.frameIndex = 0
        self.frameDisplayBox.setText(str(self.frameIndex))
        self.totalFrameCountLabel.setText('/' + str(int(self.totalVidFrames)))

        if videoChange or self.annotationDataFile is not None:        
            #pop up to ask if you want to reset the annotation data since the movie has changed
            confirmResetDataMessageBoxReply = QtGui.QMessageBox.question(self.mainWin, 'New Video File', 'Reset Annotation Data?', QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            if confirmResetDataMessageBoxReply == QtGui.QMessageBox.Ok:
                self.resetAnnotationData()
        else:
            self.resetAnnotationData()

        assert(len(self.lickStates)==self.totalVidFrames)
        
        if self.lastAnnotatedFrame is not None:
            self.frameIndex = self.lastAnnotatedFrame
            self.updatePlot()
        
        self.annotationDataSaved = False
    
    def load_config(self, default=False):
        
        if default:
            configFile = os.path.join(self.config_path, 'shortcuts.json')
        
        else:
            configFile = self.get_file('Load Config', '*.json')
            
        if configFile == '' or not os.path.exists(configFile):
            print('config file does not exist: ' + configFile)
            return
            
        with open(configFile) as file:
            self.key_shortcuts = json.load(file)
        
    def loadAnnotationData(self):

        annotationDataFile = self.get_file('Load Annotation Data', '*.npz')
        
        if annotationDataFile =='':
            return
        
        self.annotationDataFile = annotationDataFile

        savedData = np.load(self.annotationDataFile)

        self.lickStates = savedData['lickStates']
        self.lastAnnotatedFrame = int(savedData['lastAnnotatedFrame'])
        
        if self.vid is not None:
            assert(len(self.lickStates)==self.totalVidFrames)
            self.frameIndex = self.lastAnnotatedFrame
            self.updatePlot()
            
    def loadSyncFile(self):
        self.resetPlot('syncDataItems')
        
        syncFile = self.get_file('Load Sync Data', '*.h5; *.sync')
        
        if syncFile=='':
            return
        
        self.syncFile = syncFile

        syncDataset = Dataset(self.syncFile)
        sync_frame_times, _ = get_sync_line_data(syncDataset, 'cam1_exposure')
        sync_lick_times, _ = get_sync_line_data(syncDataset, channel=31)
        
        print(len(sync_frame_times))
        print(len(sync_lick_times))
        
        self.sync_lick_frames = np.searchsorted(sync_frame_times, sync_lick_times) - 1
        
        self.syncDataItems = self.plot1.plot(self.sync_lick_frames, np.ones(len(self.sync_lick_frames)), size=0.5, pen=None, symbol='t')
    
    def get_file(self, hint='', file_filter='*'):
        
        if self.data_directory is None or not os.path.exists(self.data_directory):
            file_path = QtGui.QFileDialog.getOpenFileName(self.mainWin, hint, filter=file_filter)
        else:
            file_path = QtGui.QFileDialog.getOpenFileName(self.mainWin, hint, self.data_directory, filter=file_filter)
        
        if isinstance(file_path, tuple):
            file_path = str(file_path[0])
        
        file_path = str(file_path)
        print('Getting file: ' + file_path)
        
        return file_path
        
    
    def saveAnnotationData(self, automaticName=False):
        now = datetime.now()
        dateString = now.strftime("%m%d%Y_%H%M%S")
        
        if self.videoFileName is not None:
            basedir = os.path.dirname(self.videoFileName)
            baseVidName = os.path.splitext(os.path.basename(self.videoFileName))[0]
            annotationDataFileSaveName = os.path.join(basedir, baseVidName + '_' + dateString + '_annotations.npz')
        else:
            annotationDataFileSaveName = dateString + '_annotations.npz'
        
        if not automaticName:
            annotationDataFileSaveName = QtGui.QFileDialog.getSaveFileName(self.mainWin, 'Save Annotation Data', annotationDataFileSaveName)
            if isinstance(annotationDataFileSaveName, tuple):
                annotationDataFileSaveName = str(annotationDataFileSaveName[0])
            annotationDataFileSaveName = str(annotationDataFileSaveName)
            
        # get last annotated frame to reload when opened
        annoFrames = np.where(self.lickStates>0)[0]
        lastAnnoFrame = annoFrames[-1] if len(annoFrames)>0 else 0 

        np.savez(annotationDataFileSaveName, lickStates=self.lickStates, lastAnnotatedFrame=lastAnnoFrame, videoFileName=self.videoFileName)
        print('Saving annotation data to:' +  annotationDataFileSaveName)

        self.annotationDataSaved = True

    def closeEvent(self, event):
        if self.vid is not None:
            self.vid.release()

        if self.lickStates is not None:
            saveDataMessageBoxReply = QtGui.QMessageBox.question(self.mainWin, 'Closing', 'Save Annotation Data?', QtGui.QMessageBox.Ok | QtGui.QMessageBox.No)
            if saveDataMessageBoxReply == QtGui.QMessageBox.Ok:
                self.saveAnnotationData()
        
    def resetAnnotationData(self):
        self.lickStates = np.zeros(int(self.totalVidFrames))
        self.lastAnnotatedFrame = None
        self.setRadioButtonStates()
    
    def resetPlot(self, plotDataItemName):
        if hasattr(self, plotDataItemName):
            pdi = getattr(self, plotDataItemName)
            pdi.clear()
    
    def createMenuBar(self):
        # create an instance of menu bar
        menubar = self.mainWin.menuBar()
        # add file menu and file menu actions
        file_menu = menubar.addMenu('&File')
        
        # file menu actions
        open_action = QtGui.QAction('&Open Video', self.mainWin)
        open_action.triggered.connect(self.getVideoFile)
        
        saveAnnotations_action = QtGui.QAction('&Save Annotation Data', self.mainWin)
        saveAnnotations_action.triggered.connect(self.saveAnnotationData)
        
        loadAnnotations_action = QtGui.QAction('&Load Annotation Data', self.mainWin)
        loadAnnotations_action.triggered.connect(self.loadAnnotationData)
    
        loadSync_action = QtGui.QAction('&Load Sync Data', self.mainWin)
        loadSync_action.triggered.connect(self.loadSyncFile)
        
        file_menu.addAction(open_action)
        file_menu.addAction(loadAnnotations_action)
        file_menu.addAction(saveAnnotations_action)
        file_menu.addAction(loadSync_action)
             
    def createControlPanel(self):
        #make layout for gui controls and add to main layout
        self.controlPanelLayout = QtGui.QGridLayout()
        self.mainLayout.addLayout(self.controlPanelLayout, 0, 0)
        
        self.playVideoButton = QtGui.QPushButton('Play')
        self.playVideoButton.setCheckable(True)
        self.playVideoButton.clicked.connect(self.playVideo)
        self.controlPanelLayout.addWidget(self.playVideoButton, 0, 0, 1, 1)
        self.playTimer = QtCore.QTimer()
        self.playTimer.setInterval(10)
        self.playTimer.timeout.connect(self.advanceFrame)
        
        frameLabel = QtGui.QLabel("Frame:")
        self.controlPanelLayout.addWidget(frameLabel, 0, 1, 1, 1)
        
        self.frameDisplayBox = QtGui.QLineEdit()
        self.frameDisplayBox.editingFinished.connect(self.goToFrame)
        self.controlPanelLayout.addWidget(self.frameDisplayBox, 0, 2, 1, 1)
        
        self.totalFrameCountLabel = QtGui.QLabel("/")
        self.controlPanelLayout.addWidget(self.totalFrameCountLabel, 0, 3, 1, 1)
        
        self.lickRadioButton = QtGui.QRadioButton('tongue')
        self.lickRadioButton.clicked.connect(self.lickRadioButtonCallback)
        self.lickRadioButton.setToolTip('Shortcut: T, use when tongue touches spout')
        self.controlPanelLayout.addWidget(self.lickRadioButton, 0, 4, 1, 1)
        self.lick_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.lick_counter_label, 0, 5, 1, 1)
        
        self.runRadioButton = QtGui.QRadioButton('paw')
        self.runRadioButton.clicked.connect(self.runRadioButtonCallback)
        self.runRadioButton.setToolTip('Shortcut: P, use when paw hits spout during running')
        self.controlPanelLayout.addWidget(self.runRadioButton, 0, 6, 1, 1)
        self.run_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.run_counter_label, 0, 7, 1, 1)
        
        self.groomRadioButton = QtGui.QRadioButton('groom')
        self.groomRadioButton.clicked.connect(self.groomRadioButtonCallback)
        self.groomRadioButton.setToolTip('Shortcut: G, use when paw hits spout during grooming')
        self.controlPanelLayout.addWidget(self.groomRadioButton, 0, 8, 1, 1)
        self.groom_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.groom_counter_label, 0, 9, 1, 1)
        
        self.chinRadioButton = QtGui.QRadioButton('chin')
        self.chinRadioButton.clicked.connect(self.chinRadioButtonCallback)
        self.chinRadioButton.setToolTip('Shortcut: C, use when chin touches spout')
        self.controlPanelLayout.addWidget(self.chinRadioButton, 0, 10, 1, 1)
        self.chin_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.chin_counter_label, 0, 11, 1, 1)
        
        self.missRadioButton = QtGui.QRadioButton('air lick')
        self.missRadioButton.clicked.connect(self.missRadioButtonCallback)
        self.missRadioButton.setToolTip('Shortcut: A, use when mouse licks but does not touch spout')
        self.controlPanelLayout.addWidget(self.missRadioButton, 1, 4, 1, 1)
        self.miss_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.miss_counter_label, 1, 5, 1, 1)
        
        self.noLickRadioButton = QtGui.QRadioButton('no label')
        self.noLickRadioButton.clicked.connect(self.noLickRadioButtonCallback)
        self.noLickRadioButton.setToolTip('Shortcut: 0, default state, no annotation')
        self.controlPanelLayout.addWidget(self.noLickRadioButton, 1, 10, 1, 1)
        self.noLick_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.noLick_counter_label, 1, 11, 1, 1)
        
        self.airgroomRadioButton = QtGui.QRadioButton('air groom')
        self.airgroomRadioButton.clicked.connect(self.airgroomRadioButtonCallback)
        self.airgroomRadioButton.setToolTip('Shortcut: F, use when mouse is grooming but not contacting spout')
        self.controlPanelLayout.addWidget(self.airgroomRadioButton, 1, 6, 1, 1)
        self.airgroom_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.airgroom_counter_label, 1, 7, 1, 1)
        
        self.nocontactRadioButton = QtGui.QRadioButton('no contact')
        self.nocontactRadioButton.clicked.connect(self.nocontactRadioButtonCallback)
        self.nocontactRadioButton.setToolTip('Shortcut: N, use when mouse is not contacting spout and no other labels apply')
        self.controlPanelLayout.addWidget(self.nocontactRadioButton, 1, 8, 1, 1)
        self.nocontact_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.nocontact_counter_label, 1, 9, 1, 1)

    def advanceFrame(self, toNextDetectorFrame=False):
        
        self.frameIndex += 1
        if self.frameIndex > self.totalVidFrames:
            self.frameIndex = self.totalVidFrames
        
        if toNextDetectorFrame:
            nextDetectorFrameIndex = np.searchsorted(self.sync_lick_frames, self.frameIndex)
            nextDetectorFrameIndex = np.min([nextDetectorFrameIndex, len(self.sync_lick_frames)-1])
            self.frameIndex = self.sync_lick_frames[nextDetectorFrameIndex]
            
        self.updatePlot()
        
    def backFrame(self, toLastDetectorFrame=False):
        
        if toLastDetectorFrame:
            lastDetectorFrameIndex = np.searchsorted(self.sync_lick_frames, self.frameIndex) - 1
            lastDetectorFrameIndex = np.max([lastDetectorFrameIndex, 0])
            self.frameIndex = self.sync_lick_frames[lastDetectorFrameIndex]
        
        else:
            self.frameIndex -= 1
            if self.frameIndex < 0:
                self.frameIndex = 0
            
        self.updatePlot()
    
    def scrollFrame(self):
        linePos = int(np.round(self.plot1_infLine.value()))
        self.frameIndex = linePos
        self.updatePlot()

    def goToFrame(self):
        try:
            self.frameIndex = int(self.frameDisplayBox.text())
            if self.frameIndex > self.totalVidFrames:
                self.frameIndex = self.totalVidFrames
            elif self.frameIndex < 0:
                self.frameIndex = 0
            
            self.updatePlot()
            self.frameDisplayBox.clearFocus()
        except:
            if self.vid is not None:
                print('Invalid frame number')
    
    def playVideo(self):
        if self.playVideoButton.isChecked():
            self.playTimer.start()
        else:
            self.playTimer.stop()            
            
    def updatePlot(self):
        self.vid.set(cv2.CAP_PROP_POS_FRAMES, self.frameIndex)
        ret, self.frame = self.vid.read()
        if ret:
            self.imageItem.setImage(self.frame[:,:,0].T)
            self.frameDisplayBox.setText(str(self.frameIndex))
            self.setRadioButtonStates()
            self.updateLine()
        
    def updateLine(self):
        self.plot1_infLine.setValue(self.frameIndex)
        if self.frameIndex in self.sync_lick_frames:
            self.plot1_infLine.setPen('r', width=5)
        else:
            self.plot1_infLine.setPen('y')
        xMin, xMax = self.plot1.viewRange()[0]
        plotrange = xMax-xMin
        current_position_in_plot = self.frameIndex - xMin
        if current_position_in_plot>0.9*plotrange:
            self.plot1.setXRange(self.frameIndex+0.1*plotrange, self.frameIndex - 0.9*plotrange, padding=0)

    
    def setRadioButtonStates(self):
        if self.lickStates is not None:
            thisState = self.lickStates[self.frameIndex]
            if thisState==0: self.noLickRadioButton.click()
            elif thisState==1: self.lickRadioButton.click()
            elif thisState==2: self.runRadioButton.click()
            elif thisState==3: self.groomRadioButton.click()
            elif thisState==4: self.missRadioButton.click()
            elif thisState==5: self.chinRadioButton.click()
            elif thisState==6: self.airgroomRadioButton.click()
            elif thisState==7: self.nocontactRadioButton.click()
            
    def lickRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 1
        self.reset_counters()
        
    def noLickRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 0
        self.reset_counters()

    def runRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 2
        self.reset_counters()
        
    def groomRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 3
        self.reset_counters()
        
    def missRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 4
        self.reset_counters()
        
    def chinRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 5
        self.reset_counters()
    
    def airgroomRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 6
        self.reset_counters()
    
    def nocontactRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 7
        self.reset_counters()
    
    def reset_counters(self):
        self.lick_counter_label.setText("(" + str(np.sum(self.lickStates==1)) + ")")
        self.noLick_counter_label.setText("(" + str(np.sum(self.lickStates==0)) + ")")
        self.run_counter_label.setText("(" + str(np.sum(self.lickStates==2)) + ")")
        self.groom_counter_label.setText("(" + str(np.sum(self.lickStates==3)) + ")")
        self.miss_counter_label.setText("(" + str(np.sum(self.lickStates==4)) + ")")
        self.chin_counter_label.setText("(" + str(np.sum(self.lickStates==5)) + ")")
        self.airgroom_counter_label.setText("(" + str(np.sum(self.lickStates==6)) + ")")
        self.nocontact_counter_label.setText("(" + str(np.sum(self.lickStates==7)) + ")")
  
    def keyPressCallback(self, event):
        
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('backFrame', 'Key_Left')]:
            self.backFrame()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('advanceFrame', 'Key_Right')]:
            self.advanceFrame()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('tongue', 'Key_T')]:
            self.lickRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('no_label', 'Key_0')]:
            self.noLickRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('paw', 'Key_P')]:
            self.runRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('groom', 'Key_G')]:
            self.groomRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('air_lick', 'Key_A')]:
            self.missRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('chin', 'Key_C')]:
            self.chinRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('air_groom', 'Key_F')]:
            self.airgroomRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('no_contact', 'Key_N')]:
            self.nocontactRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('play', 'Key_Space')]:
            self.playVideoButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('last_detector_frame', 'Key_Comma')]:
            self.backFrame(toLastDetectorFrame=True)
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('next_detector_frame', 'Key_Period')]:
            self.advanceFrame(toNextDetectorFrame=True)
            
            
def get_sync_line_data(syncDataset, line_label=None, channel=None):
    ''' Get rising and falling edge times for a particular line from the sync h5 file
        
        Parameters
        ----------
        dataset: sync file dataset generated by sync.Dataset
        line_label: string specifying which line to read, if that line was labelled during acquisition
        channel: integer specifying which channel to read if line wasn't labelled
        
        Returns
        ----------
        rising: npy array with rising edge times for specified line
        falling: falling edge times
    '''
    
    if line_label in syncDataset.line_labels:
        channel = syncDataset.line_labels.index(line_label)
    elif channel is None:
        print('Invalid Line Label: ' + line_label)
        return
    else:
        print('No line label specified, reading channel ' + str(channel))
    
    sample_freq = syncDataset.meta_data['ni_daq']['counter_output_freq']
    rising = syncDataset.get_rising_edges(channel)/sample_freq
    falling = syncDataset.get_falling_edges(channel)/sample_freq
    
    return rising, falling
   
        
if __name__ == '__main__':
    start()

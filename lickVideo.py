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
import os, glob
from datetime import datetime
from sync_dataset import Dataset
import json
import alignCameraFrames

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
        self.annotation_category_dict = {
                'no label': 0,
                'tongue': 1,
                'paw': 2,
                'groom': 3,
                'air lick': 4,
                'chin': 5,
                'air groom': 6,
                'no contact': 7,
                'tongue out': 8,
                'ambiguous': 9,
                'all labels': ''}
        
        self.config_path = os.path.dirname(os.path.realpath(__file__))
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
        self.mainLayout.setRowStretch(1, 7)
        self.mainLayout.setRowStretch(2, 2)
        self.mainWidget.setLayout(self.mainLayout)
        
        self.mainWin.show()

        self.annotationDataSaved = False
    
    def getVideoFile(self):
        
        videoChange = False
        if self.vid is not None:
            self.vid.release()
            videoChange = True
        
        videoFileName = self.get_file('Load Video File', '*.avi *.mp4')

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
        
        print('loading config file: ' + configFile)
        with open(configFile) as file:
            self.key_shortcuts = json.load(file)
            #self.sync_camera_label = self.key_shortcuts['sync_camera_label']
        
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
        
        #infer camera label; otherwise read from config
        self.sync_camera_label = [l for l in ['behavior', 'eye', 'face'] if l in self.videoFileName]
        if len(self.sync_camera_label)==0:
            self.sync_camera_label = self.key_shortcuts['sync_camera_label']
        else:
            self.sync_camera_label = self.sync_camera_label[0]

        cam_json = glob.glob(os.path.join(self.data_directory, '*.'+self.sync_camera_label+'.json'))
        print('getting camera json {}'.format(cam_json))
        if len(cam_json)>0:
            cam_json = cam_json[0]
        else:
            print('could not find cam json')

        sync_frame_times = get_frame_exposure_times(syncDataset, cam_json)
        #sync_frame_times, _ = get_sync_line_data(syncDataset, self.sync_camera_label)
        sync_lick_times, _ = get_sync_line_data(syncDataset, channel=31)
        
        print(len(sync_frame_times))
        print(len(sync_lick_times))
        
        sync_frame_times = np.insert(sync_frame_times, 0, 0) #correct for MVR metadata frame

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
        
        load_config_action = QtGui.QAction('&Load Config', self.mainWin)
        load_config_action.triggered.connect(self.load_config)
        
        file_menu.addAction(open_action)
        file_menu.addAction(loadAnnotations_action)
        file_menu.addAction(saveAnnotations_action)
        file_menu.addAction(loadSync_action)
        file_menu.addAction(load_config_action)
             
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
        self.lickRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('tongue', 'T') + ' use when tongue touches spout')
        self.controlPanelLayout.addWidget(self.lickRadioButton, 0, 4, 1, 1)
        self.lick_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.lick_counter_label, 0, 5, 1, 1)
        
        self.runRadioButton = QtGui.QRadioButton('paw')
        self.runRadioButton.clicked.connect(self.runRadioButtonCallback)
        self.runRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('paw', 'P') + ' use when paw hits spout during running')
        self.controlPanelLayout.addWidget(self.runRadioButton, 0, 6, 1, 1)
        self.run_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.run_counter_label, 0, 7, 1, 1)
        
        self.groomRadioButton = QtGui.QRadioButton('groom')
        self.groomRadioButton.clicked.connect(self.groomRadioButtonCallback)
        self.groomRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('groom', 'G') + ' use when paw hits spout during grooming')
        self.controlPanelLayout.addWidget(self.groomRadioButton, 0, 8, 1, 1)
        self.groom_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.groom_counter_label, 0, 9, 1, 1)
        
        self.chinRadioButton = QtGui.QRadioButton('chin')
        self.chinRadioButton.clicked.connect(self.chinRadioButtonCallback)
        self.chinRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('chin', 'C') + ' use when chin touches spout')
        self.controlPanelLayout.addWidget(self.chinRadioButton, 0, 10, 1, 1)
        self.chin_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.chin_counter_label, 0, 11, 1, 1)
        
        self.tongueOutRadioButton = QtGui.QRadioButton('tongue out')
        self.tongueOutRadioButton.clicked.connect(self.tongueOutRadioButtonCallback)
        self.tongueOutRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('tongue out', 'W') + ' use when tongue is on way to spout')
        self.controlPanelLayout.addWidget(self.tongueOutRadioButton, 0, 12, 1, 1)
        self.tongueOut_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.tongueOut_counter_label, 0, 13, 1, 1)
        
        self.missRadioButton = QtGui.QRadioButton('air lick')
        self.missRadioButton.clicked.connect(self.missRadioButtonCallback)
        self.missRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('air_lick', 'A') + ' use when mouse licks but does not touch spout')
        self.controlPanelLayout.addWidget(self.missRadioButton, 1, 4, 1, 1)
        self.miss_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.miss_counter_label, 1, 5, 1, 1)
        
        self.noLickRadioButton = QtGui.QRadioButton('no label')
        self.noLickRadioButton.clicked.connect(self.noLickRadioButtonCallback)
        self.noLickRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('no_label', '0') + ' default state, no annotation')
        self.controlPanelLayout.addWidget(self.noLickRadioButton, 1, 10, 1, 1)
        self.noLick_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.noLick_counter_label, 1, 11, 1, 1)
        
        self.airgroomRadioButton = QtGui.QRadioButton('air groom')
        self.airgroomRadioButton.clicked.connect(self.airgroomRadioButtonCallback)
        self.airgroomRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('air_groom', 'G') + ' use when mouse is grooming but not contacting spout')
        self.controlPanelLayout.addWidget(self.airgroomRadioButton, 1, 6, 1, 1)
        self.airgroom_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.airgroom_counter_label, 1, 7, 1, 1)
        
        self.nocontactRadioButton = QtGui.QRadioButton('no contact')
        self.nocontactRadioButton.clicked.connect(self.nocontactRadioButtonCallback)
        self.nocontactRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('no_contact', 'N') + ' use when mouse is not contacting spout and no other labels apply')
        self.controlPanelLayout.addWidget(self.nocontactRadioButton, 1, 8, 1, 1)
        self.nocontact_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.nocontact_counter_label, 1, 9, 1, 1)
        
        self.ambiguousRadioButton = QtGui.QRadioButton('ambiguous')
        self.ambiguousRadioButton.clicked.connect(self.ambiguousRadioButtonCallback)
        self.ambiguousRadioButton.setToolTip('Shortcut: ' + self.key_shortcuts.get('ambiguous', 'Q') + ' use to mark frames for further review')
        self.controlPanelLayout.addWidget(self.ambiguousRadioButton, 1, 12, 1, 1)
        self.ambiguous_counter_label = QtGui.QLabel("()")
        self.controlPanelLayout.addWidget(self.ambiguous_counter_label, 1, 13, 1, 1)
        
        self.seek_frame_dropdown = QtGui.QComboBox()
        self.seek_frame_dropdown.addItems(list(sorted(self.annotation_category_dict.keys())))
        #self.seek_frame_dropdown.addItems(['tongue', 'paw', 'groom', 'chin', 'tongue out', 'air lick', 'air groom', 'no contact', 'no label', 'ambiguous'])
        self.seek_frame_dropdown.currentIndexChanged.connect(self.change_seek_selection)
        self.controlPanelLayout.addWidget(self.seek_frame_dropdown, 1, 1, 1, 1)
        self.seek_label = QtGui.QLabel("Seek to: ")
        self.controlPanelLayout.addWidget(self.seek_label, 1, 0, 1, 1)
        self.current_seek_selection = 'tongue'
        
    def change_seek_selection(self):
        self.current_seek_selection = self.seek_frame_dropdown.currentText()
        
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
    
    def seek_category_advance(self):
        desired_category = str(self.current_seek_selection)
        desired_value = self.annotation_category_dict[desired_category]
        
        self.frameIndex += 1
        if self.frameIndex > self.totalVidFrames:
            self.frameIndex = self.totalVidFrames
        
        if desired_category == 'all labels':
            category_frames = np.where(self.lickStates > 0)[0]
        else:
            category_frames = np.where(self.lickStates == desired_value)[0]
            
        if len(category_frames>0):
            next_category_frame_index = np.searchsorted(category_frames, self.frameIndex)
            next_category_frame_index = np.min([next_category_frame_index, len(category_frames)-1])
            next_category_frame = category_frames[next_category_frame_index]
            self.frameIndex = next_category_frame
        
        self.updatePlot()
        
    def seek_category_back(self):
        desired_category = self.current_seek_selection
        desired_value = self.annotation_category_dict[desired_category]
        
        if desired_category == 'all labels':
            category_frames = np.where(self.lickStates > 0)[0]
        else:
            category_frames = np.where(self.lickStates == desired_value)[0]
            
        if len(category_frames>0):
            last_category_frame_index = np.searchsorted(category_frames, self.frameIndex) - 1
            last_category_frame_index = np.max([last_category_frame_index, 0])
            last_category_frame = category_frames[last_category_frame_index]
            self.frameIndex = last_category_frame
        
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
            if thisState==self.annotation_category_dict['no label']: self.noLickRadioButton.click()
            elif thisState==self.annotation_category_dict['tongue']: self.lickRadioButton.click()
            elif thisState==self.annotation_category_dict['paw']: self.runRadioButton.click()
            elif thisState==self.annotation_category_dict['groom']: self.groomRadioButton.click()
            elif thisState==self.annotation_category_dict['air lick']: self.missRadioButton.click()
            elif thisState==self.annotation_category_dict['chin']: self.chinRadioButton.click()
            elif thisState==self.annotation_category_dict['air groom']: self.airgroomRadioButton.click()
            elif thisState==self.annotation_category_dict['no contact']: self.nocontactRadioButton.click()
            elif thisState==self.annotation_category_dict['ambiguous']: self.ambiguousRadioButton.click()
            elif thisState==self.annotation_category_dict['tongue out']: self.tongueOutRadioButton.click()
            
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
        
    def tongueOutRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 8
        self.reset_counters()
    
    def ambiguousRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 9
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
        self.tongueOut_counter_label.setText("(" + str(np.sum(self.lickStates==8)) + ")")
        self.ambiguous_counter_label.setText("(" + str(np.sum(self.lickStates==9)) + ")")
        
  
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
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('tongue_out', 'Key_W')]:
            self.tongueOutRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('ambiguous', 'Key_Q')]:
            self.ambiguousRadioButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('play', 'Key_Space')]:
            self.playVideoButton.click()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('last_detector_frame', 'Key_Down')]:
            self.backFrame(toLastDetectorFrame=True)
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('next_detector_frame', 'Key_Up')]:
            self.advanceFrame(toNextDetectorFrame=True)
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('next_category_frame', 'Key_Period')]:
            self.seek_category_advance()
        if event.key() == QtCore.Qt.__dict__[self.key_shortcuts.get('last_category_frame', 'Key_Comma')]:
            self.seek_category_back()
            
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
 
def extract_lost_frames_from_json(cam_json):
    
    lost_count = cam_json['RecordingReport']['FramesLostCount']
    if lost_count == 0:
        return []
    
    lost_string = cam_json['RecordingReport']['LostFrames'][0]
    lost_spans = lost_string.split(',')
    
    lost_frames = []
    for span in lost_spans:
        
        start_end = span.split('-')
        if len(start_end)==1:
            lost_frames.append(int(start_end[0]))
        else:
            lost_frames.extend(np.arange(int(start_end[0]), int(start_end[1])+1))
    
    return np.array(lost_frames)-1 #you have to subtract one since the json starts indexing at 1 according to Totte
    

def get_frame_exposure_times(sync_dataset, cam_json):
    
    if isinstance(cam_json, str):
        cam_json = read_json(cam_json)
        
    exposure_sync_line_label_dict = {
            'Eye': 'eye_cam_exposing',
            'Face': 'face_cam_exposing',
            'Behavior': 'beh_cam_exposing'}
    
    cam_label =  cam_json['RecordingReport']['CameraLabel']
    sync_line = exposure_sync_line_label_dict[cam_label]
    
    exposure_times = sync_dataset.get_rising_edges(sync_line, units='seconds')
    
    lost_frames = extract_lost_frames_from_json(cam_json)
    total_frames = cam_json['RecordingReport']['FramesRecorded']
    
    frame_times = [e for ie, e in enumerate(exposure_times) if ie not in lost_frames]
    frame_times = frame_times[:total_frames] #trim extra exposures
    frame_times = np.insert(frame_times, 0, 0) #insert dummy time for metadata frame
    
    return np.array(frame_times)  

def read_json(jsonfilepath):
    
    with open(jsonfilepath, 'r') as f:
        contents = json.load(f)
    
    return contents


if __name__ == '__main__':
    start()

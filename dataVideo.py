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
import readIgor
from datetime import datetime

def start():
    QtGui.QApplication.setGraphicsSystem("raster")
    app = QtGui.QApplication.instance()
    if app is None:
        app = QtGui.QApplication([])
    dataVideoObj= dataVideo(app)
    app.exec_()
    
class dataVideo():
    
    def __init__(self, app):
        self.app = app
        self.vid = None
        self.lickStates = None
        self.annotationDataFile = None
        self.lastAnnotatedFrame = None
        self.dataFrameMapping = None
        self.data=None
        self.videoFileName = None
        self.frameIndex = 0
        self.mainWin = QtGui.QMainWindow()
        self.mainWidget = QtGui.QWidget()
        self.mainWin.setCentralWidget(self.mainWidget)
        self.mainWin.closeEvent = self.closeEvent
        self.mainLayout = QtGui.QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)
        self.createMenuBar()
        self.createControlPanel()
        
        self.mainWin.keyPressEvent = self.keyPressCallback
        
        self.imageLayout = pg.GraphicsLayoutWidget()
        self.imageViewBox = self.imageLayout.addViewBox(lockAspect=1,invertY=True,enableMouse=True,enableMenu=True)
        self.imageItem = pg.ImageItem()
        self.imageViewBox.addItem(self.imageItem)   
        self.mainLayout.addWidget(self.imageLayout)
        
        self.plotLayout = pg.GraphicsLayoutWidget()
        self.plot1 = self.plotLayout.addPlot(0,0)
        self.plot1.setClipToView(True)
        self.plot1_infLine = pg.InfiniteLine(movable=True)
        self.plot1_infLine.sigPositionChangeFinished.connect(self.centerPlot1)
        self.plot1.addItem(self.plot1_infLine)
        self.plot2 = self.plotLayout.addPlot(1,0)
        self.mainLayout.addWidget(self.plotLayout, 1, 1, 1, 2)
            
        self.mainWin.show()

        self.annotationDataSaved = False
    
    def getVideoFile(self):
        
        videoChange = False
        if self.vid is not None:
            self.vid.release()
            videoChange = True
            
        self.videoFileName = str(QtGui.QFileDialog.getOpenFileName())
        self.vid = cv2.VideoCapture(self.videoFileName)
        _, self.frame = self.vid.read()
        self.updatePlot()

        self.totalVidFrames = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
        self.frameRate = self.vid.get(cv2.CAP_PROP_FPS)
        self.frameIndex = 0
        self.frameDisplayBox.setText(str(self.frameIndex))
        self.totalFrameCountLabel.setText('/' + str(int(self.totalVidFrames)))

        if videoChange:        
            #pop up to ask if you want to reset the annotation data since the movie has changed
            confirmResetDataMessageBoxReply = QtGui.QMessageBox.question(self.mainWin, 'New Video File', 'Reset Annotation Data?', QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            if confirmResetDataMessageBoxReply == QtGui.QMessageBox.Ok:
                self.resetAnnotationData()
        else:
            self.resetAnnotationData()

        #assert(len(self.lickStates)==self.totalVidFrames)
        
        if self.lastAnnotatedFrame is not None:
            self.frameIndex = self.lastAnnotatedFrame
            self.updatePlot()
        
        self.annotationDataSaved = False

    def loadAnnotationData(self):
        self.annotationDataFile = QtGui.QFileDialog.getOpenFileName(self.mainWin, 'Load Annotation Data', filter='*.npz')
        savedData = np.load(str(self.annotationDataFile))

        self.lickStates = savedData['lickStates']
        self.lastAnnotatedFrame = int(savedData['lastAnnotatedFrame'])
        
        if self.vid is not None:
            assert(len(self.lickStates)==self.totalVidFrames)
            self.frameIndex = self.lastAnnotatedFrame
            self.updatePlot()
        
        #self.plot1.plot(self.lickStates)
        
    def loadDataFrameMapping(self):
        self.dataFrameMappingFile = QtGui.QFileDialog.getOpenFileName(self.mainWin, 'Data Frame Mapping File', filter='*.npy')
        self.dataFrameMapping = np.load(str(self.dataFrameMappingFile))
    
    def loadIgorData(self):
        self.dataFile = QtGui.QFileDialog.getOpenFileName(self.mainWin, 'Igor Data File')
        self.data, self.dataTime = readIgor.getData(self.dataFile)
        self.plot1DataItem = self.plot1.plot(self.data[:, :, 0].flatten())
        
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
            annotationDataFileSaveName = str(QtGui.QFileDialog.getSaveFileName(self.mainWin, 'Save Annotation Data', annotationDataFileSaveName))

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
        
        loadIgor_action = QtGui.QAction('&Load Igor Data', self.mainWin)
        loadIgor_action.triggered.connect(self.loadIgorData)
    
        loadDataFrameMapping_action = QtGui.QAction('&Load Data-Frame mapping', self.mainWin)
        loadDataFrameMapping_action.triggered.connect(self.loadDataFrameMapping)

        file_menu.addAction(open_action)
        file_menu.addAction(loadAnnotations_action)
        file_menu.addAction(loadDataFrameMapping_action)
        file_menu.addAction(saveAnnotations_action)
        file_menu.addAction(loadIgor_action)
             
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
        
        self.lickRadioButton = QtGui.QRadioButton('lick')
        self.lickRadioButton.clicked.connect(self.lickRadioButtonCallback)
        self.lickRadioButton.setToolTip('Shortcut: L')
        self.controlPanelLayout.addWidget(self.lickRadioButton, 0, 4, 1, 1)
        
        self.contactRadioButton = QtGui.QRadioButton('other contact')
        self.contactRadioButton.clicked.connect(self.contactRadioButtonCallback)
        self.contactRadioButton.setToolTip('Shortcut: C')
        self.controlPanelLayout.addWidget(self.contactRadioButton, 0, 5, 1, 1)
        
        self.noLickRadioButton = QtGui.QRadioButton('no lick')
        self.noLickRadioButton.clicked.connect(self.noLickRadioButtonCallback)
        self.noLickRadioButton.setToolTip('Shortcut: N')
        self.controlPanelLayout.addWidget(self.noLickRadioButton, 0, 6, 1, 1)

    def advanceFrame(self):
        self.frameIndex += 1
        if self.frameIndex > self.totalVidFrames:
            self.frameIndex = self.totalVidFrames
        
        self.updatePlot()
        
    def backFrame(self):
        self.frameIndex -= 1
        if self.frameIndex < 0:
            self.frameIndex = 0
        
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
            if self.data is not None:
                self.syncVideoAndData()
        
    def syncVideoAndData(self):
        if self.dataFrameMapping is None:
            self.plot1_infLine.setValue(self.frameIndex)
        else:
            self.plot1_infLine.setValue(self.dataFrameMapping[self.frameIndex])
        
        self.plot1_infLine.sigPositionChangeFinished.emit(self.plot1_infLine)
        
    def setRadioButtonStates(self):
        if self.lickStates is not None:
            thisState = self.lickStates[self.frameIndex]
            if thisState > 1: self.contactRadioButton.click()
            elif thisState < 1: self.noLickRadioButton.click()
            else: self.lickRadioButton.click()
            
    def lickRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 1
    
    def noLickRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 0

    def contactRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 2
  
    def keyPressCallback(self, event):
        
        if event.key() == QtCore.Qt.Key_Left:
            self.backFrame()
        if event.key() == QtCore.Qt.Key_Right:
            self.advanceFrame()
        if event.key() == QtCore.Qt.Key_L:
            self.lickRadioButton.click()
        if event.key() == QtCore.Qt.Key_N:
            self.noLickRadioButton.click()
        if event.key() == QtCore.Qt.Key_C:
            self.contactRadioButton.click()
        if event.key() == QtCore.Qt.Key_Space:
            self.playVideoButton.click()
            
    def centerPlot1(self):
        xMin, xMax = self.plot1.viewRange()[0]
        halfXRange = (xMax-xMin)/2
        linePos = self.plot1_infLine.value()
        #self.plot1.plot(self.data[:, :, 0].flatten()[int(linePos-halfXRange):int(linePos+halfXRange)])        
        self.plot1.setXRange(linePos-halfXRange, linePos+halfXRange, padding=0)
        #xs = np.arange(int(linePos-halfXRange), int(linePos+halfXRange))
        #ys = self.data[:, :, 0].flatten()[int(linePos-halfXRange):int(linePos+halfXRange)]

        #self.plot1DataItem.setData(x=xs, y=ys)
        #self.plot1DataItem.clipToView=True
        
        closestFrame = np.searchsorted(self.dataFrameMapping, linePos)
        if abs(self.frameIndex-closestFrame)>1:
            self.frameIndex = closestFrame
            self.updatePlot()

        
if __name__ == '__main__':
    start()

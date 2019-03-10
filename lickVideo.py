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

def start():
    QtGui.QApplication.setGraphicsSystem("raster")
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
        self.frameIndex = 0
        self.mainWin = QtGui.QMainWindow()
        self.mainWidget = QtGui.QWidget()
        self.mainWin.setCentralWidget(self.mainWidget)
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
        self.mainWin.show()
    
    def getVideoFile(self):
        
        if self.vid is not None:
            self.vid.release()
            
        self.videoFileName = QtGui.QFileDialog.getOpenFileName()
        self.vid = cv2.VideoCapture(str(self.videoFileName))
        _, self.frame = self.vid.read()
        self.updatePlot()

        self.totalVidFrames = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
        self.frameRate = self.vid.get(cv2.CAP_PROP_FPS)
        self.frameIndex = 0
        self.frameDisplayBox.setText(str(self.frameIndex))
        self.totalFrameCountLabel.setText('/' + str(int(self.totalVidFrames)))
        
        if self.annotationDataFile is None:
            self.resetAnnotationData()
        else:
            assert(len(self.lickStates)==self.totalVidFrames)
        
    def loadAnnotationData(self):
        self.annotationDataFile = QtGui.QFileDialog.getOpenFileName()
        self.lickStates = np.load(str(self.annotationDataFile))
        if self.vid is not None:
            assert(len(self.lickStates)==self.totalVidFrames)
    
    def saveAnnotationData(self):
        annotationDataFileSaveName = QtGui.QFileDialog.getSaveFileName()
        np.save(str(annotationDataFileSaveName), self.lickStates)
        
    def resetAnnotationData(self):
        self.lickStates = np.zeros(int(self.totalVidFrames))
        
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
    
        file_menu.addAction(open_action)
        file_menu.addAction(loadAnnotations_action)
        file_menu.addAction(saveAnnotations_action)
             
    def createControlPanel(self):
        #make layout for gui controls and add to main layout
        self.controlPanelLayout = QtGui.QGridLayout()
        self.mainLayout.addLayout(self.controlPanelLayout, 0, 0)
        
        self.playVideoButton = QtGui.QPushButton('>')
        self.playVideoButton.setCheckable(True)
        self.playVideoButton.clicked.connect(self.playVideo)
        self.controlPanelLayout.addWidget(self.playVideoButton, 0, 0)
        self.playTimer = QtCore.QTimer()
        self.playTimer.timeout.connect(self.advanceFrame)
        
        frameLabel = QtGui.QLabel("Frame:")
        self.controlPanelLayout.addWidget(frameLabel, 0, 1)
        
        self.frameDisplayBox = QtGui.QLineEdit()
        self.frameDisplayBox.editingFinished.connect(self.goToFrame)
        self.controlPanelLayout.addWidget(self.frameDisplayBox, 0, 2)
        
        self.totalFrameCountLabel = QtGui.QLabel("/")
        self.controlPanelLayout.addWidget(self.totalFrameCountLabel, 0, 3)
        
        self.lickRadioButton = QtGui.QRadioButton('lick')
        self.lickRadioButton.clicked.connect(self.lickRadioButtonCallback)
        self.lickRadioButton.setToolTip('Shortcut: L')
        self.controlPanelLayout.addWidget(self.lickRadioButton, 0, 4)
        
        self.contactRadioButton = QtGui.QRadioButton('other contact')
        self.contactRadioButton.clicked.connect(self.contactRadioButtonCallback)
        self.contactRadioButton.setToolTip('Shortcut: C')
        self.controlPanelLayout.addWidget(self.contactRadioButton, 0, 5)
        
        self.noLickRadioButton = QtGui.QRadioButton('no lick')
        self.noLickRadioButton.clicked.connect(self.noLickRadioButtonCallback)
        self.noLickRadioButton.setToolTip('Shortcut: N')
        self.controlPanelLayout.addWidget(self.noLickRadioButton, 0, 6)

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
        self.frameIndex = int(self.frameDisplayBox.text())
        if self.frameIndex > self.totalVidFrames:
            self.frameIndex = self.totalVidFrames
        elif self.frameIndex < 0:
            self.frameIndex = 0
        
        self.updatePlot()
        self.frameDisplayBox.clearFocus()
    
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
        
        
    def setRadioButtonStates(self):
        if self.lickStates is not None:
            thisState = self.lickStates[self.frameIndex]
            if thisState > 1: self.contactRadioButton.click()
            elif thisState < 1: self.noLickRadioButton.click()
            else: self.lickRadioButton.click()
            
    def lickRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 1
        print('lick')
        print(self.lickStates[:10])
    
    def noLickRadioButtonCallback(self):
        if self.lickStates is not None:
            self.lickStates[self.frameIndex] = 0
            print('no lick')
            print(self.lickStates[:10])

    def contactRadioButtonCallback(self):
        self.lickStates[self.frameIndex] = 2
        print('contact')
        print(self.lickStates[:10])

    
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

            
    
        
if __name__ == '__main__':
    start()

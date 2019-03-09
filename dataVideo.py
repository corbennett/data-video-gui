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

        self.videoFileName = QtGui.QFileDialog.getOpenFileName()
        self.vid = cv2.VideoCapture(self.videoFileName)
        _, self.frame = self.vid.read()
        self.updatePlot()
        
#        self.imageItem = pg.ImageItem(self.frame[:, :, 0].T)
#        self.imageViewBox.addItem(self.imageItem)
        self.totalVidFrames = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
        self.frameRate = self.vid.get(cv2.CAP_PROP_FPS)
        self.frameIndex = 0
        self.frameDisplayBox.setText(str(self.frameIndex))
        
    def createMenuBar(self):
        # create an instance of menu bar
        menubar = self.mainWin.menuBar()
        # add file menu and file menu actions
        file_menu = menubar.addMenu('&File')
        
        # file menu actions
        open_action = QtGui.QAction('&Open Video', self.mainWin)
        open_action.triggered.connect(self.getVideoFile)
    
        file_menu.addAction(open_action)
     
    def createControlPanel(self):
        #make layout for gui controls and add to main layout
        self.controlPanelLayout = QtGui.QGridLayout()
        self.mainLayout.addLayout(self.controlPanelLayout, 0, 0)
        
        self.backFrameButton = QtGui.QPushButton('<')
        self.backFrameButton.clicked.connect(self.backFrame)
        self.controlPanelLayout.addWidget(self.backFrameButton, 0, 0)
        
        self.advanceFrameButton = QtGui.QPushButton('>')
        self.advanceFrameButton.clicked.connect(self.advanceFrame)
        self.controlPanelLayout.addWidget(self.advanceFrameButton, 0, 1)
              
        self.frameDisplayBox = QtGui.QLineEdit()
        self.frameDisplayBox.editingFinished.connect(self.goToFrame)
        self.controlPanelLayout.addWidget(self.frameDisplayBox, 0, 2)

    def advanceFrame(self):
        ret, self.frame = self.vid.read()
        if ret:
            self.updatePlot()
        else:
            print('Error reading video. Likely reached video limit.')
    
    def backFrame(self):
        self.vid.set(cv2.CAP_PROP_POS_FRAMES, self.frameIndex - 1)
        ret, self.frame = self.vid.read()
        if ret:
            self.updatePlot()
        else:
            print('Error reading video. Likely reached video limit.')
    
    def goToFrame(self):
        if self.vid is not None:
#            self.vid.set(cv2.CAP_PROP_POS_FRAMES, int(self.frameDisplayBox.text())+1)
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, self.frameIndex)
            ret, self.frame = self.vid.read()
            if ret:
                self.updatePlot()
            else:
                print('Invalid frame given')
            
    def updatePlot(self):
        self.imageItem.setImage(self.frame[:,:,0].T)
        self.frameIndex = int(self.vid.get(cv2.CAP_PROP_POS_FRAMES)-1)
        self.frameDisplayBox.setText(str(self.frameIndex))
                
    def keyPressCallback(self, event):
        
        if event.key() == QtCore.Qt.Key_Left:
            self.backFrame()
        if event.key() == QtCore.Qt.Key_Right:
            self.advanceFrame()
        


        
if __name__ == '__main__':
    start()
    

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 09:36:35 2019

@author: corbennett
"""

import scipy.io
import readIgor
import numpy as np
from matplotlib import pyplot as plt

#Get eye data from mat file and find flash frames
eyeDataFile = "/Volumes/LC/Castor and Pollux/data with eyetracking/06292015/06292015B_real1_eyeData.mat"
eyeData = scipy.io.loadmat(eyeDataFile, struct_as_record=False, squeeze_me=True)
flashFrames = eyeData['flashFrames']

#Get Igor data and find flash samples
igorDataFile = "/Volumes/LC/Castor and Pollux/data with eyetracking/06292015/06292015B.009"
igorData, igorTime = readIgor.getData(igorDataFile)
sampleRate = round(1/np.mean(np.diff(igorTime))*1000)
running = readIgor.readBall(igorData, [2,3], sampleRate)

flashSamples = np.arange(0, igorData.shape[1]*igorData.shape[0], igorData.shape[1])

#Map frames to samples
frameSamples = np.full(len(eyeData['pupilArea']), np.nan)
frameSamples[flashFrames[:flashSamples.size]] = flashSamples
nans, x= np.isnan(frameSamples), lambda z: z.nonzero()[0]
frameSamples[nans]= np.interp(x(nans), x(~nans), frameSamples[~nans]).astype(np.int)
frameSamples[:flashFrames[0]] = 0

trace = 2
plt.figure()
plt.plot(igorData[trace, :, 0])
plt.figure()
plt.plot(frameSamples[flashFrames[trace]:flashFrames[trace+1]], eyeData['pupilArea'][flashFrames[trace]:flashFrames[trace+1]])


plt.figure()
plt.plot(frameSamples, eyeData['pupilArea'])
plt.plot(running.flatten())
plt.plot(igorData[:, :, 4].flatten())
plt.plot(igorData[:, :, 0].flatten())
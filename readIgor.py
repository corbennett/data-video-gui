#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 13 01:22:00 2017

@author: corbennett
"""
from __future__ import division
import numpy as np
import fileIO
from scipy.stats import mode

def getData(file=None):
    if file is None:
        file = fileIO.getfile()
    a = open(file, 'rb')
    
    #Get header size from first byte of file: a single precision, little endian float
    [headerSize, waveSize] = np.fromfile(a, dtype='<f', count=2)
    
    #Read header
    header_dt = 'a' + str(int(headerSize))
    header = str(np.fromfile(a, dtype=header_dt, count=1))
    hwave = np.fromfile(a, dtype='<f', count=1)
    
    #Get total channel number (including dummy channels)
    total_chan_num = int(getKeyValue(header, 'total_chan_num', ':', ';'))
    
    #Get sample frequency and samples per trace and trace num
    freq = float(getKeyValue(header, 'freq', ':', ';'))
    samples = int(getKeyValue(header, 'samples', ':', ';'))
    
    
    #Get gains and status for adcs
    adcGains = []
    adcStatus = []
    for adc in range(8):
        stringToFind = 'adc_gain' + str(adc)
        adcGains.append(float(getKeyValue(header, stringToFind, ':', ';')))
        stringToFind = 'adc_status' + str(adc)
        adcStatus.append(int(getKeyValue(header, stringToFind, '>', '|')))
    
    adcGains = np.array(adcGains)
    adcStatus = np.array(adcStatus)
    adcGains = 3.2*adcGains[adcStatus==1]
    
    data = np.fromfile(a, dtype='<i2')
    traces = int(data.size/(total_chan_num*samples))
    data = np.reshape(data, [traces, samples, total_chan_num])
    
    time = np.linspace(0, samples/freq, samples)
    
    return data[:, :, :adcGains.size]/np.array(adcGains)[None,None,:], time
    
def getKeyValue(header, key, keyValSeparator, delimiter):
    stringToFind = key + keyValSeparator
    indexStart = header.find(stringToFind) + len(stringToFind)
    indexEnd = header[indexStart:].find(delimiter) + indexStart
    return header[indexStart:indexEnd]

def readBall(data, ballChannels, sampleRate, convWindowSize=0.1):
    #Data should be [traces, samples, channels], sampleRate should be in Hz
    #and convWindowSize should be in seconds
    
    ball = data[:, :, ballChannels]
    ballModeValues = mode(ball[0])[0][0]
    ball -= ballModeValues
    centimeterConversionFactor = 19.298 * sampleRate/10

    convWin = np.ones(round(convWindowSize*sampleRate))
    speed = []
    for trial in range(data.shape[0]):    
        trialball = np.array([np.convolve(ball[trial, :, c], convWin, mode='same') for c in [0, 1]])/convWindowSize
        trialball /= centimeterConversionFactor
        speed.append((trialball[0]**2 + trialball[1]**2)**0.5)

    return np.array(speed)
    


    


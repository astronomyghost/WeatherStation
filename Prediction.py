import numpy as np
from PIL import Image
import datetime
import math
import sqlite3 as sql

class CloudCover:
    def __init__(self, fileName):
        # Converts the image into an array for easier analysis
        self.refImage = Image.open(fileName)
        self.refLoad = self.refImage.load()
        self.totalClear, self.totalCloud, self.coverPercentage = 0,0,0
        self.xMaximum, self.yMaximum = self.refImage.size
        self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    def calcCoverPercentage(self):
        self.coverPercentage = (self.totalCloud/(self.totalClear+self.totalCloud))*100
        return self.coverPercentage
    def determineCondition(self):
        if self.coverPercentage > 90:
            return "Overcast"
        elif self.coverPercentage < 90 and self.coverPercentage > 60:
            return "Mostly cloudy"
        elif self.coverPercentage < 60 and self.coverPercentage > 30:
            return "Slightly cloudy"
        else:
            return "Clear"
    def classifyPixel(self, xPixel, yPixel):
        # Determines whether the pixel is cloudy (grey or white) or sky (blue)
        r,g,b = self.refLoad[xPixel,yPixel]
        totalPixelValue = r+g+b
        if (r,g,b) != (0,0,0):
            # Percentage blue constant is defined as 0.45
            if (b/totalPixelValue) > 0.45:
                self.totalClear += 1
            else:
                self.totalCloud += 1
    def linearScan(self):
        # Performs a linear scan across the image, row upon row
        yTemp = 0
        for i in range(self.yMaximum):
            xTemp = 0
            for j in range(self.xMaximum):
                # Calls the classifyPixel function
                self.classifyPixel(xTemp, yTemp)
                xTemp += 1
            yTemp += 1

class prediction:
    def __init__(self, locationID, cur):
        self.locationID = locationID
        self.cur = cur
    def grab(self, dataType, period):
        self.cur.execute('SELECT Timestamp, Value FROM Samples WHERE TypeID=? AND LocationID=?',(dataType, self.locationID,))
        dataset = self.cur.fetchall()
        currentTime = datetime.datetime.now()
        data = []
        time = []
        for i in range(len(dataset)):
            sampleTime = datetime.datetime.strptime(dataset[i][0], '%Y-%m-%d, %H:%M:%S')
            deltaTime = (sampleTime- currentTime).total_seconds()
            if deltaTime >= -period and deltaTime <= 0:
                data.append(dataset[i][1])
                time.append(dataset[i][0])
        return data, time
    def linearRegression(self, dataType, period):
        self.cur.execute('SELECT Timestamp, Value FROM Samples WHERE TypeID=? AND LocationID=?',(dataType, self.locationID,))
        dataset = self.cur.fetchall()
        currentTime = datetime.datetime.now()
        self.x_train, self.y_train = np.array([]), np.array([])
        for i in range(len(dataset)):
            sampleTime = datetime.datetime.strptime(dataset[i][0], '%Y-%m-%d, %H:%M:%S')
            deltaTime = (currentTime-sampleTime).total_seconds()
            if deltaTime <= period:
                self.x_train = np.append(self.x_train, [(period-deltaTime)])
                self.y_train = np.append(self.y_train, [(dataset[i][1])])
        self.n = len(self.x_train)
        meanX = np.mean(self.x_train)
        meanY = np.mean(self.y_train)
        XY = np.sum(np.multiply(self.y_train, self.x_train)) - self.n * meanY * meanX
        XX = np.sum(np.multiply(self.x_train, self.x_train)) - self.n * meanX * meanX
        self.m = XY / XX
        self.c = meanY - self.m * meanX
        if len(self.y_train) > 1:
            return self.y_train[len(self.y_train)-1]
        if len(self.y_train) == 1:
            self.m = 0
            self.c = self.y_train[len(self.y_train)-1]
            return self.y_train[len(self.y_train)-1]
        else:
            return "null"
    def hourPrediction(self, timeAfterHour):
        predictedTemp = self.m * (3600+(timeAfterHour*60)) + self.c
        return predictedTemp
    def checkTrend(self):
        if self.m < 0:
            return "decrease"
        if self.m == 0:
            return "stay constant"
        if self.m > 0:
            return "increase"

def checkTimeFormat(timeIn):
    if len(str(timeIn)) == 1:
        timeOut = "0"+str(timeIn)
    else:
        timeOut = str(timeIn)
    return timeOut

def makeTimestamp(timeAccessed, i, time):
    newTimestamp = timeAccessed + datetime.timedelta(minutes=i)
    newTimestamp = newTimestamp.strftime('%Y-%m-%d, %H:%M:%S')
    time.append(newTimestamp)

def appendValues(data, ID, period, dataset):
    latestValue = dataset.linearRegression(ID, period)
    time = []
    timeAccessed = datetime.datetime.now()
    if not (type(latestValue) is str):
        oldTemperatures, oldTime = dataset.grab(ID, period)
        for i in range(len(oldTemperatures)):
            data.append(oldTemperatures[i])
            time.append(oldTime[i])
        for j in range(60):
            data.append(dataset.hourPrediction(j))
            makeTimestamp(timeAccessed, j, time)
    else:
        data.append("Not enough data")
    return data, time, latestValue

def minuteCast(locationID, cur):
    availableData = []
    dataset = prediction(locationID, cur)
    availableTimes, latestValues, trendInfoList = [], [], []
    for i in range(1,5):
        temporaryList = []
        temporaryList, time, latestValue = appendValues(temporaryList, i, 3600, dataset)
        availableData.append(tuple(temporaryList))
        availableTimes.append(time)
        latestValues.append(latestValue)
        trendInfoList.append(dataset.checkTrend())
    return availableData, availableTimes, latestValues, trendInfoList

def grabTimeline(locationID, dataType, cur):
    dataset = prediction(locationID, cur)
    cur.execute("SELECT SampleID FROM Samples")
    n = cur.fetchall()
    data, time = dataset.grab(dataType, 100000000000000000000)
    return data, time



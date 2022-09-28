import numpy as np
from PIL import Image
import datetime, os
import sqlite3 as sql
import pandas as pd
import statsmodels.tsa.statespace.sarimax as sm

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
    def grab(self, sampleType, period):
        print(sampleType, self.locationID)
        self.cur.execute('SELECT Timestamp, Value FROM Samples WHERE TypeID=? AND LocationID=?',(sampleType, self.locationID,))
        dataset = self.cur.fetchall()
        currentTime = datetime.datetime.now()
        data = []
        time = []
        for i in range(len(dataset)):
            sampleTime = datetime.datetime.strptime(dataset[i][0], '%Y-%m-%d, %H:%M:%S')
            deltaTime = (sampleTime- currentTime).total_seconds()
            if deltaTime >= -period and deltaTime <= 0:
                count = 0
                for j in range(len(data)):
                    if time[j] == dataset[i][0]:
                        data.append((dataset[i][1]+data[j])/2)
                        time.append(dataset[i][0])
                        del data[j], time[j]
                    else:
                        count += 1
                if count == len(data):
                    data.append(dataset[i][1])
                    time.append(dataset[i][0])
        return data, time
    def prepareDataset(self, dataset, periodType):
        prepDataset = pd.DataFrame(dataset)
        prepDataset = prepDataset.set_index('Datetime')
        prepDataset = prepDataset.resample(periodType).ffill().reset_index()
        prepDataset = prepDataset.set_index('Datetime')
        return prepDataset
    def timeSeriesForecast(self, sampleType, period, periodType, locationID):
        data, time = self.grab(sampleType, 100000000000000)
        if(len(data) > 1 and type(data[0]) == float):
            trainDataSet = {'Datetime': pd.to_datetime(time), 'Data': data}
            df_trainDataSet = self.prepareDataset(trainDataSet, periodType)
            if not os.path.exists(periodType+'Models\model-'+str(sampleType)+'-'+str(locationID)+'.pkl'):
                mod = sm.SARIMAX(df_trainDataSet,order=(1,1,1), seasonal_order=(0,1,0, 12), trend='t',
                                                enforce_stationarity=False, enforce_invertibility=False)
                results = mod.fit()
                results.save(periodType+'Models\model-'+str(sampleType)+'-'+str(locationID)+'.pkl')
                forecast = results.forecast(steps=period, dynamic=False)
            else:
                results = sm.SARIMAXResults.load(periodType+'Models\model-'+str(sampleType)+'-'+str(locationID)+'.pkl')
                forecast = results.forecast(steps=period, dynamic=False)
            return forecast
        else:
            return "None"
    def linearRegression(self, sampleType, period):
        self.cur.execute('SELECT Timestamp, Value FROM Samples WHERE TypeID=? AND LocationID=?',(sampleType, self.locationID,))
        dataset = self.cur.fetchall()
        currentTime = datetime.datetime.now()
        x_train, y_train = np.array([]), np.array([])
        for i in range(len(dataset)):
            sampleTime = datetime.datetime.strptime(dataset[i][0], '%Y-%m-%d, %H:%M:%S')
            deltaTime = (currentTime-sampleTime).total_seconds()
            if deltaTime <= period:
                x_train = np.append(x_train, [(period-deltaTime)])
                y_train = np.append(y_train, [(dataset[i][1])])
        if(len(dataset) > 0):
            if(type(dataset[0][1]) == float):
                self.n = len(x_train)
                meanX = np.mean(x_train)
                meanY = np.mean(y_train)
                XY = np.sum(np.multiply(y_train, x_train)) - self.n * meanY * meanX
                XX = np.sum(np.multiply(x_train, x_train)) - self.n * meanX * meanX
                self.m = XY / XX
                self.c = meanY - self.m * meanX
                if len(y_train) > 1:
                    return y_train[len(y_train)-1]
                if len(y_train) == 1:
                    self.m = 0
                    self.c = y_train[len(y_train)-1]
                    return y_train[len(y_train)-1]
                else:
                    return "null"
            else:
                self.m = 0
                return "null"
        else:
            self.m = 0
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

def bubbleSort(data, time):
    currentTime = datetime.datetime.now()
    for i in range(len(data)):
        for j in range(len(data)-(i+1)):
            deltaTime1 = (datetime.datetime.strptime(time[j+i], '%Y-%m-%d, %H:%M:%S') - currentTime).total_seconds()
            deltaTime2 = (datetime.datetime.strptime(time[j+i+1], '%Y-%m-%d, %H:%M:%S') - currentTime).total_seconds()
            if deltaTime1 > deltaTime2:
                tempStoreData, tempStoretime = data[i+j], time[i+j]
                time[i+j], data[i+j] = time[i+j+1], data[i+j+1]
                time[i + j + 1], data[i + j + 1] = tempStoretime, tempStoreData
    return data, time

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
        oldTemperatures, oldTime = bubbleSort(oldTemperatures, oldTime)
        for i in range(len(oldTemperatures)):
            data.append(oldTemperatures[i])
            time.append(oldTime[i])
        for j in range(60):
            data.append(dataset.hourPrediction(j))
            makeTimestamp(timeAccessed, j, time)
    else:
        data.append("Not enough data")
    return data, time, latestValue

def minuteCast(locationID, cur, sampleTypes):
    availableData = []
    dataset = prediction(locationID, cur)
    availableTimes, latestValues, trendInfoList = [], [], []
    for i in range(len(sampleTypes)):
        temporaryList = []
        temporaryList, time, latestValue = appendValues(temporaryList, i+1, 3600, dataset)
        availableData.append(tuple(temporaryList))
        availableTimes.append(time)
        latestValues.append(latestValue)
        trendInfoList.append(dataset.checkTrend())
    return availableData, availableTimes, latestValues, trendInfoList

def grabTimeline(locationID, sampleType, cur):
    dataset = prediction(locationID, cur)
    data, time = dataset.grab(sampleType, 100000000000000000000)
    return data, time

def machineLearning(locationID, sampleType, cur, period, periodType):
    time = []
    dataset = prediction(locationID, cur)
    forecast = dataset.timeSeriesForecast(sampleType, period, periodType, locationID)
    if isinstance(forecast, str):
        data, time = [0,0]
    else:
        data = forecast.values
        for i in range(len(forecast.index)):
            time.append(datetime.datetime.strftime(forecast.index[i], '%Y-%m-%d, %H:%M:%S'))
        data = data.tolist()
    return data, time

def checkStormWarning(cur, locationID, periodOfConcern):
    dataset = prediction(locationID, cur)
    data, time = dataset.grab(5, periodOfConcern)
    if(len(time) == 0):
        return "None"
    else:
        return time[0]


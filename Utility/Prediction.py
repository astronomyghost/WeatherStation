import numpy as np
import datetime, os
import sqlite3 as sql
import pandas as pd
import statsmodels.tsa.statespace.sarimax as sm

class sample:
    def __init__(self, data, timestamp):
        self.data = data
        self.timestamp = timestamp

class calculateRatingOfTime:
    def __init__(self, time, temperature, pressure, cloudCover, humidity):
        self.temperature, self.pressure, self.cloudCover, self.humidity = temperature, pressure, cloudCover, humidity
        self.time = time
        self.score = 0
        self.accuracy = 0
    def temperatureRating(self):
        if type(self.temperature) != str:
            self.score += ((140-(self.temperature+40))/140)*0.25
            self.accuracy += 0.25
    def pressureRating(self):
        if type(self.pressure) != str:
            self.score += ((self.pressure-950)/100)*0.25
            self.accuracy += 0.25
    def cloudCoverRating(self):
        if type(self.cloudCover) != str:
            self.score += ((100-(self.cloudCover))/100)*0.25
            self.accuracy += 0.25
    def humidityRating(self):
        if type(self.humidity) != str:
            self.score += ((100-(self.humidity))/100)*0.25
            self.accuracy += 0.25
    def darknessRating(self, sunrise, sunset):
        if self.time != 0:
            deltaTimeSunset = (self.time-sunset).total_seconds()
            deltaTimeSunrise = (sunrise-self.time).total_seconds()
            if deltaTimeSunset < 6000:
                self.score = self.score*(deltaTimeSunset/6000)
            elif deltaTimeSunrise < 6000:
                self.score = self.score * (deltaTimeSunrise / 6000)
    def fullRating(self, sunrise, sunset):
        self.temperatureRating()
        self.pressureRating()
        self.cloudCoverRating()
        self.humidityRating()
        self.darknessRating(sunrise, sunset)
        return self.score

class prediction:
    def __init__(self, locationID, cur):
        self.locationID = locationID
        self.cur = cur
    def selectRecordsInPeriod(self, sampleType, period):
        self.cur.execute('SELECT Timestamp, Value FROM Samples WHERE TypeID=? AND LocationID=?',(sampleType, self.locationID,))
        dataset = self.cur.fetchall()
        currentTime = datetime.datetime.now()
        data = []
        time = []
        for i in range(len(dataset)):
            sampleTime = datetime.datetime.strptime(dataset[len(dataset)-i-1][0], '%Y-%m-%d, %H:%M:%S')
            deltaTime = (currentTime- sampleTime).total_seconds()
            if deltaTime <= period:
                count = 0
                for j in range(len(data)):
                    if time[j] == dataset[len(dataset)-i-1][0]:
                        data.append((dataset[len(dataset)-i-1][1]+data[j])/2)
                        time.append(dataset[len(dataset)-i-1][0])
                        print("Duplicate detected: "+str((dataset[len(dataset)-i-1][1]+data[j])/2))
                        del data[j], time[j]
                    else:
                        count += 1
                if count == len(data):
                    data.append(dataset[len(dataset)-i-1][1])
                    time.append(dataset[len(dataset)-i-1][0])
        return data, time
    def prepareDataset(self, dataset, periodType):
        prepDataset = pd.DataFrame(dataset)
        prepDataset = prepDataset.set_index('Datetime')
        prepDataset = prepDataset.ffill()
        return prepDataset
    def timeSeriesForecast(self, sampleType, period, periodType, locationID):
        path = periodType+'model-'+str(sampleType)+'-'+str(locationID)+'.pkl'
        if (not os.path.exists(path)) or ((datetime.datetime.now()-datetime.datetime.fromtimestamp(os.path.getctime(path))).total_seconds() >= 86400):
            data, time = self.selectRecordsInPeriod(sampleType, 604800)
            if (len(data) > 1):
                trainDataSet = {'Datetime': pd.to_datetime(time).to_period(periodType), 'Data': data}
                df_trainDataSet = self.prepareDataset(trainDataSet, periodType)
                mod = sm.SARIMAX(df_trainDataSet,order=(1,1,1), seasonal_order=(0,1,0, 12), trend='t',
                                                enforce_stationarity=False, enforce_invertibility=False)
                results = mod.fit()
                results.save(path)
                forecast = results.forecast(steps=period, dynamic=False)
            else:
                return "None"
        else:
            results = sm.SARIMAXResults.load(path)
            forecast = results.forecast(steps=period, dynamic=False)
        return forecast
    def linearRegression(self, sampleType, period):
        currentTime = datetime.datetime.now()
        x_train, y_train = np.array([]), np.array([])
        data, time = self.selectRecordsInPeriod(sampleType, period)
        for i in range(len(time)):
            y_train = np.append(y_train, [data[i]])
            dTime = (currentTime-datetime.datetime.strptime(time[i], '%Y-%m-%d, %H:%M:%S')).total_seconds()
            x_train = np.append(x_train, [period-dTime])
        if(len(data) > 0):
            if(type(data[0]) == int or type(data[0]) == float):
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
            deltaTime1 = (datetime.datetime.strptime(time[j], '%Y-%m-%d, %H:%M:%S') - currentTime).total_seconds()
            deltaTime2 = (datetime.datetime.strptime(time[j+1], '%Y-%m-%d, %H:%M:%S') - currentTime).total_seconds()
            if deltaTime1 > deltaTime2:
                tempStoreData, tempStoretime = data[j], time[j]
                time[j], data[j] = time[j+1], data[j+1]
                time[j + 1], data[j + 1] = tempStoretime, tempStoreData
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
        oldTemperatures, oldTime = dataset.selectRecordsInPeriod(ID, period)
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
    data, time = dataset.selectRecordsInPeriod(sampleType, 100000000000000000000)
    return data, time

def machineLearning(locationID, sampleType, cur, period, periodType):
    data = []
    time = []
    dataset = prediction(locationID, cur)
    forecast = dataset.timeSeriesForecast(sampleType, period, periodType, locationID)
    if isinstance(forecast, str):
        for i in range(period):
            data.append(0)
            time.append(0)
    else:
        data = forecast.values
        for i in range(len(forecast.index)):
            time.append(datetime.datetime.strftime(forecast.index[i].to_timestamp(), '%Y-%m-%d, %H:%M:%S'))
        data = data.tolist()
    return data, time

def checkStormWarning(cur, locationID, periodOfConcern):
    dataset = prediction(locationID, cur)
    data, time = dataset.selectRecordsInPeriod(5, periodOfConcern)
    if(len(time) == 0):
        return "None"
    else:
        return time[0]

def findBestTimeForAstro(time, data, latitude, longitude):
    scores = []
    sun = Sun(latitude, longitude)
    dateToday = datetime.date.today()
    dateTomorrow = dateToday+datetime.timedelta(days=1)
    sunrise = sun.get_local_sunrise_time(dateTomorrow).replace(tzinfo=None)
    sunset = sun.get_local_sunset_time(dateToday).replace(tzinfo=None)
    timeUse = 0
    for i in range(len(data[0])-1):
        for j in range(len(time)-1):
            if time[j][i] != 0:
                timeUse = j
        sample = calculateRatingOfTime(datetime.datetime.strptime(time[timeUse][i], '%Y-%m-%d, %H:%M:%S'), data[0][i], data[2][i], data[3][i], data[1][i])
        scores.append(sample.fullRating(sunrise, sunset))
    return scores
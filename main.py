import numpy as np
from PIL import Image
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import math

class CloudCover:
    def __init__(self, fileName):
        self.refImage = Image.open(fileName)
        self.refLoad = self.refImage.load()
        self.totalClear, self.totalCloud, self.coverPercentage = 0,0,0
        self.xMaximum, self.yMaximum = self.refImage.size
        try:
            self.timestamp = self.refImage.getexif()[36867]
        except:
            self.timestamp = datetime.datetime.now()
    def calcCoverPercentage(self):
        self.coverPercentage = (self.totalCloud/(self.totalClear+self.totalCloud))*100
        print("Cloud cover :"+str(self.coverPercentage))
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
        r,g,b = self.refLoad[xPixel,yPixel]
        totalPixelValue = r+g+b
        if (r,g,b) != (0,0,0):
            if (b/totalPixelValue) > 0.45:
                self.totalClear += 1
            else:
                self.totalCloud += 1
    def linearScan(self):
        yTemp = 0
        for i in range(self.yMaximum):
            xTemp = 0
            for j in range(self.xMaximum):
                self.classifyPixel(xTemp, yTemp)
                xTemp += 1
            yTemp += 1

class prediction:
    def __init__(self, datasetName):
        self.weatherData = pd.read_csv(datasetName)
    def linearRegression(self, x_field, y_field, period):
        self.x_train = (self.weatherData.loc[:, x_field])[len(self.weatherData.loc[:, "ID"])-period:len(self.weatherData.loc[:, "ID"])]
        self.y_train = (self.weatherData.loc[:, y_field])[len(self.weatherData.loc[:, "ID"])-period:len(self.weatherData.loc[:, "ID"])]
        self.n = len(self.x_train)
        meanX = np.mean(self.x_train)
        meanY = np.mean(self.y_train)
        XY = np.sum(self.y_train * self.x_train) - self.n * meanY * meanX
        XX = np.sum(self.x_train * self.x_train) - self.n * meanX * meanX
        self.m = XY / XX
        self.c = meanY - self.m * meanX
        print(self.m, self.c)
        plt.scatter(self.x_train, self.y_train)
        plt.plot(self.x_train, self.m * self.x_train + self.c)
        return self.m, self.c
    def correlationCoefficient(self):
        XY = np.sum(self.x_train*self.y_train)
        XX = np.sum(self.x_train**2)
        YY = np.sum(self.y_train**2)
        coefficent = ((self.n*XY)-(np.sum(self.x_train)*np.sum(self.y_train)))/math.sqrt(((self.n*XX)-XX)*((self.n*YY)-YY))
        return coefficent
    def hourPrediction(self, timeAfterHour):


# Load image and begin simple analysis
skyShot = CloudCover("Clouds1.jpg")
skyShot.linearScan()
skyShot.calcCoverPercentage()
condition = skyShot.determineCondition()
print(condition, skyShot.timestamp)

# OpenCV stuff
dataset = prediction("TestHourlyData.csv")
dataset.linearRegression("ID", "Cloud cover",30)

#Calculating correlation coefficient
r = dataset.correlationCoefficient()
print(r)
plt.show()
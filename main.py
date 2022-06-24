import numpy
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
                self.refLoad[xPixel, yPixel] = (0,0,0)
            else:
                self.totalCloud += 1
                self.refLoad[xPixel, yPixel] = (255,255,255)
    def linearScan(self):
        yTemp = 0
        for i in range(self.yMaximum):
            xTemp = 0
            for j in range(self.xMaximum):
                self.classifyPixel(xTemp, yTemp)
                xTemp += 1
            yTemp += 1
        plt.imshow(self.refImage)
        plt.show()

class CorrelationCoefficient:
    def __init__(self, xValue, yValue):
        self.X = xValue
        self.Y = yValue
        self.coefficient = 0
        self.sigmax, self.sigmay, self.sigmaxy, self.sigmaxSq, self.sigmaySq = 0, 0, 0, 0, 0
        self.count = 0
    def calcSigmas(self, rangeLO, rangeHI):
        for i in range(rangeLO, rangeHI):
            if not math.isnan(self.X[i]) and not math.isnan(self.Y[i]):
                self.count += 1
                self.sigmaxy += self.X[i] * self.Y[i]
                self.sigmaxSq += self.X[i] ** 2
                self.sigmaySq += self.Y[i] ** 2
                self.sigmax += self.X[i]
                self.sigmay += self.Y[i]
    def calcCoefficient(self):
        self.coefficient = ((self.count*self.sigmaxy)-(self.sigmax*self.sigmay))/(math.sqrt(((self.count*self.sigmaxSq)-self.sigmaxSq)*((self.count * self.sigmaySq)-self.sigmaySq)))
        return self.coefficient

# Load image and begin simple analysis
skyShot = CloudCover("Clouds1.jpg")
skyShot.linearScan()
skyShot.calcCoverPercentage()
condition = skyShot.determineCondition()
print(condition, skyShot.timestamp)

# OpenCV stuff
temperature = pd.read_csv("WeatherData.csv")
maxTemperature = temperature.loc[:,"tmax"]
minTemperature = temperature.loc[:, "tmin"]
plt.scatter(maxTemperature, minTemperature)
plt.xlabel("Temperature")
plt.ylabel("Sun")

#Calculating correlation coefficient
temp = CorrelationCoefficient(maxTemperature, minTemperature)
temp.calcSigmas(0,len(maxTemperature))
r = temp.calcCoefficient()
print(r)
plt.show()
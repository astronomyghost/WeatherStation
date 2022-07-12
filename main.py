import numpy as np
from PIL import Image
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import math, requests, json, time
from csv import writer
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
@app.route('/')
def homePage():
    return render_template('ForecastSite.html')

#Test site for weather forecasting

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
        return self.m, self.c
    def correlationCoefficient(self):
        XY = np.sum(self.x_train*self.y_train)
        XX = np.sum(self.x_train**2)
        YY = np.sum(self.y_train**2)
        coefficent = ((self.n*XY)-(np.sum(self.x_train)*np.sum(self.y_train)))/math.sqrt(((self.n*XX)-XX)*((self.n*YY)-YY))
        return coefficent
    def hourPrediction(self, dataset, timeAfterHour, lastID, field):
        dataset.linearRegression("ID", field, 60)
        predictedTemp = self.m * (lastID+timeAfterHour) + self.c
        print("Predicted temperature after "+str(timeAfterHour)+" minutes is "+str(predictedTemp)+" degrees celsius")
        return predictedTemp

# Load image and begin simple analysis
skyShot = CloudCover("Clouds1.jpg")
skyShot.linearScan()
skyShot.calcCoverPercentage()
condition = skyShot.determineCondition()
print(condition, skyShot.timestamp)
pTempList, humidityList, countList = [], [], []
count = 0

# OpenCV stuff
if __name__ == "__main__":
    count += 1
    dataset = prediction("TestHourlyData.csv")
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather?"
    CITY = "London"
    API_KEY = "10bc2d9b9c3edc8216ea0c7e49460849"

    URL = BASE_URL + "q=" + CITY + "&appid=" + API_KEY
    response = requests.get(URL)
    print(URL)
    if response.status_code == 200:
        data = response.json()
        main = data['main']
        temperature = main['temp']-273
        humidity = main['humidity']
        weatherData = pd.read_csv("TestHourlyData.csv")
        n = len(weatherData.loc[: "ID"])
        for i in range(60):
            pTempList.append(dataset.hourPrediction(dataset, i, n, "Temperature"))
            humidityList.append(dataset.hourPrediction(dataset, i, n, "Humidity"))
            countList.append(count+i)
        with open("TestHourlyData.csv", 'a', newline='') as file:
            csvWriter =  writer(file)
            csvWriter.writerow([n+1, temperature, humidity, 0])
        plt.subplot(1,2,1)
        plt.scatter(countList, pTempList, color='black')
        plt.subplot(1,2,2)
        plt.scatter(countList, humidityList, color='blue')
        plt.savefig('Plots.png')
        file.close()
    app.run(debug=False)
    time.sleep(60)

data = response.json()
main = data['main']
temperature = main['temp']
print(temperature-273)

#Calculating correlation coefficient
r = dataset.correlationCoefficient()
print(r)
plt.show()

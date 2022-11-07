from PIL import Image
import datetime
from enum import Enum

class Conditions(Enum):
    overcast = "Overcast"
    mostlyCloudy = "Mostly cloudy"
    slightlyCloudy = "Slightly cloudy"
    clear = "clear"

class CloudCover:
    def __init__(self, fileName):
        # Converts the image into an array for easier analysis
        self.refImage = Image.open(fileName)
        self.refLoad = self.refImage.load()
        self.totalClear, self.totalCloud, self.coverPercentage = 0,0,0
        self.xMaximum, self.yMaximum = self.refImage.size
        self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    def calcCoverPercentage(self, fileName):
        self.coverPercentage = (self.totalCloud/(self.totalClear+self.totalCloud))*100
        self.refImage.save(fileName+'.png')
        return self.coverPercentage
    def determineCondition(self):
        if self.coverPercentage > 90:
            return Conditions.overcast
        elif self.coverPercentage < 90 and self.coverPercentage > 60:
            return Conditions.mostlyCloudy
        elif self.coverPercentage < 60 and self.coverPercentage > 30:
            return Conditions.slightlyCloudy
        else:
            return Conditions.clear
    def classifyPixel(self, xPixel, yPixel):
        # Determines whether the pixel is cloudy (grey or white) or sky (blue)
        r,g,b = self.refLoad[xPixel,yPixel]
        totalPixelValue = r+g+b
        if (r,g,b) != (0,0,0):
            # Percentage blue constant is defined as 0.45
            if (b/totalPixelValue) > 0.45:
                self.totalClear += 1
                self.refLoad[xPixel, yPixel] = (0,0,0)
            else:
                self.totalCloud += 1
                self.refLoad[xPixel, yPixel] = (255,255,255)
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
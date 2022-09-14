import math
class location:
    def __init__(self,name, latitude, longitude, data):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.data = data
    def calculateMeanOfData(self):
        total = 0
        for i in range(len(self.data)):
            total += self.data[i]
        self.mean = total/len(self.data)
    def calculateDistance(self, secondLocation):
        deltaLatitude = self.latitude - secondLocation.latitude
        deltaLongitude = self.longitude - secondLocation.longitude
        scalarDistance = math.sqrt(deltaLatitude**2+deltaLongitude**2)
    def checkCorrelation(self, secondLocation):
        print(self.mean)
import Utility.General as g
from flask import *

# Fetches all location IDs and their respective names from the Locations table
def getLocationIDandLocationName(conn):
    locationCursor = conn.cursor()
    locationCursor.execute("SELECT LocationID, LocationName ID FROM Locations")
    locationList = locationCursor.fetchall()
    cleanLocationIDList = g.sqliteTupleToList(locationList, 0)
    cleanLocationNameList = g.sqliteTupleToList(locationList, 1)
    return cleanLocationIDList, cleanLocationNameList

# Fetches all location information by their name
def getLocationInfobyLocationName(conn, locationName):
    locationCursor = conn.cursor()
    locationCursor.execute("SELECT LocationID, Latitude, Longitude FROM Locations WHERE LocationName = ?", (locationName,))
    locationInfo = locationCursor.fetchall()
    locationID, locationLatitude, locationLongitude = g.sqliteTupleToList(locationInfo, 0)\
        ,g.sqliteTupleToList(locationInfo, 1),g.sqliteTupleToList(locationInfo, 2)
    return locationID, locationLatitude, locationLongitude

# Gets the total number of samples for each location in a list of location IDs
def getSampleCountByLocation(conn, locationIDList):
    sampleCursor = conn.cursor()
    sampleCountList = []
    for i in range(len(locationIDList)):
        sampleCursor.execute("SELECT COUNT(*) FROM Samples WHERE LocationID=?",(locationIDList[i],))
        sampleCount = sampleCursor.fetchall()
        sampleCountList.append(sampleCount[0][0])
    return sampleCountList

# Gets the sample info for all samples in the table
def getSampleInfo(conn):
    sampleCursor = conn.cursor()
    sampleCursor.execute("SELECT TypeID, TypeName FROM SampleType")
    availableSampleTypes = sampleCursor.fetchall()
    availableSampleTypeIds, availableSampleTypeNames = g.sqliteTupleToList(availableSampleTypes, 0)\
        , g.sqliteTupleToList(availableSampleTypes, 1)
    return availableSampleTypeIds, availableSampleTypeNames

def createDictionaryOfData(availableSampleTypeNames, data, time):
    sensorDict = {}
    for i in range(len(availableSampleTypeNames)):
        sensorDict.update({availableSampleTypeNames[i]: {"data": data[i], "time": time[i]}})
    return sensorDict

def createJsonForDailyAndHourlyPage(typeNames):
    locationName = request.args.get('locationName')
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return jsonPost
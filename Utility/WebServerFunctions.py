import Utility.General as g
import datetime, random

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


# Creates a dictionary of the data to be used in json
def createDictionaryOfData(availableSampleTypeNames, data, time):
    sensorDict = {}
    for i in range(len(availableSampleTypeNames)):
        sensorDict.update({availableSampleTypeNames[i]: {"data": data[i], "time": time[i]}})
    return sensorDict

#
def createJsonForPageLoading(typeNames, request):
    locationName = request.args.get('locationName')
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return jsonPost

def getLinkedAccountIDByName(conn, username):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT LinkedAccountID FROM RegisteredDevices WHERE Name=?", (username,))
    linkedID = g.sqliteTupleToList(deviceCursor.fetchall(), 0)
    return linkedID

def getNameAndPasswordByLinkedID(conn, linkedID):
    deviceCursor = conn.cursor()
    linkedID = linkedID[0]
    deviceCursor.execute("SELECT Name,Password FROM RegisteredDevices WHERE DeviceID=?", (linkedID,))
    stationDetails = deviceCursor.fetchall()
    stationName, stationAPI = g.sqliteTupleToList(stationDetails, 0)[0], g.sqliteTupleToList(stationDetails, 1)[0]
    return stationName, stationAPI

def makeUserDetailsString(userDetails, stationName, stationAPI):
    userDetails = userDetails + ',' + stationName + ',' + stationAPI
    return userDetails

def getDeviceIDByNameAndPassword(conn, name, password):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=? AND Password=?", (name, password))
    deviceID = deviceCursor.fetchall()
    deviceID = g.sqliteTupleToList(deviceID, 0)
    return deviceID[0]

def getDeviceIDByNameOnly(conn, name):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=?", (name,))
    deviceID = deviceCursor.fetchall()
    deviceID = g.sqliteTupleToList(deviceID, 0)
    return deviceID[0]

def getSampleCountByDeviceID(conn, deviceID):
    sampleCursor = conn.cursor()
    sampleCursor.execute("SELECT COUNT(*) FROM Samples WHERE DeviceID=?", (deviceID,))
    imageCount = sampleCursor.fetchall()
    imageCount = g.sqliteTupleToList(imageCount, 0)
    return imageCount[0]

def getNameAndPassword(request):
    username = request.form['username']
    password = request.form['password']
    return username, password

def addNewDevice(conn, name, password, type, locationID):
    deviceCursor = conn.cursor()
    deviceCursor.execute("INSERT INTO RegisteredDevices (Name, Password, Type, LocationID) VALUES (?, ?, ?, ?)",
                         (name, password, type, locationID))
    conn.commit()

def addNewLocation(conn, name, latitude, longitude):
    locationCursor = conn.cursor()
    locationCursor.execute("INSERT INTO Locations (LocationName, Latitude, Longitude) VALUES (?,?,?)",
                (name.upper(), latitude, longitude,))
    conn.commit()

def longitudeAndLatitudeValidation(conn, name, latitude, longitude):
    if (latitude < 90 and latitude > -90) and (longitude < 180 and longitude > -180):
        addNewLocation(conn, name, latitude, longitude)
        return "New location " + name + " added to database"
    else:
        return "Latitude or longitude is not in range of values"

def getDeviceCountByDeviceName(conn, name):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT COUNT(*) FROM RegisteredDevices WHERE Name=?", (name,))
    deviceCount = deviceCursor.fetchall()
    deviceCount = g.sqliteTupleToList(deviceCount, 0)
    return deviceCount[0]


def generateStationAPIKey(conn, locationName):
    isUnique = False
    while isUnique == False:
        currentDate = datetime.datetime.now().strftime("%d%m%Y")
        stationName = currentDate + locationName + str(random.randint(0, 9999))
        deviceCount = getDeviceCountByDeviceName(conn, stationName)
        if (deviceCount == 0):
            isUnique = True
    return stationName
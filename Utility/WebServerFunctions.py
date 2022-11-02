import json

import Utility.General as g
import Utility.Prediction as p
import Utility.ImageAnalysis as ia
import datetime, random, os, base64, io
from PIL import Image
import smtplib

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
    if len(locationID) > 0:
        return locationID, locationLatitude, locationLongitude
    else:
        return None, None, None

# Returns the total number of samples for each location in a list of location IDs
def getSampleCountByLocation(conn, locationIDList):
    sampleCursor = conn.cursor()
    sampleCountList = []
    for i in range(len(locationIDList)):
        sampleCursor.execute("SELECT COUNT(*) FROM Samples WHERE LocationID=?",(locationIDList[i],))
        sampleCount = sampleCursor.fetchall()
        sampleCountList.append(sampleCount[0][0])
    return sampleCountList

# Returns the sample info for all samples in the table
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

# Creates a json dictionary of the location name and sample types to be used on the webpage
def createJsonForPageLoading(typeNames, request):
    locationName = request.args.get('locationName')
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return jsonPost

# Returns the linked account ID by the username
def getLinkedAccountIDByName(conn, username):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT LinkedAccountID FROM RegisteredDevices WHERE Name=?", (username,))
    linkedID = g.sqliteTupleToList(deviceCursor.fetchall(), 0)
    return linkedID

# Returns the name and password of the linked account to the station
def getNameAndPasswordByLinkedID(conn, linkedID):
    deviceCursor = conn.cursor()
    linkedID = linkedID[0]
    deviceCursor.execute("SELECT Name,Password FROM RegisteredDevices WHERE DeviceID=?", (linkedID,))
    stationDetails = deviceCursor.fetchall()
    if len(stationDetails) > 0:
        stationName, stationAPI = g.sqliteTupleToList(stationDetails, 0)[0], g.sqliteTupleToList(stationDetails, 1)[0]
        return stationName, stationAPI
    else:
        return 'None', 'None'

# Creates a string of the user's details for use in the user page
def makeUserDetailsString(userDetails, stationName, stationAPI):
    userDetails = userDetails + ',' + stationName + ',' + stationAPI
    return userDetails

# Returns the deviceID from the sqlite database by finding the matching username and password
def getDeviceIDByNameAndPassword(conn, name, password):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=? AND Password=?", (name, password))
    deviceID = deviceCursor.fetchall()
    deviceID = g.sqliteTupleToList(deviceID, 0)
    if len(deviceID) > 0:
        return deviceID[0]
    else:
        return None

# Returns the number of samples/images contributed by a user
def getSampleCountByDeviceID(conn, deviceID):
    sampleCursor = conn.cursor()
    sampleCursor.execute("SELECT COUNT(*) FROM Samples WHERE DeviceID=?", (deviceID,))
    imageCount = sampleCursor.fetchall()
    imageCount = g.sqliteTupleToList(imageCount, 0)
    return imageCount[0]

# Returns the username and password from the html form
def getNameAndPassword(request):
    username = request.form['username']
    password = request.form['password']
    return username, password

# Returns the username and password from the html form
def getNamePasswordAndEmail(request):
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']
    return username, password, email

# Adds a new device/user to the RegisteredDevices table
def addNewDevice(conn, name, password, type, locationID, email):
    deviceCursor = conn.cursor()
    deviceCursor.execute("INSERT INTO RegisteredDevices (Name, Password, Type, LocationID, Verified, Email) VALUES (?, ?, ?, ?, 0, ?)",
                         (name, password, type, locationID, email))
    conn.commit()

# Checks that no duplicate locations are uploaded
def checkIfLocationExists(conn, name):
    locationCursor = conn.cursor()
    locationCursor.execute("SELECT COUNT(*) FROM Locations WHERE LocationName = ?"(name,))
    locationCount = locationCursor.fetchall()
    if locationCount[0][0] == 0:
        return True
    else:
        return False

# Adds a new location by name, latitude and longitude to the locations table
def addNewLocation(conn, name, latitude, longitude):
    locationCursor = conn.cursor()
    locationCursor.execute("INSERT INTO Locations (LocationName, Latitude, Longitude) VALUES (?,?,?)",
                (name.upper(), latitude, longitude,))
    conn.commit()

# Checks that the longitude and latitude values are valid by checking that they are within the correct values
def longitudeAndLatitudeValidation(conn, name, latitude, longitude):
    if (latitude < 90 and latitude > -90) and (longitude < 180 and longitude > -180) and checkIfLocationExists(conn, name):
        addNewLocation(conn, name, latitude, longitude)
        return "New location " + name + " added to database"
    else:
        return "Latitude or longitude is not in range of values"

# Checks that no devices exist with the same username
def getDeviceCountByDeviceName(conn, name):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT COUNT(*) FROM RegisteredDevices WHERE Name=?", (name,))
    deviceCount = deviceCursor.fetchall()
    return deviceCount[0][0]

# Checks that no devices exist with the same username
def getDeviceCountByDeviceNameAndEmail(conn, name, email):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT COUNT(*) FROM RegisteredDevices WHERE Name=? OR Email=?", (name,email,))
    deviceCount = deviceCursor.fetchall()
    return deviceCount[0][0]

# Produces a station API key (hash code of the station name)
def generateStationAPIKey(conn, locationName):
    isUnique = False
    while isUnique == False:
        currentDate = datetime.datetime.now().strftime("%d%m%Y")
        stationName = currentDate + locationName + str(random.randint(0, 9999))
        deviceCount = getDeviceCountByDeviceName(conn, stationName)
        if (deviceCount == 0):
            isUnique = True
    return stationName

# Returns the ID of the station by checking for the APIKey
def getIDOfStation(conn, password):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID FROM RegisteredDevices WHERE Password=? AND Type='Station'", (password,))
    stationID = deviceCursor.fetchall()
    stationID = g.sqliteTupleToList(stationID, 0)[0]
    return stationID

# Updates the linked account ID of the user so that they have an associated weather station to them
def linkIDWithStation(conn, stationID, name):
    deviceCursor = conn.cursor()
    deviceCursor.execute("UPDATE RegisteredDevices SET LinkedAccountID=? WHERE Name=?", (stationID, name,))
    conn.commit()

# Returns the location and device ID where the device name = name
def getLocationAndDeviceIDByName(conn, name):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID, LocationID FROM RegisteredDevices WHERE Name=?", (name,))
    userInfo = deviceCursor.fetchall()
    return userInfo

# Adds a sample to the sample table
def addSamples(conn, deviceID, typeID, locationID, timestamp, value):
    sampleCursor = conn.cursor()
    sampleCursor.execute("INSERT INTO Samples(DeviceID, TypeID, LocationID, Timestamp, Value) VALUES(?,?,?,?,?)",
                (deviceID, typeID, locationID, timestamp, value))
    conn.commit()

# A sequence of commands performed to return the percentage cloud cover in the image
def imageAnalysisSequence(savePath, fetchTime):
    skyShot = ia.CloudCover(savePath)
    skyShot.linearScan()
    percentageCover = skyShot.calcCoverPercentage()
    condition = skyShot.determineCondition()
    if fetchTime:
        timestamp = skyShot.timestamp
        return percentageCover, condition, timestamp
    else:
        return percentageCover, condition

# Returns the deviceID by checking against the name and type of the device
def getDeviceIDByNameAndType(conn, name, type):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=? AND Type=?", (name, type,))
    deviceID = deviceCursor.fetchall()[0][0]
    return deviceID

# Sets a user's home location for ease of image submission and extreme weather reports
def setHomeLocationOfDevice(conn, locationID, deviceID):
    deviceCursor = conn.cursor()
    deviceCursor.execute("UPDATE RegisteredDevices SET LocationID=? WHERE DeviceID=? ", (locationID, deviceID,))
    conn.commit()

# Decodes the image from base64 so that it is readable by the pillow library for measuring cloud cover
def saveAndLoadImg(imgRaw, timestamp):
    imgReadable = base64.b64decode(imgRaw.encode('utf-8'))
    img = Image.open(io.BytesIO(imgReadable))
    datetimeTimestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d, %H:%M:%S')
    savePath = os.path.join("Images", datetimeTimestamp.strftime("%Y-%m-%d-%H%M%S") + ".jpg")
    img.save(savePath)
    return savePath

# Returns the type ID from the type name
def getTypeIDFromListOfTypeNames(conn, sampleTypes, i):
    sampleCursor = conn.cursor()
    sampleCursor.execute("SELECT TypeID FROM SampleType WHERE TypeName=?", (sampleTypes[i].upper(),))
    typeID = sampleCursor.fetchall()
    return typeID[0][0]

# Adds a new type of sample to the SampleType database
def addNewSampleType(conn, name, units):
    typeCursor = conn.cursor()
    typeCursor.execute("INSERT INTO SampleType(TypeName, Units) VALUES(?,?)", (name.upper(), units))
    conn.commit()

# returns the device and location ID of a device from the name, password and type of the device
def getDeviceIDAndLocationIDByNameTypeAndKey(conn, name, type, key):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT DeviceID, LocationID FROM RegisteredDevices WHERE Name=? AND Password=? AND Type=?",
                (name, key,type,))
    IDs = deviceCursor.fetchall()
    deviceID, locationID = IDs[0][0], IDs[0][1]
    return deviceID, locationID

def getLocationsThatStartWith(conn, name):
    locationCursor = conn.cursor()
    locationCursor.execute("SELECT LocationName, Latitude, Longitude FROM Locations WHERE LocationName LIKE ?",(name+'%',))
    locationInfo = locationCursor.fetchall()
    locationNames, latitudes, longitudes = g.sqliteTupleToList(locationInfo, 0), g.sqliteTupleToList(locationInfo, 1), g.sqliteTupleToList(locationInfo, 2)
    return locationNames, latitudes, longitudes

def sendEmail(senderAddress, senderPassword, receiverAddress, username):
    emailSubject = 'Confirm email'
    emailBody = 'Thank you for signing up! Please go to this address here to confirm your email : http://127.0.0.1:5000/verifyAddress?username='+username
    emailText = "From: "+senderAddress+"\n To: "+receiverAddress+"\n Subject: "+emailSubject+"\n\n "+emailBody
    smtpServer = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtpServer.ehlo()
    smtpServer.login(senderAddress, senderPassword)
    smtpServer.sendmail(senderAddress, receiverAddress, emailText)
    smtpServer.close()

def updateVerification(conn, username):
    deviceCursor = conn.cursor()
    deviceCursor.execute("UPDATE RegisteredDevices SET Verified=1 WHERE Name=?", (username,))
    conn.commit()

def checkVerification(conn, username):
    deviceCursor = conn.cursor()
    deviceCursor.execute("SELECT Verified FROM RegisteredDevices WHERE Name=?",(username,))
    verificationNum = deviceCursor.fetchall()
    if verificationNum[0][0] == 1:
        return True
    else:
        return False


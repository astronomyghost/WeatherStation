from Prediction import *
import Utility.WebServerFunctions as wf
from flask import *
import os, base64, io
import hashlib, random

conn = sql.connect('Users.db', check_same_thread=False)
cur = conn.cursor()
app = Flask(__name__)

def imageAnalysisSequence(savePath, fetchTime):
    skyShot = CloudCover(savePath)
    skyShot.linearScan()
    percentageCover = skyShot.calcCoverPercentage()
    condition = skyShot.determineCondition()
    if fetchTime:
        timestamp = skyShot.timestamp
        return percentageCover, condition, timestamp
    else:
        return percentageCover, condition

# Setting up the home page on the web server
@app.route('/')
def home():
    locationIDList, locationNameList = wf.getLocationIDandLocationName(conn)
    sampleCountList = wf.getSampleCountByLocation(conn, locationIDList)
    jsonPost = {'locationNames' : tuple(locationNameList), 'sampleCounts' : tuple(sampleCountList)}
    return render_template('ForecastSite.html', post=jsonPost)

@app.route('/home?locationName=<locationName>')
def locationPage(locationName):
    locationInfo = wf.getLocationInfobyLocationName(conn, locationName)
    stormWarning = checkStormWarning(cur, locationInfo[0][0], 3600)
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames), "stormWarning": stormWarning}
    return render_template('LocationTemplate.html', post=jsonPost)

@app.route('/fetchData')
def locationForecast():
    locationName = request.args.get('locationName')
    locationInfo = wf.getLocationInfobyLocationName(conn, locationName)
    availableSampleTypeIds, availableSampleTypeNames = wf.getSampleInfo(conn)
    data, time, latestValues, trendInfoList = minuteCast(locationID=locationInfo[0][0], cur=cur, sampleTypes=availableSampleTypeIds)
    sensorDict = {}
    for i in range(len(availableSampleTypeNames)):
        sensorDict.update({availableSampleTypeNames[i]: {"data": data[i], "latestValue": latestValues[i],
                                                         "trend": trendInfoList[i], "time": time[i]}})
    jsonData = {"data": sensorDict,
                "location": {'locationName': locationName, 'latitude': locationInfo[1][0], 'longitude': locationInfo[1][0]}}
    return jsonData

@app.route('/fetchTimeline')
def locationTimeline():
    locationName = request.args.get('locationName')
    locationInfo = wf.getLocationInfobyLocationName(conn, locationName)
    dataList, timeList = [], []
    availableSampleTypeIds, availableSampleTypeNames = wf.getSampleInfo(conn)
    for i in range(len(availableSampleTypeIds)):
        data, time = grabTimeline(locationInfo[0][0], i+1, cur)
        dataList.append(data)
        timeList.append(time)
    sensorDict = wf.createDictionaryOfData(availableSampleTypeNames, dataList, timeList)
    jsonData = {"data": sensorDict}
    return jsonData

@app.route('/timeline', methods=['POST', 'GET'])
def timelinePage():
    jsonPost = wf.createJsonForPageLoading()
    return render_template('LocationTimeline.html', post=jsonPost)

@app.route('/fetchMachineLearningPredictions')
def machineLearningPredictions():
    locationName = request.args.get('locationName')
    period = int(request.args.get('period'))
    periodType = request.args.get('periodType')
    locationInfo = wf.getLocationInfobyLocationName(conn, locationName)
    dataList, timeList = [], []
    availableSampleTypeIds, availableSampleTypeNames = wf.getSampleInfo(conn)
    for i in range(len(availableSampleTypeIds)):
        data, time = machineLearning(locationInfo[0][0], i+1, cur, period, periodType)
        dataList.append(data)
        timeList.append(time)
    sensorDict = wf.createDictionaryOfData(availableSampleTypeNames, dataList, timeList)
    jsonData = {"data": sensorDict}
    return jsonData

@app.route('/hourlyPrediction', methods=['POST', 'GET'])
def hourlyPage():
    jsonPost = wf.createJsonForPageLoading(typeNames, request)
    return render_template('LocationHourly.html', post=jsonPost)

@app.route('/dailyPrediction', methods=['POST', 'GET'])
def dailyPage():
    jsonPost = wf.createJsonForPageLoading(typeNames, request)
    return render_template('LocationDaily.html', post=jsonPost)

@app.route('/UserPage?userDetails=<userDetails>')
def userPage(userDetails):
    username = userDetails.split(",")[0]
    linkedID = wf.getLinkedAccountIDByName(conn, username)
    if(len(linkedID) > 0):
        stationName, stationAPI = wf.getNameAndPasswordByLinkedID(conn, linkedID)
        userDetails = wf.makeUserDetailsString(userDetails, stationName, stationAPI)
    else:
        userDetails = wf.makeUserDetailsString(userDetails, 'None', 'None')
    return render_template('UserPage.html', info=list(userDetails.split(",")))

@app.route('/LoginPage')
def loginPage():
    return render_template('Login.html')

@app.route('/LoginReceiver', methods=['POST', 'GET'])
def loginRequest():
    if request.method == 'POST':
        username, password = wf.getNameAndPassword(request)
        hashPassword = hashlib.sha256(password.encode()).hexdigest()
        userID = wf.getDeviceIDByNameAndPassword(conn, username, hashPassword)
        if userID == None or username == '' or password == '':
            return redirect(url_for('loginPage'))
        else:
            imageCount = wf.getSampleCountByDeviceID(conn, userID)
            if imageCount > 0:
                return redirect(url_for('userPage', userDetails=username+','+str(imageCount)))
            else:
                return redirect(url_for('userPage', userDetails=username+','+str(imageCount)))

@app.route('/RegisterReceiver', methods=['POST', 'GET'])
def registerRequest():
    if request.method == 'POST':
        username, password = wf.getNameAndPassword(request)
        checkPassword = request.form['checkPassword']
        deviceID = wf.getDeviceIDByNameOnly(conn, username)
        if password == checkPassword and deviceID == None and username != '' and password != '':
            hashPassword = hashlib.sha256(password.encode()).hexdigest()
            wf.addNewDevice(conn, username, hashPassword, 'User', None)
            return redirect(url_for('userPage', userDetails=username+','+str(0)))
        else:
            return redirect(url_for('loginPage'))

@app.route('/LocationReceiver', methods=['POST', 'GET'])
def getSelectedLocation():
    if request.method == 'POST':
        locationName = request.form.get('locationSelect')
        if locationName == "none":
            return redirect(url_for('home'))
        else:
            return redirect(url_for('locationPage', locationName=locationName))

@app.route('/addLocation', methods=['POST', 'GET'])
def addNewLocation():
    if request.method == 'POST':
        locationName = request.form.get('locationName')
        try:
            latitude, longitude = float(request.form.get('latitude')), float(request.form.get('longitude'))
            wf.longitudeAndLatitudeValidation(conn, locationName, latitude, longitude)
        except:
            return "Latitude or longitude is not a valid data type (floats or integers only)"

@app.route('/addStation', methods=['POST', 'GET'])
def addNewStation():
    userDetails = request.args.get('userDetails').split(',')
    if request.method == 'POST':
        locationName = request.json['location'].upper()
        locationID = wf.getLocationInfobyLocationName(conn, locationName)[0][0]
        if(locationID != None):
            stationName = wf.generateStationAPIKey(conn, locationName)
            hashPassword = hashlib.sha256(stationName.encode()).hexdigest()
            wf.addNewDevice(conn, stationName, hashPassword, 'Station', locationID)
            cur.execute("SELECT DeviceID FROM RegisteredDevices WHERE Password=? AND Type='Station'",(hashPassword,))
            stationLinkID = cur.fetchall()
            stationLinkID = stationLinkID[0][0]
            print(userDetails[0])
            cur.execute("UPDATE RegisteredDevices SET LinkedAccountID=? WHERE Name=?",(stationLinkID, userDetails[0],))
            conn.commit()
        else:
            return "Location not found"
    return {"stationName": stationName, "stationPass": hashPassword}

@app.route('/reportWarning', methods=['GET', 'POST'])
def reportWarning():
    reportTime = datetime.datetime.now()
    reportTimeStr = reportTime.strftime('%Y-%m-%d, %H:%M:%S')
    userDetails = request.args.get('userDetails').split(',')
    if request.method == 'POST':
        cur.execute("SELECT DeviceID, LocationID FROM RegisteredDevices WHERE Name=?",(userDetails[0],))
        userInfo = cur.fetchall()
        if userInfo[0][1] != None:
            cur.execute("INSERT INTO Samples(DeviceID, TypeID, LocationID, Timestamp, Value) VALUES(?,5,?,?,?)",
                        (userInfo[0][0], userInfo[0][1], reportTimeStr, "True"))
            conn.commit()
            return {"message": "Report submitted"}
        else:
            return {"message": "No home location set"}

@app.route('/imageReceiver', methods=['POST', 'GET'])
def receiveImage():
    if request.method == 'POST':
        locationName = request.form['location'].upper()
        username = request.form['hiddenUsername']
        if locationName == "":
            cur.execute("SELECT LocationID FROM RegisteredDevices WHERE Name = ?",(username,))
            locationID = cur.fetchall()
            if len(locationID) > 0:
                locationID = locationID[0][0]
            else:
                return "Not a valid location name"
        else:
            cur.execute("SELECT LocationID FROM Locations WHERE LocationName = ?",(locationName,))
            locationID = cur.fetchall()
            if len(locationID) > 0:
                locationID = locationID[0][0]
            else:
                return "Not a valid location name"
        file = request.files['imageUpload']
        setHome = False
        if request.form.get('setHome'):
            setHome = True
        savePath = os.path.join("Images", datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")+".jpg")
        file.save(savePath)
        try:
            #image analysis algorithm
            percentageCover, condition, timestamp = imageAnalysisSequence(savePath, True)
            cur.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=? AND Type='User'",(username,))
            userID = cur.fetchall()[0][0]
            cur.execute("INSERT INTO Samples (DeviceID, TypeID, LocationID, Timestamp, Value) VALUES (?,?,?,?,?)",(userID, 4, locationID, timestamp, percentageCover))
            if setHome:
                cur.execute("UPDATE RegisteredDevices SET LocationID=? WHERE DeviceID=? ",(locationID, userID,))
            conn.commit()
        except:
            return "Error, invalid file type"
        return "File upload finished, info : "+str(percentageCover)+" "+condition

@app.route('/DataReceiver', methods=['POST', 'GET'])
def appendData():
    if request.method == 'POST':
        query = request.json
        login = query['login']
        name, key = login['stationName'], login['stationKey']
        cur.execute("SELECT DeviceID, LocationID FROM RegisteredDevices WHERE Name=? AND Password=? AND Type='Station'",
                    (name, key,))
        IDs = cur.fetchall()
        if len(IDs) > 0:
            stationID = IDs[0][0]
            locationID = IDs[0][1]
            if query['command'] == 'send':
                data = query['data']
                timestamp = query['timestamp']
                sampleTypes = query['types']
                for i in range(len(sampleTypes)):
                    if(sampleTypes[i] == 'media'):
                        imgRawB64 = data['media']
                        imgReadable = base64.b64decode(imgRawB64.encode('utf-8'))
                        img = Image.open(io.BytesIO(imgReadable))
                        datetimeTimestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d, %H:%M:%S')
                        savePath = os.path.join("Images", datetimeTimestamp.strftime("%Y-%m-%d-%H%M%S") + ".jpg")
                        img.save(savePath)
                        percentageCover, condition = imageAnalysisSequence(savePath, False)
                        cur.execute(
                            "INSERT INTO Samples (DeviceID, TypeID, LocationID, Timestamp, Value) VALUES (?,?,?,?,?)",
                            (stationID, 4, locationID, timestamp, percentageCover))
                        conn.commit()
                    cur.execute("SELECT TypeID FROM SampleType WHERE TypeName=?",(sampleTypes[i].upper(),))
                    typeID = cur.fetchall()
                    if (len(typeID) > 0):
                        typeID = typeID[0][0]
                        cur.execute(
                            "INSERT INTO Samples (DeviceID, TypeID, LocationID, Timestamp, Value) VALUES (?,?,?,?,?)",
                            (stationID, typeID, locationID, timestamp, data[sampleTypes[i]]))
                        conn.commit()
                return data
            elif query['command'] == 'addType':
                typeName, typeUnits = query['name'], query['units']
                cur.execute("INSERT INTO SampleType(TypeName, Units) VALUES(?,?)",(typeName.upper(), typeUnits))
                conn.commit()
                return "Successfully added data type "+typeName+" of units "+typeUnits
        else:
            return "Station not registered"

'''
def geoFencingTest():
    cur.execute("SELECT * FROM Locations")
    stuff = cur.fetchall()
    Test1 = location(stuff[0][1], stuff[0][2], stuff[0][3], [0,1])
    Test2 = location(stuff[1][1], stuff[1][2], stuff[1][3], [1,2])
    print(Test1.calculateDistance(Test2))
'''

if __name__ == "__main__":
    #geoFencingTest()
    cur.execute("SELECT TypeName FROM SampleType")
    typeNames = cur.fetchall()
    typeNames = wf.g.sqliteTupleToList(typeNames, 0)
    app.run(host="0.0.0.0", debug=False)

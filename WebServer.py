import DiscordBot
from Prediction import *
from GeoFencing import *
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

def tupleToList(list, j):
    rfList = []  # Queries from the sql database are received as tuples so it must be refined to an ordinary list
    for i in range(len(list)):
        rfList.append(list[i][j])
    return rfList

# Setting up the home page on the web server
@app.route('/')
def home():
    cur.execute("SELECT LocationID, LocationName ID FROM Locations")
    locationList = cur.fetchall()
    cleanLocationIDList = tupleToList(locationList, 0)
    cleanLocationNameList = tupleToList(locationList, 1)
    sampleCountList = []
    for i in range(len(cleanLocationIDList)):
        cur.execute("SELECT COUNT(*) FROM Samples WHERE LocationID=?",(cleanLocationIDList[i],))
        sampleCount = cur.fetchall()
        sampleCountList.append(sampleCount[0][0])
    jsonPost = {'locationNames' : tuple(cleanLocationNameList), 'sampleCounts' : tuple(sampleCountList)}
    return render_template('ForecastSite.html', post=jsonPost)

@app.route('/home?locationName=<locationName>')
def locationPage(locationName):
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return render_template('LocationTemplate.html', post=jsonPost)

@app.route('/fetchData')
def locationForecast():
    locationName = request.args.get('locationName')
    cur.execute("SELECT LocationID, Latitude, Longitude FROM Locations WHERE LocationName = ?", (locationName,))
    locationDetails = cur.fetchall()
    locationID, latitude, longitude = locationDetails[0][0], locationDetails[0][1], locationDetails[0][2]
    cur.execute("SELECT TypeID, TypeName FROM SampleType")
    availableSampleTypes = cur.fetchall()
    rfAvailableSampleTypeIds = tupleToList(availableSampleTypes, 0)
    rfAvailableSampleTypeNames = tupleToList(availableSampleTypes, 1)
    data, time, latestValues, trendInfoList = minuteCast(locationID=locationID, cur=cur, sampleTypes=rfAvailableSampleTypeIds)
    sensorDict = {}
    print(time)
    for i in range(len(rfAvailableSampleTypeNames)):
        sensorDict.update({rfAvailableSampleTypeNames[i]:{"data": data[i], "latestValue": latestValues[i], "trend": trendInfoList[i], "time": time[i]}})
    jsonData = {"data": sensorDict,
                "location": {'locationName': locationName, 'latitude': latitude, 'longitude': longitude}}
    print(jsonData)
    return jsonData

@app.route('/fetchTimeline')
def locationTimeline():
    locationName = request.args.get('locationName')
    cur.execute("SELECT LocationID FROM Locations WHERE LocationName = ?", (locationName,))
    locationID = cur.fetchall()
    locationID = locationID[0][0]
    dataList, timeList = [], []
    cur.execute("SELECT TypeID, TypeName FROM SampleType")
    availableSampleTypes = cur.fetchall()
    rfAvailableSampleTypeIds = tupleToList(availableSampleTypes, 0)
    rfAvailableSampleTypeNames = tupleToList(availableSampleTypes, 1)
    for i in range(len(rfAvailableSampleTypeIds)):
        data, time = grabTimeline(locationID, i+1, cur)
        dataList.append(data)
        timeList.append(time)
    sensorDict = {}
    for i in range(len(rfAvailableSampleTypeNames)):
        sensorDict.update({rfAvailableSampleTypeNames[i]:{"data": dataList[i], "time": timeList[i]}})
    jsonData = {"data": sensorDict}
    print(jsonData)
    return jsonData

@app.route('/timeline', methods=['POST', 'GET'])
def timelinePage():
    locationName = request.args.get('locationName')
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return render_template('LocationTimeline.html', post=jsonPost)

@app.route('/fetchMachineLearningPredictions')
def machineLearningPredictions():
    locationName = request.args.get('locationName')
    print(locationName)
    period = int(request.args.get('period'))
    periodType = request.args.get('periodType')
    cur.execute("SELECT LocationID FROM Locations WHERE LocationName = ?", (locationName,))
    locationID = cur.fetchall()
    locationID = locationID[0][0]
    dataList, timeList = [], []
    cur.execute("SELECT TypeID, TypeName FROM SampleType")
    availableSampleTypes = cur.fetchall()
    rfAvailableSampleTypeIds = tupleToList(availableSampleTypes, 0)
    rfAvailableSampleTypeNames = tupleToList(availableSampleTypes, 1)
    for i in range(len(rfAvailableSampleTypeIds)):
        data, time = machineLearning(locationID, i+1, cur, period, periodType)
        dataList.append(data)
        timeList.append(time)
    sensorDict = {}
    for i in range(len(rfAvailableSampleTypeNames)):
        sensorDict.update({rfAvailableSampleTypeNames[i]:{"data": dataList[i], "time": timeList[i]}})
    jsonData = {"data": sensorDict}
    return jsonData

@app.route('/hourlyPrediction', methods=['POST', 'GET'])
def hourlyPage():
    locationName = request.args.get('locationName')
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return render_template('LocationHourly.html', post=jsonPost)

@app.route('/dailyPrediction', methods=['POST', 'GET'])
def dailyPage():
    locationName = request.args.get('locationName')
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames)}
    return render_template('LocationDaily.html', post=jsonPost)

@app.route('/UserPage?userDetails=<userDetails>')
def userPage(userDetails):
    username = userDetails.split(",")[0]
    cur.execute("SELECT LinkedAccountID FROM RegisteredDevices WHERE Name=?",(username,))
    linkedID = cur.fetchall()
    if(len(linkedID) > 0):
        linkedID = linkedID[0][0]
        cur.execute("SELECT Name,Password FROM RegisteredDevices WHERE DeviceID=?",(linkedID,))
        stationDetails = cur.fetchall()
        stationName = stationDetails[0][0]
        stationAPI = stationDetails[0][1]
        userDetails = userDetails+','+stationName+','+stationAPI
    else:
        userDetails = userDetails+',None,None'
    return render_template('UserPage.html', info=list(userDetails.split(",")))

@app.route('/LoginPage')
def loginPage():
    return render_template('Login.html')

@app.route('/LoginReceiver', methods=['POST', 'GET'])
def loginRequest():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashPassword = hashlib.sha256(password.encode()).hexdigest()
        cur.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=? AND Password=?", (username, hashPassword))
        userID = cur.fetchall()
        if len(userID) == 0 or username == '' or password == '':
            return redirect(url_for('loginPage'))
        else:
            userID = userID[0][0]
            cur.execute("SELECT SampleID FROM Samples WHERE DeviceID=?", (userID,))
            imageCount = cur.fetchall()
            if len(imageCount) > 0:
                return redirect(url_for('userPage', userDetails=username+','+str(len(imageCount))))
            else:
                return redirect(url_for('userPage', userDetails=username+','+str(len(imageCount))))

@app.route('/RegisterReceiver', methods=['POST', 'GET'])
def registerRequest():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        checkPassword = request.form['checkPassword']
        cur.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=?", (username,))
        if password == checkPassword and len(cur.fetchall()) < 1 and username != '' and password != '':
            hashPassword = hashlib.sha256(password.encode()).hexdigest() # salt hashing d o i t
            cur.execute("INSERT INTO RegisteredDevices (Name, Password, Type) VALUES (?, ?, 'User')", (username, hashPassword))
            conn.commit()
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
            if (latitude < 90 and latitude > -90) and (longitude < 180 and longitude > -180):
                cur.execute("INSERT INTO Locations (LocationName, Latitude, Longitude) VALUES (?,?,?)",
                            (locationName.upper(), latitude, longitude,))
                conn.commit()
                return "New location "+locationName+" added to database"
            else:
                return "Latitude or longitude is not in range of values"
        except:
            return "Latitude or longitude is not a valid data type (floats or integers only)"

@app.route('/addStation', methods=['POST', 'GET'])
def addNewStation():
    userDetails = request.args.get('userDetails').split(',')
    if request.method == 'POST':
        locationName = request.json['location'].upper()
        cur.execute("SELECT LocationID FROM Locations WHERE LocationName = ?",(locationName,))
        locations = cur.fetchall()
        isUnique = False;
        if(len(locations) > 0):
            while isUnique == False:
                currentDate = datetime.datetime.now().strftime("%d%m%Y")
                stationName = currentDate+locationName+str(random.randint(0,1024))
                cur.execute("SELECT * FROM RegisteredDevices WHERE Name=?",(stationName,))
                isDuplicate = cur.fetchall()
                if(len(isDuplicate) <= 0):
                    isUnique = True
            hashPassword = hashlib.sha256(stationName.encode()).hexdigest()
            cur.execute("INSERT INTO RegisteredDevices(LocationID, Type, Name, Password) VALUES(?, 'Station', ?, ?)",
                        (locations[0][0], stationName, hashPassword,))
            conn.commit()
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
            if request.json['command'] == 'send':
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
            elif request.json['command'] == 'addType':
                print("hi")
        else:
            return "Station not registered"

def geoFencingTest():
    cur.execute("SELECT * FROM Locations")
    stuff = cur.fetchall()
    Test1 = location(stuff[0][1], stuff[0][2], stuff[0][3], [0,1])
    Test2 = location(stuff[1][1], stuff[1][2], stuff[1][3], [1,2])
    print(Test1.calculateDistance(Test2))

if __name__ == "__main__":
    geoFencingTest()
    cur.execute("SELECT TypeName FROM SampleType")
    typeNames = cur.fetchall()
    typeNames = tupleToList(typeNames, 0)
    app.run(host="0.0.0.0", debug=False)

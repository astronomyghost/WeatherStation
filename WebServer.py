from Utility.Prediction import *
import Utility.WebServerFunctions as wf
from flask import *
import os, base64, io
import hashlib

conn = sql.connect('Users.db', check_same_thread=False)
cur = conn.cursor()
app = Flask(__name__)

# Route for the home page, displays a map and links to other locations and login/register page
@app.route('/')
def home():
    locationIDList, locationNameList = wf.getLocationIDandLocationName(conn)
    sampleCountList = wf.getSampleCountByLocation(conn, locationIDList)
    jsonPost = {'locationNames' : tuple(locationNameList), 'sampleCounts' : tuple(sampleCountList)}
    return render_template('ForecastSite.html', post=jsonPost) # Renders the webpage using the forecast site

@app.route('/satellitePass')
def satellitePage():
    jsonPost = wf.createJsonForPageLoading(typeNames, request)
    return render_template('LocationSatellitePass.html', post=jsonPost)

@app.route('/checkSatellitePass')
def checkPass():
    locationName = request.args.get('locationName')
    satelliteName = request.args.get('satelliteName')
    satInfo = wf.getSatelliteInfo(satelliteName)
    locInfo = wf.getLocationInfobyLocationName(conn, locationName)
    locInfo = [locInfo[1][0], locInfo[2][0]]
    satPass = wf.checkSatellitePass(locInfo, satInfo[0:1])
    return {"checkpass": satPass, "satelliteInfo": satInfo}

@app.route('/home?locationNames=<locationName>')
def locationList(locationName):
    locationNames = wf.getLocationsThatStartWith(conn, locationName)
    jsonPost = {"locationNames":tuple(locationNames[0]), "latitudes":tuple(locationNames[1]),"longitudes":tuple(locationNames[2])}
    return render_template('LocationFinder.html', post=jsonPost)

@app.route('/home?locationName=<locationName>')
def locationPage(locationName):
    locationInfo = wf.getLocationInfobyLocationName(conn, locationName)
    stormWarning = checkStormWarning(cur, locationInfo[0][0], 3600)
    jsonPost = {"locationName": locationName, "sampleTypes": tuple(typeNames), "stormWarning": stormWarning}
    return render_template('LocationTemplate.html', post=jsonPost)

@app.route('/locationRedirect', methods=['POST', 'GET'])
def locationRedirect():
    locationName = request.form['locationName']
    return redirect(url_for('locationPage', locationName=locationName))

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
                "location": {'locationName': locationName, 'latitude': locationInfo[1][0], 'longitude': locationInfo[2][0]}}
    print(locationInfo)
    return jsonData

@app.route('/fetchTimeline')
def locationTimeline():
    locationName = request.args.get('locationName')
    print(locationName)
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
    jsonPost = wf.createJsonForPageLoading(typeNames, request)
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
        deviceCount = wf.getDeviceCountByDeviceName(conn, username)
        if password == checkPassword and deviceCount == 0 and username != '' and password != '':
            hashPassword = hashlib.sha256(password.encode()).hexdigest()
            wf.addNewDevice(conn, username, hashPassword, 'User', None)
            return redirect(url_for('userPage', userDetails=username+','+str(0)))
        else:
            return redirect(url_for('loginPage'))

@app.route('/LocationReceiver', methods=['POST', 'GET'])
def getSelectedLocation():
    if request.method == 'POST':
        locationName = request.form.get('locationSelect').upper()
        if locationName == "none":
            return redirect(url_for('home'))
        else:
            return redirect(url_for('locationList', locationName=locationName))

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
            stationLinkID = wf.getIDOfStation(conn, hashPassword)
            wf.linkIDWithStation(conn, stationLinkID, userDetails[0])
        else:
            return "Location not found"
    return {"stationName": stationName, "stationPass": hashPassword}

@app.route('/reportWarning', methods=['GET', 'POST'])
def reportWarning():
    reportTime = datetime.datetime.now()
    reportTimeStr = reportTime.strftime('%Y-%m-%d, %H:%M:%S')
    userDetails = request.args.get('userDetails').split(',')
    if request.method == 'POST':
        userInfo = wf.getLocationAndDeviceIDByName(conn, userDetails[0])
        if userInfo[0][1] != None:
            wf.addSamples(conn, userInfo[0][0], 5, userInfo[0][1], reportTimeStr, "True")
            return {"message": "Report submitted"}
        else:
            return {"message": "No home location set"}

@app.route('/imageReceiver', methods=['POST', 'GET'])
def receiveImage():
    if request.method == 'POST':
        locationName = request.form['location'].upper()
        username = request.form['hiddenUsername']
        if locationName == "":
            locationID = wf.getLocationAndDeviceIDByName(conn, username)[0][1]
            if locationID == None:
                return "Not a valid location name"
        else:
            locationID = wf.getLocationInfobyLocationName(conn, locationName)[0]
            if locationID == None:
                return "Not a valid location name"
            locationID = locationID[0]
        file = request.files['imageUpload']
        setHome = False
        if request.form.get('setHome'):
            setHome = True
        savePath = os.path.join("Images", datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")+".jpg")
        file.save(savePath)
        try:
            #image analysis algorithm
            percentageCover, condition, timestamp = wf.imageAnalysisSequence(savePath, True)
            userID = wf.getDeviceIDByNameAndType(conn, username, 'User')
            wf.addSamples(conn, userID, 4, locationID, timestamp, percentageCover)
            if setHome:
                wf.setHomeLocationOfDevice(conn, locationID, userID)
        except:
            return "Error, invalid file type"
        return "File upload finished, info : "+str(percentageCover)+" "+condition

@app.route('/DataReceiver', methods=['POST', 'GET'])
def appendData():
    if request.method == 'POST':
        query = request.json
        login = query['login']
        name, key = login['stationName'], login['stationKey']
        stationID, locationID = wf.getDeviceIDAndLocationIDByNameTypeAndKey(conn, name, 'Station', key)
        if stationID != None:
            if query['command'] == 'send':
                data = query['data']
                timestamp = query['timestamp']
                sampleTypes = query['types']
                for i in range(len(sampleTypes)):
                    if(sampleTypes[i] == 'media'):
                        imgRawB64 = data['media']
                        savePath = wf.saveAndLoadImg(imgRawB64, timestamp)
                        percentageCover, condition = wf.imageAnalysisSequence(savePath, False)
                        wf.addSamples(conn, stationID, 4, locationID, timestamp, percentageCover)
                    typeID = wf.getTypeIDFromListOfTypeNames(conn, sampleTypes, i)
                    if (typeID != None):
                        wf.addSamples(conn, stationID, typeID, locationID, timestamp, data[sampleTypes[i]])
                return data
            elif query['command'] == 'addType':
                typeName, typeUnits = query['name'], query['units']
                wf.addNewSampleType(conn, typeName, typeUnits)
                return "Successfully added data type "+typeName+" of units "+typeUnits
        else:
            return "Station not registered"

if __name__ == "__main__":
    cur.execute("SELECT TypeName FROM SampleType")
    typeNames = cur.fetchall()
    typeNames = wf.g.sqliteTupleToList(typeNames, 0)
    app.run(host="0.0.0.0", debug=False)

from Prediction import *
from flask import *
import os, base64, io

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
    cleanLocationList = []
    cur.execute("SELECT LocationName FROM Locations")
    locationList = cur.fetchall()
    for i in range(len(locationList)):
        cleanLocationList.append(locationList[i][0])
    return render_template('ForecastSite.html', locationList=cleanLocationList)

@app.route('/<locationName>')
def locationPage(locationName):
    return render_template('LocationTemplate.html', locationName=locationName)

@app.route('/<locationName>/fetchData')
def locationForecast(locationName):
    cur.execute("SELECT LocationID, Latitude, Longitude FROM Locations WHERE LocationName = ?", (locationName,))
    locationDetails = cur.fetchall()
    locationID, latitude, longitude = locationDetails[0][0], locationDetails[0][1], locationDetails[0][2]
    cur.execute("SELECT TypeID FROM DataType")
    availableDataTypes = cur.fetchall()
    rfAvailableDataTypes = []  # Queries from the sql database are received as tuples so it must be refined to an ordinary list
    for i in range(len(availableDataTypes)):
        rfAvailableDataTypes.append(availableDataTypes[i][0])
    data, time, latestValues = minuteCast(locationID=locationID, cur=cur)
    jsonData = {'data': {"Temperature": data[0], "Humidity": data[1], "Pressure": data[2], "Cloud cover": data[3]},
                'latestData' : {"Temperature": latestValues[0], "Humidity": latestValues[1], "Pressure": latestValues[2], "Cloud cover": latestValues[3]},
                'time': tuple(time[0]), 'location': {'locationName': locationName, 'latitude': latitude, 'longitude': longitude}}
    return jsonData

@app.route('/UserPage/<userDetails>')
def userPage(userDetails):
    return render_template('UserPage.html', info=list(userDetails.split(",")))

@app.route('/LoginPage')
def loginPage():
    return render_template('Login.html')

@app.route('/LoginReceiver', methods=['POST', 'GET'])
def loginRequest():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=? AND Password=?", (username, password))
        userID = cur.fetchall()
        if len(userID) == 0 or username == '' or password == '':
            return redirect(url_for('loginPage'))
        else:
            userID = userID[0][0]
            cur.execute("SELECT SampleID FROM Samples WHERE DeviceID=?", (userID,))
            imageCount = cur.fetchall()
            if len(imageCount) > 0:
                return redirect(url_for('userPage', userDetails=username+","+str(len(imageCount))))
            else:
                return redirect(url_for('userPage', userDetails=username + "," + str(0)))

@app.route('/RegisterReceiver', methods=['POST', 'GET'])
def registerRequest():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        checkPassword = request.form['checkPassword']
        cur.execute("SELECT DeviceID FROM RegisteredDevices WHERE Name=?", (username,))
        if password == checkPassword and len(cur.fetchall()) < 1 and username != '' and password != '':
            cur.execute("INSERT INTO RegisteredDevices (Name, Password, Type) VALUES (?, ?, 'User')", (username, password))
            conn.commit()
            return redirect(url_for('userPage', userDetails=username+","+str(0)))
        else:
            return redirect(url_for('loginPage'))

@app.route('/LocationReceiver', methods=['POST', 'GET'])
def getSelectedLocation():
    if request.method == 'POST':
        locationName = request.form.get('locationSelect')
        print(locationName)
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
        data, login, media = request.json['data'], request.json['login'], request.json['media']
        name, key = login['stationName'], login['stationKey']
        cur.execute("SELECT DeviceID, LocationID FROM RegisteredDevices WHERE Name=? AND Password=? AND Type='Station'", (name, key,))
        IDs = cur.fetchall()
        if len(IDs) > 0:
            stationID = IDs[0][0]
            locationID = IDs[0][1]
            timestamp, pressure, temperature = data["timestamp"], data["pressure"], data["temperature"]
            imgRawB64 = media['image']
            imgReadable = base64.b64decode(imgRawB64.encode('utf-8'))
            img = Image.open(io.BytesIO(imgReadable))
            datetimeTimestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d, %H:%M:%S')
            savePath = os.path.join("Images", datetimeTimestamp.strftime("%Y-%m-%d-%H%M%S") + ".jpg")
            #img.save(savePath)
            #percentageCover, condition = imageAnalysisSequence(savePath, False)
            #cur.execute("INSERT INTO Samples (DeviceID, TypeID, LocationID, Timestamp, Value) VALUES (?,?,?,?,?)",(stationID, 4, locationID, timestamp, percentageCover))
            cur.execute("INSERT INTO Samples (DeviceID, TypeID, LocationID, Timestamp, Value) VALUES (?,?,?,?,?)",(stationID, 1, locationID, timestamp, temperature))
            cur.execute("INSERT INTO Samples (DeviceID, TypeID, LocationID, Timestamp, Value) VALUES (?,?,?,?,?)",(stationID, 3, locationID, timestamp, pressure))
            conn.commit()
            return data
        else:
            return "Station not registered"

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)

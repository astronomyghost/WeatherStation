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
    print(locationName)
    cur.execute("SELECT LocationID FROM Locations WHERE LocationName = ?", (locationName,))
    locationID = cur.fetchall()
    locationID = locationID[0][0]
    cur.execute("SELECT TypeID FROM DataType")
    availableDataTypes = cur.fetchall()
    rfAvailableDataTypes = []  # Queries from the sql database are received as tuples so it must be refined to an ordinary list
    for i in range(len(availableDataTypes)):
        rfAvailableDataTypes.append(availableDataTypes[i][0])
    data, time = minuteCast(locationID=locationID, cur=cur)
    jsonData = {'data': {"Temperature": data[0], "Humidity": data[1], "Pressure": data[2], "Cloud cover": data[3]},
                'time': tuple(time[0]), 'locationName': locationName}
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

@app.route('/imageReceiver', methods=['POST', 'GET'])
def receiveImage():
    if request.method == 'POST':
        locationName = request.form['location'].upper()
        cur.execute("SELECT LocationID FROM Locations WHERE LocationName = ?",(locationName,))
        locationID = cur.fetchall()
        if len(locationID) > 0:
            locationID = locationID[0][0]
            username = request.form['hiddenUsername']
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
        else:
            return "Location does not exist in database, please add location"
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

@app.route('/LocationReceiver', methods=['POST', 'GET'])
def getSelectedLocation():
    if request.method == 'POST':
        locationName = request.form.get('locationSelect')
        if locationName == "none":
            return redirect(url_for('home'))
        else:
            return redirect(url_for('locationPage', locationName=locationName))

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)

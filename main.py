from Prediction import *
from flask import *
import sqlite3 as sql
import os

conn = sql.connect('Users.db', check_same_thread=False)
cur = conn.cursor()
app = Flask(__name__)

# Setting up the home page on the web server
@app.route('/')
def home():
    post = minuteCast()
    return render_template('ForecastSite.html', post=post)

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
        cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=? AND Password=?", (username, password))
        if len(cur.fetchall()) < 1 or username == '' or password == '':
            return redirect(url_for('loginPage'))
        else:
            cur.execute("SELECT ImageCount FROM RegisteredUsers WHERE Username=?", (username,))
            imageCount = cur.fetchall()
            return redirect(url_for('userPage', userDetails=username+","+str(imageCount[0][0])))

@app.route('/RegisterReceiver', methods=['POST', 'GET'])
def registerRequest():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        checkPassword = request.form['checkPassword']
        cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=?", (username,))
        if password == checkPassword and len(cur.fetchall()) < 1 and username != '' and password != '':
            cur.execute("INSERT INTO RegisteredUsers (Username, Password, ImageCount) VALUES (?, ?, 0)", (username, password))
            conn.commit()
            cur.execute("SELECT ImageCount FROM RegisteredUsers WHERE Username=?", (username,))
            imageCount = cur.fetchall()
            return redirect(url_for('userPage', userDetails=username+","+str(imageCount[0][0])))
        else:
            return redirect(url_for('loginPage'))

@app.route('/imageReceiver', methods=['POST', 'GET'])
def receiveImage():
    if request.method == 'POST':
        username = request.form['hiddenUsername']
        longitude, latitude = request.form['longitudeValue'], request.form['latitudeValue']
        file = request.files['imageUpload']
        setHome = False
        if request.form.get('setHome'):
            setHome = True
        file.save(file.filename)
        if longitude != "" and latitude != "":
            try:
                #image analysis algorithm
                skyShot = CloudCover(file.filename)
                skyShot.linearScan()
                percentageCover = skyShot.calcCoverPercentage()
                condition = skyShot.determineCondition()
                timestamp = skyShot.timestamp
                cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=?",(username,))
                userID = cur.fetchall()[0][0]
                cur.execute("INSERT INTO UserSubmittedData (UserID, Timestamp, CloudCover, Condition, Longitude, Latitude) VALUES (?,?,?,?,?,?)",(userID, timestamp, percentageCover, condition, longitude, latitude,))
                if setHome:
                    cur.execute("UPDATE RegisteredUsers SET Latitude=?, Longitude=? WHERE UserID=?",(float(latitude), float(longitude), userID,))
                cur.execute("UPDATE RegisteredUsers SET ImageCount=ImageCount+1 WHERE Username=?", (username,))
                conn.commit()
            except:
                os.remove(file.filename)
                return "Error, invalid file type"
        else:
            return "Error, no longitude and latitude provided"
        os.remove(file.filename)
        return "File upload finished, info : "+str(percentageCover)+" "+condition

if __name__ == "__main__":
    app.run(debug=False)
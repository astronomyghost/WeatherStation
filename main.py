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
        file = request.files['imageUpload']
        file.save(file.filename)
        try:
            #image analysis algorithm
            skyShot = CloudCover(file.filename)
            skyShot.linearScan()
            percentageCover = skyShot.calcCoverPercentage()
            condition = skyShot.determineCondition()
            print(username)
        except:
            os.remove(file.filename)
            return "Error, invalid file type"
        cur.execute("UPDATE RegisteredUsers SET ImageCount=ImageCount+1 WHERE Username=?", (username,))
        conn.commit()
        os.remove(file.filename)
        return "File upload finished, info : "+str(percentageCover)+" "+condition

if __name__ == "__main__":
    app.run(debug=False)
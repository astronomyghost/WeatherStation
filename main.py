from Prediction import *
from flask import *
import sqlite3 as sql

conn = sql.connect('Users.db', check_same_thread=False)
cur = conn.cursor()
app = Flask(__name__)

# Load image and begin simple analysis
skyShot = CloudCover("Clouds1.jpg")
skyShot.linearScan()
skyShot.calcCoverPercentage()
condition = skyShot.determineCondition()

# Setting up the home page on the web server
@app.route('/')
def home():
    post = minuteCast()
    return render_template('ForecastSite.html', post=post)

@app.route('/UserPage/<userDetails>')
def userPage(userDetails):
    print(userDetails)
    return render_template('UserPage.html', info=userDetails)

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
            imageCount = list(cur.execute("SELECT ImageCount FROM RegisteredUsers WHERE Username=?", (username,)))
            return redirect(url_for('userPage', userDetails=[username, imageCount]))
    else:
        username = request.form['username']
        password = request.form['password']
        cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=? AND Password=?", (username, password))
        if len(cur.fetchall()) < 1 or username == '' or password == '':
            return redirect(url_for('loginPage'))
        else:
            imageCount = list(cur.execute("SELECT ImageCount FROM RegisteredUsers WHERE Username=?", (username,)))
            return redirect(url_for('userPage', userDetails=[username, imageCount]))

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
            imageCount = list(cur.execute("SELECT ImageCount FROM RegisteredUsers WHERE Username=?", (username,)))
            return redirect(url_for('userPage', userDetails=[username, imageCount]))
        else:
            return redirect(url_for('loginPage'))
    else:
        username = request.args.get('username')
        password = request.args.get('password')
        checkPassword = request.args.get('checkPassword')
        cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=?", (username,))
        if password == checkPassword and len(cur.fetchall()) < 1 and username != '' and password != '':
            cur.execute("INSERT INTO RegisteredUsers (Username, Password, ImageCount) VALUES (?, ?, 0)", (username, password))
            conn.commit()
            imageCount = list(cur.execute("SELECT ImageCount FROM RegisteredUsers WHERE Username=?", (username,)))
            return redirect(url_for('userPage', userDetails=[username, imageCount]))
        else:
            return redirect(url_for('loginPage'))

if __name__ == "__main__":
    app.run(debug=False)

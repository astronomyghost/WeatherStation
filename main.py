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

@app.route('/UserPage/<user>')
def userPage(user):
    return render_template('UserPage.html', name=user)

@app.route('/LoginPage')
def loginPage():
    return render_template('Login.html')

@app.route('/LoginReceiver', methods=['POST', 'GET'])
def loginRequest():
    if request.method == 'POST':
        username = request.form['username']
        return redirect(url_for('userPage', user=username))
    else:
        username = request.args.get('username')
        return redirect(url_for('userPage', user=username))

@app.route('/RegisterReceiver', methods=['POST', 'GET'])
def registerRequest():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        checkPassword = request.form['checkPassword']
        cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=?", (username,))
        if password == checkPassword and len(cur.fetchall()) < 1:
            cur.execute("INSERT INTO RegisteredUsers (Username, Password, ImageCount) VALUES (?, ?, 0)", (username, password))
            conn.commit()
            return redirect(url_for('userPage', user=username))
        else:
            return redirect(url_for('loginPage'))
    else:
        username = request.args.get('username')
        password = request.args.get('password')
        checkPassword = request.args.get('checkPassword')
        cur.execute("SELECT UserID FROM RegisteredUsers WHERE Username=?", (username,))
        if password == checkPassword and len(cur.fetchall()) < 1:
            cur.execute("INSERT INTO RegisteredUsers (Username, Password, ImageCount) VALUES (?, ?, 0)", (username, password))
            conn.commit()
            return redirect(url_for('userPage', user=username))
        else:
            return redirect(url_for('loginPage'))

if __name__ == "__main__":
    app.run(debug=False)

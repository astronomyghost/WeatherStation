from Prediction import *
from flask import *

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
        userName = request.form['userName']
        return redirect(url_for('userPage', user=userName))
    else:
        userName = request.args.get('userName')
        return redirect(url_for('userPage', user=userName))

if __name__ == "__main__":
    app.run(debug=False)

import requests, json, bmp180, time
import datetime as dt
import os, base64

def getMedia():
    os.system('libcamera-jpeg -o cloudImage.jpg --shutter 2000 --width 640 --height 480')
    with open("cloudImage.jpg", "rb") as img:
        imgBytes = img.read()
    imgDecoded = base64.b64encode(imgBytes).decode("utf8")
    return imgDecoded

def writeToBuffer(query):
    with open("../../buffer.txt", "a") as buffer:
        buffer.write(str(query)+"\n")
        buffer.close()

def sendData(query, url):
    try:
        jsonData = requests.post(url, json=query)
        print(jsonData.text)
        return True
    except:
        print("server not online")
        writeToBuffer(query)
        return False

def sendBuffer(url):
    with open("../../buffer.txt", "r+") as buffer:
        queries = buffer.readlines()
        if(len(queries) > 0):
            count = 0
            for i in range(len(queries)):
                query = (queries[i][0:len(queries[i])-1].replace("'","\"")).replace("(","[").replace(")","]")
                if(sendData(json.loads(query), url) or queries[i] == ""):
                    count += 1
                time.sleep(0.0001)
            if(count == len(queries)):
                buffer.truncate(0)
            print("sent "+str(count)+" queries and missed "+str(len(queries)-count)+"queries")
        buffer.close()
            
url = "http://192.168.1.72:5000/DataReceiver"
location = "PURLEY"
stationName = "09082022PURLEY0001" #Format is DateOfCreation+Location+ID 
stationKey = "MY_KEY" #Will be a unique hash code in the future

command = input("What command would you like to use? (send, addType)")

if(command == "send"):
    sampleType = input("What type of data are you sending? (floats, both(media and floats))")
    if(sampleType == "both"):
        while True:      
            timestamp = dt.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
            temperature, pressure = bmp180.readBmp180()
            imgDecoded = getMedia()
            query = {"command": "send", "types": ("temperature", "pressure", "media"), "data": ({"temperature": temperature, "pressure": pressure, "media": (imgDecoded)}), "login": ({"stationName": stationName, "stationKey": stationKey}), "timestamp": timestamp}
            if(sendData(query, url)):
                sendBuffer(url)
            time.sleep(60)
    elif(sampleType == "floats"):
        while True:
            timestamp = dt.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
            temperature, pressure = bmp180.readBmp180()
            query = {"command": "send", "types": ("temperature", "pressure"), "data": ({"temperature": temperature, "pressure": pressure}), "login": ({"stationName": stationName, "stationKey": stationKey}), "timestamp": timestamp}
            if(sendData(query, url)):
                sendBuffer(url)
            time.sleep(60)
elif(command == "addType"):
    name = input("What is the name of the sample type?")
    units = input("What is the sample type's units?")
    query = {"command": "addType", "name": name, "units": units}
    try:
        jsonData = requests.post(url, json=query)
        print(jsonData.text)
    except:
        print("Server currently unavailable")
else:
    print("Invalid command")

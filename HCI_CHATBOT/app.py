from flask import Flask, render_template, request, jsonify,flash,redirect,url_for,session
from flask_session import Session
from flask_pymongo import PyMongo
import random
import json
from keras.models import load_model
import pyttsx3
import speech_recognition as sr
import numpy as np
import pickle
from nltk.stem import WordNetLemmatizer
import time
from time import sleep
import requests
import nltk
import objc
import subprocess
nltk.download('popular')
lemmatizer = WordNetLemmatizer()
r = sr.Recognizer()

model = load_model('./Chatbot_model.h5')
intents = json.loads(open('./intents.json').read())
words = pickle.load(open('./words.pkl', 'rb'))
classes = pickle.load(open('./classes.pkl', 'rb'))
def clean_up_sentence(sentence):
    # tokenize the pattern - split words into array
    sentence_words = nltk.word_tokenize(sentence)
    # stem each word - create short form for word
    sentence_words = [lemmatizer.lemmatize(
        word.lower()) for word in sentence_words]
    return sentence_words
# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
def bow(sentence, words, show_details=True):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)
    # bag of words - matrix of N words, vocabulary matrix
    bag = [0]*len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" % w)
    return(np.array(bag))
def predict_class(sentence, model):
    # filter out predictions below a threshold
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list


def getResponse(ints, intents_json):
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if i['tag'] == tag:
            result = random.choice(i['responses'])
            break
    return result


def text_to_speech(text):
    try:
        # Select a voice that sounds warm and friendly; for example, Victoria sounds quite natural.
        voice = 'Samantha'
        # Set a speaking rate that's calm and comforting. The normal rate is about 200 words per minute.
        rate = '180'
        # Command to execute the say function with specific voice and rate
        subprocess.call(['say', '-v', voice, '-r', rate, text])
    except Exception as e:
        print(f"Failed to speak out loud due to: {e}")

def speech_to_text():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            text = recognizer.recognize_google(audio)
            print(f"Recognized: {text}")
            return text
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except Exception as ex:
        print(f"An error occurred: {ex}")
    return ""
 
app = Flask(__name__)
app.static_folder = 'static'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config["MONGO_URI"] = "mongodb://localhost:27017/chatbot"
mongodb_client = PyMongo(app)
db = mongodb_client.db
app.secret_key = "abc"
   
@app.route("/chatbot")
def chatbot():
    return render_template('index.html')
def chatbot_response(msg):
    if msg=="show my appointment" or msg=="view my appointment" or msg=="when is my appointment booked?":
        print(session["name"])
        res=db.appointments.find({'name':session["name"]})
        result = []
        for data in res:
            result.append(data)
        
        l=[]
        for i in range(len(result)):
            patientname=result[i]["name"]
            gender=result[i]["gender"]
            date=result[i]["appointment"]
            location=result[i]["location"]
            department=result[i]["department"]
            app=[patientname,gender,date,location,department]
            l.append(app)
       
        res=""
        if(result==[]):
            res="you haven't booked any appointment yet.To book an appointment :<a href='http://127.0.0.1:5000/appointment' target='_blank'>Appointment page</a> "
        else:
            for i in l:
                res+="your appointment is booked on"+i[2]+"\nlocation:"+i[3]
        res+="For more details.visit your bookings<a href='http://127.0.0.1:5000/myappointments' target='_blank'>My appoitments</a>"
        text_to_speech(res)
        return res
    else:
        ints = predict_class(msg, model)
        res = getResponse(ints, intents)
        text_to_speech(res)
        return res
@app.route("/")
def home1():
    return render_template("login.html")

@app.route("/get")
def get_bot_response1():
    userText = request.args.get('msg')
    return chatbot_response(userText)
 


@app.route("/voice", methods=['GET'])
def speech_to_text_route():
    recognized_text = speech_to_text()
    if recognized_text:
        return jsonify(message=recognized_text)
    else:
        return jsonify(message="Failed to recognize speech or error occurred"), 400

@app.route("/speak", methods=['POST'])
def text_to_speech_route():
    data = request.json
    text = data.get("text")
    if text:
        text_to_speech(text)
        return jsonify(message="Speech synthesis successful"), 200
    else:
        return jsonify(message="No text provided"), 400
    return jsonify(message=res)


@app.route("/dashboard",methods=['GET'])
def home():
  return render_template("dashboard.html",value=session["name"])

@app.route("/appointment",methods=['GET'])
def appoint():
  return render_template("appointment.html",value=session["name"])

@app.route('/appointment', methods=['POST'])
def bookappointment():
    
    if request.method=='POST':
        
        data = {}
        data["name"]=request.form['name']
        data["gender"]=request.form['gender']
        data["contactnumber"]=request.form['contactnumber']
        data["appointment"]=request.form['appointment']
        data["location"]=request.form['location']
        data["department"]=request.form['department']
        db.appointments.insert_one(data)
        flash("your appointment is booked...Check your mail for further details") 
        return render_template("dashboard.html",value=session["name"])

@app.route("/login",methods=['GET'])
def get_login():
    return render_template("login.html")
@app.route("/signup",methods=['POST'])
def post_signup():
    if request.method=='POST':
        data = {}
        data["Username"]=request.form['Username']
        data["Email"]=request.form['Email']
        data["Password"]=request.form['Password']
        db.userDetails.insert_one(data)
        session["name"] = data["Username"]
        return render_template('dashboard.html',value=session["name"]) 
@app.route("/login",methods=['POST'])
def post_login():
    if request.method=='POST':
        username=request.form['Username']
        pwd=request.form['Password']
        if username!="" and pwd!="":
            res=db.userDetails.find({'Username':username});
            result = []
            for data in res:
                result.append(data)
            if result[0]['Password']==pwd:
                flash(f"Record Saved!", "success")
                session["name"] = username
                return redirect(url_for("home"))
            else:
                return redirect(url_for("login"))
    return render_template('login.html')
@app.route("/logout")
def logout():
    session["name"] = None
    return redirect("/")

@app.route("/myappointments")
def get_my_appointments():
    res=db.appointments.find({'name':session["name"]})
    result = []
    for data in res:
        result.append(data)
    print(len(result))
    l=[]
    for i in range(len(result)):
        patientname=result[i]["name"]
        gender=result[i]["gender"]
        date=result[i]["appointment"]
        location=result[i]["location"]
        department=result[i]["department"]
        app=[patientname,gender,date,location,department]
        l.append(app)
    print(l)
    return render_template('myappointments.html',value=session["name"],data=l)



     


  
if __name__ == "__main__":
    app.run()

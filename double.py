from flask import Flask, render_template, Response, flash, request, redirect, url_for, session, make_response
import cv2
import pickle
import numpy as np
import face_recognition
import cvzone
import datetime
from datetime import time as datetime_time
import time
import threading
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'abc'
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:@localhost/college"
db = SQLAlchemy(app)
with open('config.json') as p:
    params = json.load(p)['params']
file = open('Resources/EncodeFile.p', 'rb')
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds


camera = None  # Global variable to store camera object
morn_time = datetime_time(int(params['morning_time']))
even_time = datetime_time(int(params['evening_time']))
curr_time = datetime.datetime.now().time()


# Logic to find what function to call based on the time of day for marking the attendance
if morn_time <= curr_time < even_time:
    morn_attendance = True
    even_attendance = False
else:
    even_attendance = True
    morn_attendance = False

class Student_data(db.Model):
    __tablename__ = 'student_data'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    branch = db.Column(db.String(80), unique=True, nullable=False)
    division = db.Column(db.String(80), unique=True, nullable=False)
    regid = db.Column(db.String(80), unique=True, nullable=False)
    rollno = db.Column(db.String(120), unique=True, nullable=False)


# Model of Attendance table 
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(20))
    end_time = db.Column(db.String(20))
    date = db.Column(db.Date, default=datetime.date.today)
    roll_no = db.Column(db.String(20), nullable=False)
    division = db.Column(db.String(10))
    branch = db.Column(db.String(100))
    reg_id = db.Column(db.String(100))


# Model of users table 
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    reg_id = db.Column(db.Integer, unique=True)
    psw = db.Column(db.String(128))
    role = db.Column(db.String(100), unique=True)


def compare(encodeListKnown, encodeFace):
    try:
        matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
        faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
        matchIndex = np.argmin(faceDis)
        return matches, faceDis, matchIndex
    except Exception as e:
        print("Error in face comparison:", e)
        return None, None, None


def get_data(matches, matchIndex, studentIds):
    try:
        if matches[matchIndex]:
            student_id = studentIds[matchIndex]
            return student_id
        return None
    except Exception as e:
        print("Error in getting data:", e)
        return None


def mysqlconnect(student_id):
    # If student_id is None, return None for all values
    if student_id is None:
        return None, None, None, None, None

    try:
        with app.app_context():
            # Query student data using SQLAlchemy
            student_data = Student_data.query.filter_by(
                regid=student_id).first()

            if student_data:
                # If student data is found, extract values
                id = student_data.id
                name = student_data.name
                roll_no = student_data.rollno
                division = student_data.division
                branch = student_data.branch

                return id, name, roll_no, division, branch
            else:
                # If no student is found, return None for all values
                return None, None, None, None, None

    except Exception as e:
        print("Error:", e)
        return None, None, None, None, None


def morningattendance(name, current_date, roll_no, div, branch, reg_id):
    time.sleep(2)
    try:
        with app.app_context():
            existing_entry = Attendance.query.filter(
                Attendance.name == name,
                Attendance.date == current_date,
                Attendance.start_time != None
            ).first()

            if existing_entry:
                print("Your Attendance is already recorded before")
            else:
                new_attendance = Attendance(
                    name=name,
                    start_time=datetime.datetime.now().strftime("%H:%M:%S"),
                    date=current_date,
                    roll_no=roll_no,
                    division=div,
                    branch=branch,
                    reg_id=reg_id
                )
                db.session.add(new_attendance)
                db.session.commit()
                print("Start time and student data recorded in the database")
    except Exception as e:
        print("Error:", e)


# Function which writes the evening attendance in the database
def eveningattendance(name, current_date):
    time.sleep(2)
    try:
        with app.app_context():
            existing_entry = Attendance.query.filter(
                Attendance.name == name,
                Attendance.date == current_date,
                Attendance.start_time != None
            ).first()

            if existing_entry:
                existing_entry.end_time = datetime.datetime.now().strftime("%H:%M:%S")
                db.session.commit()
                print("End time recorded in the database")
            else:
                print("No existing entry found for evening attendance")
    except Exception as e:
        print("Error:", e)




def generate(camera):
    while True:
        try:
            success, frame = camera.read()
            if not success:
                break
            imgS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            faceCurFrame = face_recognition.face_locations(imgS)
            encodeCurFrame = face_recognition.face_encodings(
                imgS, faceCurFrame)

            for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                matches, faceDis, matchIndex = compare(
                    encodeListKnown, encodeFace)
                student_id = get_data(matches, matchIndex, studentIds)
                data = mysqlconnect(student_id)
                name = data[1]
                roll_no = data[2]
                div = data[3]
                branch = data[4]
                reg_id = student_id
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                bbox = x1, y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(frame, bbox, rt=0)
                cv2.putText(frame, name, (bbox[0], bbox[1] - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                            (255, 255, 0), 3, lineType=cv2.LINE_AA)
                cv2.putText(imgBackground, roll_no,
                            (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                current_date = datetime.datetime.now().date()
                if student_id and morn_attendance and student_id :
                    t = threading.Thread(target=morningattendance, args=(
                        name, current_date, roll_no, div, branch, reg_id))
                    t.start()
                if student_id and even_attendance and student_id :
                    t = threading.Thread(
                        target=eveningattendance, args=(name, current_date))
                    t.start()
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print("Error in frame generation:", e)


@app.route('/video1')
def video1():
    try:
        camera = cv2.VideoCapture("http://192.168.137.139:8080/video")
        return Response(generate(camera), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print("Error:", e)
        return "Error connecting to the video stream"

@app.route('/video2')
def video2():
    try:
        camera = cv2.VideoCapture("http://192.168.137.86:8080/video")
        return Response(generate(camera), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print("Error:", e)
        return "Error connecting to the video stream"


@app.route('/')
def index():
    return render_template('double.html')


if __name__ == '__main__':
    app.run(debug=True,host='192.168.0.128')

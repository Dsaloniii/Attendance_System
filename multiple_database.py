from flask import Flask, render_template, Response, request
import cv2
import pickle
import numpy as np
import face_recognition
import cvzone
import pymysql

app = Flask(__name__)
# Initialize variables to keep track of camera sources and their corresponding class information
camera_sources = {
    1: 'Class 1',
    0: 'Class 2'
}
current_camera_source = 0  # Initially set to the first camera source

# Load face encoding data
with open('Resources/EncodeFile.p', 'rb') as file:
    encodeListKnownWithIds = pickle.load(file)
encodeListKnown, studentIds = encodeListKnownWithIds


def get_data(matches, matchIndex, studentIds):
    if matches[matchIndex]:
        student_id = studentIds[matchIndex]  # ID from face recognition
        return student_id
    return None  # Return None if no match found


# Function to compare faces
def compare(encodeListKnown, encodeFace):
    matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
    faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
    matchIndex = np.argmin(faceDis)
    return matches, faceDis, matchIndex

# Function to get student data from database
def mysqlconnect(student_id):
    if student_id is None:
        return None, None, None, None, None

    # Establish connection to MySQL database
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='college'
    )

    cur = conn.cursor()

    try:
        # Query student data
        cur.execute("SELECT * FROM student_data WHERE regid = %s", (student_id,))
        output = cur.fetchall()

        for i in output:
            id = i[0]
            name = i[1]
            roll_no = i[2]
            division = i[3]
            branch = i[4]

        # Close connection
        conn.close()
        return id, name, roll_no, division, branch

    except Exception as e:
        print("Error:", e)
        return None, None, None, None, None

# Function to generate video frames
def gen_frames():
    camera = cv2.VideoCapture(current_camera_source)  # Access the current camera source
    while True:
        success, frame = camera.read()
        if not success:
            break
        imgS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches, faceDis, matchIndex = compare(encodeListKnown, encodeFace)
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
            cv2.putText(imgBackground, reg_id,
                        (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            # Insert data into the database based on the current camera source
            class_info = camera_sources[current_camera_source]
            print(f"Camera source {current_camera_source}: {name} attended {class_info}")
            # Your database insertion code goes here

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/switch_camera', methods=['POST'])
def switch_camera():
    global current_camera_source
    # Get the new camera source from the request data
    new_camera_source = int(request.form['camera_source'])
    if new_camera_source in camera_sources:
        current_camera_source = new_camera_source
        print(f"Switched to camera source {current_camera_source}")
        return 'Switched camera source successfully'
    else:
        return 'Invalid camera source'

@app.route('/')
def index():
    return render_template('multiple.html')

if __name__ == '__main__':
    app.run(debug=True)

import av
import cv2
import csv
import json
import os
import threading

from datetime import datetime

import streamlit as st

from streamlit_webrtc import (
    VideoProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)


# ==========================================
# FILE LOCATIONS
# ==========================================

MODEL_PATH = "data/model/face_model.yml"
LABEL_PATH = "data/model/labels.json"
STUDENTS_PATH = "data/students.csv"
ATTENDANCE_PATH = "data/attendance.csv"


# ==========================================
# LOAD STUDENT NAMES
# ==========================================

students = {}

with open(STUDENTS_PATH, "r", newline="") as file:

    reader = csv.DictReader(file)

    for row in reader:

        students[row["student_id"]] = row["name"]


# ==========================================
# LOAD LABEL MAP
# ==========================================

with open(LABEL_PATH, "r") as file:

    raw_labels = json.load(file)


# JSON converts integer keys to strings,
# so convert them back.
label_map = {
    int(label): student_id
    for label, student_id in raw_labels.items()
}


# ==========================================
# LOAD FACE RECOGNITION MODEL
# ==========================================

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read(MODEL_PATH)


# ==========================================
# LOAD FACE DETECTOR
# ==========================================

face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)


# ==========================================
# ATTENDANCE LOCK
# ==========================================

attendance_lock = threading.Lock()


# ==========================================
# MARK ATTENDANCE
# ==========================================

def mark_attendance(student_id, name):

    today = datetime.now().strftime("%Y-%m-%d")

    with attendance_lock:

        already_present = False

        # Check existing attendance
        if os.path.exists(ATTENDANCE_PATH):

            with open(
                ATTENDANCE_PATH,
                "r",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    if (
                        row["student_id"] == student_id
                        and row["date"] == today
                    ):

                        already_present = True
                        break

        # Don't mark same student twice
        if already_present:

            return False

        now = datetime.now()

        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        with open(
            ATTENDANCE_PATH,
            "a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                student_id,
                name,
                date,
                time,
                "Present"
            ])

        print(
            f"Attendance marked: "
            f"{student_id} - {name}"
        )

        return True


# ==========================================
# VIDEO PROCESSOR
# ==========================================

class AttendanceProcessor(VideoProcessorBase):

    def __init__(self):

        self.frame_counter = 0

        self.last_student = None


    def recv(self, frame):

        img = frame.to_ndarray(
            format="bgr24"
        )

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )


        for (x, y, w, h) in faces:

            face = gray[
                y:y+h,
                x:x+w
            ]

            face = cv2.resize(
                face,
                (200, 200)
            )


            # ----------------------------------
            # FACE RECOGNITION
            # ----------------------------------

            label, confidence = recognizer.predict(
                face
            )
            cv2.putText(
    img,
    f"Distance: {confidence:.1f}",
    (20, 40),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    (255, 255, 255),
    2
)


            # LBPH:
            # LOWER confidence value = better match.
            #
            # Start with 65 for our demo.
            # We can tune this later.

            if (
                confidence < 45
                and label in label_map
            ):

                student_id = label_map[label]

                name = students.get(
                    student_id,
                    student_id
                )

                display_name = name

                box_color = (
                    0,
                    255,
                    0
                )


                # ----------------------------------
                # MARK ATTENDANCE
                # ----------------------------------

                self.frame_counter += 1


                # Require several recognized frames
                # before marking attendance.

                if (
                    self.last_student
                    == student_id
                ):

                    if self.frame_counter >= 10:

                     pass

                else:

                    self.last_student = student_id

                    self.frame_counter = 1


                # Student ID
                cv2.putText(
                    img,
                    student_id,
                    (
                        x,
                        y + h + 25
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    box_color,
                    2
                )


            else:

                display_name = "UNKNOWN"

                box_color = (
                    0,
                    0,
                    255
                )

                self.frame_counter = 0

                self.last_student = None


            # ----------------------------------
            # FACE BOX
            # ----------------------------------

            cv2.rectangle(
                img,
                (x, y),
                (
                    x + w,
                    y + h
                ),
                box_color,
                3
            )


            # ----------------------------------
            # NAME
            # ----------------------------------

            cv2.putText(
                img,
                display_name,
                (
                    x,
                    max(
                        y - 15,
                        25
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                box_color,
                2
            )


        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


# ==========================================
# STREAMLIT WEBSITE
# ==========================================

st.set_page_config(
    page_title="VisionED AI",
    page_icon="🎓",
    layout="wide"
)


st.title("🎓 VisionED AI")

st.subheader(
    "📋 AI Smart Attendance"
)


st.write(
    "Look at the camera. "
    "Enrolled students can be recognized "
    "and attendance is recorded automatically."
)


st.warning(
    "Demo system: face recognition can make "
    "mistakes. Unknown or uncertain faces "
    "should not be treated as identified."
)


# ==========================================
# CAMERA
# ==========================================

webrtc_streamer(

    key="attendance-camera",

    mode=WebRtcMode.SENDRECV,

    video_processor_factory=AttendanceProcessor,

    media_stream_constraints={
        "video": True,
        "audio": False
    },

    async_processing=True
)


# ==========================================
# ATTENDANCE TABLE
# ==========================================

st.divider()

st.subheader(
    "📊 Today's Attendance"
)


if os.path.exists(ATTENDANCE_PATH):

    import pandas as pd

    try:

        attendance_data = pd.read_csv(
            ATTENDANCE_PATH
        )

        if not attendance_data.empty:

            today = datetime.now().strftime(
                "%Y-%m-%d"
            )

            today_data = attendance_data[
                attendance_data["date"]
                == today
            ]

            st.metric(
                "Students Present",
                len(today_data)
            )

            st.dataframe(
                today_data,
                use_container_width=True
            )

        else:

            st.info(
                "No attendance recorded yet."
            )

    except Exception as error:

        st.error(
            f"Could not load attendance: {error}"
        )


st.caption(
    "VisionED AI • Smart Classroom Management"
)
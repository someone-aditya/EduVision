import streamlit as st
import pandas as pd
import os
import av
import cv2
import json
import threading
from deepface import DeepFace
import numpy as np
from datetime import datetime

from streamlit_webrtc import (
    VideoProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)


# ==========================================
# EDVISION SETTINGS
# ==========================================

st.set_page_config(
    page_title="EduVision",
    page_icon="🎓",
    layout="wide"
)
# ==========================================
# SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🎓 EduVision")

st.sidebar.write(
    "Smart Classroom Management"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "📋 Smart Attendance",
        "🚪 Smart Occupancy",
        "📊 Reports"
    ]
)

st.sidebar.divider()

st.sidebar.success("● System Online")

STUDENTS_FILE = "data/students.csv"
ATTENDANCE_FILE = "data/attendance.csv"

STUDENT_COLUMNS = [
    "student_id",
    "name"
]

ATTENDANCE_COLUMNS = [
    "student_id",
    "name",
    "date",
    "time",
    "status"
]


# ==========================================
# SAFE CSV LOADER
# ==========================================

def load_csv_safely(file_path, required_columns):

    if not os.path.exists(file_path):
        return pd.DataFrame(columns=required_columns)

    if os.path.getsize(file_path) == 0:
        return pd.DataFrame(columns=required_columns)

    try:

        data = pd.read_csv(file_path)

        # Clean accidental spaces
        data.columns = data.columns.str.strip()

        # Add any missing columns
        for column in required_columns:

            if column not in data.columns:
                data[column] = ""

        return data

    except Exception:
        return pd.DataFrame(columns=required_columns)

# ==========================================
# FACE RECOGNITION CAMERA
# ==========================================

MODEL_PATH = "data/model/face_model.yml"
LABELS_PATH = "data/model/labels.json"


# Face detector
face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)


# Face recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read(MODEL_PATH)


# Load label numbers
with open(LABELS_PATH, "r") as file:
    raw_labels = json.load(file)


label_map = {
    int(label): student_id
    for label, student_id in raw_labels.items()
}


# Load student names
student_names = {}

if os.path.exists(STUDENTS_FILE):

    student_data = pd.read_csv(STUDENTS_FILE)

    student_data.columns = (
        student_data.columns.str.strip()
    )

    for _, row in student_data.iterrows():

        student_names[
            str(row["student_id"]).strip()
        ] = str(row["name"]).strip()

# ==========================================
# AUTOMATIC ATTENDANCE
# ==========================================

attendance_lock = threading.Lock()


def mark_attendance(student_id, name):

    with attendance_lock:

        now = datetime.now()

        today_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        # Create file if it does not exist
        if not os.path.exists(ATTENDANCE_FILE):

            attendance_data = pd.DataFrame(
                columns=ATTENDANCE_COLUMNS
            )

        else:

            try:
                attendance_data = pd.read_csv(
                    ATTENDANCE_FILE
                )

            except Exception:

                attendance_data = pd.DataFrame(
                    columns=ATTENDANCE_COLUMNS
                )


        # Check if student already marked today
        already_present = False

        if not attendance_data.empty:

            already_present = (
                (
                    attendance_data["student_id"]
                    .astype(str)
                    .str.strip()
                    == str(student_id)
                )
                &
                (
                    attendance_data["date"]
                    .astype(str)
                    .str.strip()
                    == today_date
                )
            ).any()


        # Mark only once per day
        if not already_present:

            new_record = pd.DataFrame(
                [{
                    "student_id": student_id,
                    "name": name,
                    "date": today_date,
                    "time": current_time,
                    "status": "Present"
                }]
            )

            attendance_data = pd.concat(
                [
                    attendance_data,
                    new_record
                ],
                ignore_index=True
            )

            attendance_data.to_csv(
                ATTENDANCE_FILE,
                index=False
            )
# ==========================================
# CAMERA PROCESSOR
# ==========================================

class AttendanceCamera(VideoProcessorBase):

    def __init__(self):
        self.last_student = None
        self.stable_frames = 0

    def recv(self, frame):

        img = frame.to_ndarray(format="bgr24")

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        for (x, y, w, h) in faces:

            # Get detected face
            face = gray[y:y+h, x:x+w]

            # Resize face to same size used in training
            face = cv2.resize(
                face,
                (200, 200)
            )

            # ==================================
            # RECOGNIZE FACE
            # ==================================

            label, distance = recognizer.predict(face)

            # Lower distance = better match
            MATCH_THRESHOLD = 70

            # ==================================
            # KNOWN STUDENT
            # ==================================

            if (
                distance < MATCH_THRESHOLD
                and label in label_map
            ):

                student_id = label_map[label]

                name = student_names.get(
                    student_id,
                    student_id
                )

                text = f"{name} | {student_id}"

                color = (0, 255, 0)

                # ==================================
                # CHECK STABLE RECOGNITION
                # ==================================

                if self.last_student == student_id:
                    self.stable_frames += 1

                else:
                    self.last_student = student_id
                    self.stable_frames = 1

                # ==================================
                # MARK ATTENDANCE
                # ==================================

                if self.stable_frames >= 15:

                    mark_attendance(
                        student_id,
                        name
                    )

                    text = f"{name} | PRESENT"

            # ==================================
            # UNKNOWN FACE
            # ==================================

            else:

                self.last_student = None
                self.stable_frames = 0

                text = "UNKNOWN"

                color = (0, 0, 255)

            # ==================================
            # DRAW FACE BOX
            # ==================================

            cv2.rectangle(
                img,
                (x, y),
                (x + w, y + h),
                color,
                3
            )

            # Student name / UNKNOWN
            cv2.putText(
                img,
                text,
                (x, max(y - 35, 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

            # Recognition distance
            cv2.putText(
                img,
                f"Distance: {distance:.1f}",
                (x, max(y - 10, 50)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )
# ==========================================
# LOAD DATABASE
# ==========================================

students = load_csv_safely(
    STUDENTS_FILE,
    STUDENT_COLUMNS
)

attendance = load_csv_safely(
    ATTENDANCE_FILE,
    ATTENDANCE_COLUMNS
)


# ==========================================
# TODAY'S DATA
# ==========================================

today = datetime.now().strftime("%Y-%m-%d")

if not attendance.empty:

    today_attendance = attendance[
        attendance["date"].astype(str).str.strip()
        == today
    ]

else:

    today_attendance = pd.DataFrame(
        columns=ATTENDANCE_COLUMNS
    )


# ==========================================
# STATISTICS
# ==========================================

total_students = len(students)

if not today_attendance.empty:

    present_today = today_attendance[
        "student_id"
    ].nunique()

else:

    present_today = 0


absent_today = max(
    total_students - present_today,
    0
)

# ==========================================
# SMART ATTENDANCE PAGE
# ==========================================

if page == "📋 Smart Attendance":

    st.title("📋 EduVision Smart Attendance")

    st.write(
        "Press START and allow camera access."
    )

    webrtc_streamer(
        key="eduvision-attendance-camera",

        mode=WebRtcMode.SENDRECV,

        video_processor_factory=AttendanceCamera,

        media_stream_constraints={
            "video": True,
            "audio": False
        },

        async_processing=True
    )

    st.info(
        "EduVision camera system is active."
    )

    st.stop()
    # ==========================================
# REPORTS PAGE
# ==========================================

if page == "📊 Reports":

    st.title("📊 EduVision Attendance Reports")

    st.write(
        "View and analyze attendance records recorded by EduVision."
    )

    st.divider()

    # ======================================
    # REPORT STATISTICS
    # ======================================

    total_records = len(attendance)

    if not attendance.empty:
        unique_students = attendance["student_id"].nunique()
        total_days = attendance["date"].nunique()
    else:
        unique_students = 0
        total_days = 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📋 Attendance Records",
            total_records
        )

    with col2:
        st.metric(
            "👨‍🎓 Students Recorded",
            unique_students
        )

    with col3:
        st.metric(
            "📅 School Days Recorded",
            total_days
        )

    st.divider()

    # ======================================
    # ATTENDANCE HISTORY
    # ======================================

    st.subheader("📋 Attendance History")

    if not attendance.empty:

        st.dataframe(
            attendance[
                [
                    "student_id",
                    "name",
                    "date",
                    "time",
                    "status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No attendance records are available yet."
        )

    st.divider()

    # ======================================
    # STUDENT SUMMARY
    # ======================================

    st.subheader("👨‍🎓 Student Attendance Summary")

    if not attendance.empty:

        student_summary = (
            attendance
            .groupby(
                ["student_id", "name"]
            )
            .size()
            .reset_index(
                name="Days Present"
            )
        )

        st.dataframe(
            student_summary,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Attendance will appear here after students are marked present."
        )

    st.divider()

    st.caption(
        "EduVision • Attendance Reporting System"
    )

    # Stop here so dashboard does not appear below Reports
    st.stop()
# ==========================================
# HEADER
# ==========================================

st.title("🎓 EduVision")

st.subheader(
    "AI-Powered Smart Classroom Management System"
)

st.caption(
    "Smarter Classrooms Through AI"
)

st.divider()


# ==========================================
# CLASSROOM OVERVIEW
# ==========================================

st.header("📊 Today's Classroom Overview")

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "👨‍🎓 Total Students",
        total_students
    )


with col2:

    st.metric(
        "✅ Present",
        present_today
    )


with col3:

    st.metric(
        "❌ Absent",
        absent_today
    )


with col4:

    st.metric(
        "🚪 Room Occupancy",
        "Not Active"
    )


st.divider()


# ==========================================
# AI SYSTEMS
# ==========================================

st.header("🧠 EduVision AI Systems")

left, right = st.columns(2)


with left:

    st.subheader("📋 Smart Attendance")

    st.write(
        "Recognizes enrolled students and "
        "records their attendance automatically."
    )

    st.write("✅ Face Detection")
    st.write("✅ Student Recognition")
    st.write("✅ Automatic Date & Time")
    st.write("✅ Unknown Face Detection")


with right:

    st.subheader("🚪 Smart Occupancy")

    st.write(
        "Uses AI person detection to monitor "
        "classroom occupancy."
    )

    st.write("✅ Person Detection")
    st.write("✅ Entry Detection")
    st.write("✅ Exit Detection")
    st.write("✅ Current Room Count")


st.divider()


# ==========================================
# ATTENDANCE TABLE
# ==========================================

st.header("📋 Today's Attendance")


if not today_attendance.empty:

    st.dataframe(
        today_attendance[
            [
                "student_id",
                "name",
                "time",
                "status"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No attendance has been recorded today."
    )


st.divider()


# ==========================================
# SYSTEM STATUS
# ==========================================

st.header("⚙️ System Status")

status1, status2, status3 = st.columns(3)


with status1:

    st.success(
        "● Attendance System Ready"
    )


with status2:

    st.success(
        "● Student Database Connected"
    )


with status3:

    st.info(
        "● Occupancy Camera Waiting"
    )


st.divider()


# ==========================================
# FOOTER
# ==========================================

st.caption(
    "EduVision • AI-Powered Smart Classroom Management"
)
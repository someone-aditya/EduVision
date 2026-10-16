import streamlit as st
import pandas as pd
import os
import av
import cv2
import json
import threading
from ultralytics import YOLO
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
# DEEPFACE RECOGNITION
# ==========================================

STUDENT_IMAGES_DIR = "data/student_images"
FACE_MODEL = "Facenet512"
# Cosine distance: lower = more similar. Start strict to reject strangers.
FACE_MATCH_THRESHOLD = 0.30

face_detector = cv2.CascadeClassifier(
    os.path.join("assets", "haarcascade_frontalface_default.xml")
)

student_names = {}
if os.path.exists(STUDENTS_FILE):
    student_data = load_csv_safely(STUDENTS_FILE, STUDENT_COLUMNS)
    for _, row in student_data.iterrows():
        student_id = str(row["student_id"]).strip()
        student_names[student_id] = str(row["name"]).strip()


def get_embedding(image):
    """Return a normalized DeepFace embedding, or None if no usable face."""
    try:
        reps = DeepFace.represent(
            img_path=image,
            model_name=FACE_MODEL,
            detector_backend="skip",
            enforce_detection=False,
            align=False,
        )
        if not reps:
            return None
        emb = np.asarray(reps[0]["embedding"], dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm == 0:
            return None
        return emb / norm
    except Exception:
        return None


@st.cache_resource
def load_student_embeddings():
    database = {}
    if not os.path.isdir(STUDENT_IMAGES_DIR):
        return database

    for student_id in sorted(os.listdir(STUDENT_IMAGES_DIR)):
        folder = os.path.join(STUDENT_IMAGES_DIR, student_id)
        if not os.path.isdir(folder):
            continue

        embeddings = []
        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            path = os.path.join(folder, filename)
            image = cv2.imread(path)
            if image is None:
                continue

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            if len(faces) == 0:
                continue

            x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
            pad = int(0.15 * max(w, h))
            x1, y1 = max(0, x-pad), max(0, y-pad)
            x2, y2 = min(image.shape[1], x+w+pad), min(image.shape[0], y+h+pad)
            face = image[y1:y2, x1:x2]
            if face.size == 0:
                continue

            emb = get_embedding(face)
            if emb is not None:
                embeddings.append(emb)

        if embeddings:
            database[student_id] = embeddings

    return database


student_embeddings = load_student_embeddings()

# ==========================================
# AUTOMATIC ATTENDANCE
# ==========================================

attendance_lock = threading.Lock()


def mark_attendance(student_id, name):
    with attendance_lock:
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        attendance_data = load_csv_safely(ATTENDANCE_FILE, ATTENDANCE_COLUMNS)
        already_present = False
        if not attendance_data.empty:
            already_present = (
                (attendance_data["student_id"].astype(str).str.strip() == str(student_id))
                & (attendance_data["date"].astype(str).str.strip() == today_date)
            ).any()

        if not already_present:
            new_record = pd.DataFrame([{
                "student_id": student_id,
                "name": name,
                "date": today_date,
                "time": current_time,
                "status": "Present",
            }])
            attendance_data = pd.concat([attendance_data, new_record], ignore_index=True)
            os.makedirs(os.path.dirname(ATTENDANCE_FILE), exist_ok=True)
            attendance_data.to_csv(ATTENDANCE_FILE, index=False)


class AttendanceCamera(VideoProcessorBase):
    def __init__(self):
        self.frame_number = 0
        self.last_student = None
        self.stable_checks = 0
        self.cached_text = "Scanning..."
        self.cached_color = (0, 255, 255)
        self.cached_distance = None

    def recognize(self, face_bgr):
        query = get_embedding(face_bgr)
        if query is None or not student_embeddings:
            return None, None

        best_student = None
        best_distance = float("inf")

        for student_id, embeddings in student_embeddings.items():
            # Compare against every enrolled photo and use the best match.
            distance = min(float(1.0 - np.dot(query, emb)) for emb in embeddings)
            if distance < best_distance:
                best_distance = distance
                best_student = student_id

        if best_distance <= FACE_MATCH_THRESHOLD:
            return best_student, best_distance
        return None, best_distance

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.frame_number += 1
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        # Attendance is only considered when exactly one face is visible.
        if len(faces) != 1:
            self.last_student = None
            self.stable_checks = 0
            if len(faces) > 1:
                self.cached_text = "ONE PERSON AT A TIME"
                self.cached_color = (0, 165, 255)
            else:
                self.cached_text = "Scanning..."
                self.cached_color = (0, 255, 255)
            self.cached_distance = None

        for (x, y, w, h) in faces:
            pad = int(0.15 * max(w, h))
            x1, y1 = max(0, x-pad), max(0, y-pad)
            x2, y2 = min(img.shape[1], x+w+pad), min(img.shape[0], y+h+pad)
            face = img[y1:y2, x1:x2]

            # DeepFace is expensive, so check every 10th frame.
            if len(faces) == 1 and self.frame_number % 10 == 0 and face.size:
                student_id, distance = self.recognize(face)
                self.cached_distance = distance

                if student_id is not None:
                    name = student_names.get(student_id, student_id)
                    if self.last_student == student_id:
                        self.stable_checks += 1
                    else:
                        self.last_student = student_id
                        self.stable_checks = 1

                    self.cached_text = f"{name} | {student_id}"
                    self.cached_color = (0, 255, 0)

                    # Require 3 successful DeepFace checks before attendance.
                    if self.stable_checks >= 3:
                        mark_attendance(student_id, name)
                        self.cached_text = f"{name} | PRESENT"
                else:
                    self.last_student = None
                    self.stable_checks = 0
                    self.cached_text = "UNKNOWN"
                    self.cached_color = (0, 0, 255)

            cv2.rectangle(img, (x, y), (x+w, y+h), self.cached_color, 3)
            cv2.putText(
                img, self.cached_text, (x, max(y-30, 25)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.cached_color, 2
            )
            if self.cached_distance is not None:
                cv2.putText(
                    img, f"Match distance: {self.cached_distance:.3f}",
                    (x, max(y-8, 50)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, self.cached_color, 2
                )

        return av.VideoFrame.from_ndarray(img, format="bgr24")
# ==========================================
# SMART OCCUPANCY CAMERA
# ==========================================

occupancy_model = YOLO("yolo11n.pt")


class OccupancyCamera(VideoProcessorBase):

    def __init__(self):
        self.previous_positions = {}
        self.entered = 0
        self.exited = 0
        self.inside = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")

        height, width = img.shape[:2]

        # Virtual doorway line
        line_x = width // 2

        results = occupancy_model.track(
            img,
            persist=True,
            classes=[0],
            conf=0.45,
            verbose=False
        )

        people_detected = 0

        # Draw doorway line
        cv2.line(
            img,
            (line_x, 0),
            (line_x, height),
            (255, 255, 255),
            3
        )

        cv2.putText(
            img,
            "DOOR LINE",
            (line_x + 10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        for result in results:

            if (
                result.boxes is not None
                and result.boxes.id is not None
            ):

                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.int().cpu().tolist()

                people_detected = len(boxes)

                for box, track_id in zip(boxes, ids):

                    x1, y1, x2, y2 = map(int, box)

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    # Draw person
                    cv2.rectangle(
                        img,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    cv2.circle(
                        img,
                        (center_x, center_y),
                        5,
                        (0, 255, 255),
                        -1
                    )

                    cv2.putText(
                        img,
                        f"PERSON {track_id}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    # Check line crossing
                    if track_id in self.previous_positions:

                        old_x = self.previous_positions[track_id]

                        # Left -> Right = ENTER
                        if old_x < line_x <= center_x:
                            self.entered += 1
                            self.inside += 1

                        # Right -> Left = EXIT
                        elif old_x > line_x >= center_x:
                            self.exited += 1
                            self.inside = max(0, self.inside - 1)

                    self.previous_positions[track_id] = center_x

        # Information panel
        cv2.putText(
            img,
            f"Detected: {people_detected}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2
        )

        cv2.putText(
            img,
            f"Entered: {self.entered}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 0),
            2
        )

        cv2.putText(
            img,
            f"Exited: {self.exited}",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2
        )

        cv2.putText(
            img,
            f"Inside: {self.inside}",
            (20, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
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
# SMART OCCUPANCY PAGE
# ==========================================

if page == "🚪 Smart Occupancy":

    st.title("🚪 EduVision Smart Occupancy")

    st.write(
        "AI-powered person detection for classroom occupancy."
    )

    st.info("Press START and allow camera access.")

    webrtc_streamer(
        key="eduvision-occupancy-camera",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=OccupancyCamera,
        media_stream_constraints={
            "video": True,
            "audio": False
        },
        async_processing=True
    )

    st.success("🟢 Smart Occupancy System Ready")

    st.stop()
    # ==========================================
# REPORTS PAGE
# ==========================================

if page == "📊 Reports":

   if st.button("🗑️ Clear Today's Attendance"):

    df = load_csv_safely(
        ATTENDANCE_FILE,
        ATTENDANCE_COLUMNS
    )

    if not df.empty:
        df = df[
            df["date"].astype(str).str.strip() != today
        ]

        df.to_csv(ATTENDANCE_FILE, index=False)

    st.success("✅ Today's attendance cleared!")
    st.rerun()

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
current_time = datetime.now().strftime("%d %B %Y • %I:%M %p")
st.write(f"🕐 {current_time}")
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

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.success("📋 Attendance\n\n🟢 READY")

with col2:
    st.success("🚪 Occupancy\n\n🟢 READY")

with col3:
    st.success("👤 Face Recognition\n\n🟢 ACTIVE")

with col4:
    st.success("📊 Reports\n\n🟢 ACTIVE")

st.divider()

# ==========================================
# FOOTER
# ==========================================

st.caption(
    "EduVision • AI-Powered Smart Classroom Management"
)
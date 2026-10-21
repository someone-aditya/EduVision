import streamlit as st
import pandas as pd
import os
import av
import cv2
import threading
from ultralytics import YOLO
from deepface import DeepFace
import numpy as np
from datetime import datetime
import streamlit.components.v1 as components

from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer


# ==========================================
# EDVISION SETTINGS
# ==========================================

st.set_page_config(
    page_title="EduVision",
    page_icon="🎓",
    layout="wide",
)

st.markdown("""
<style>
:root{--bg:#060914;--panel:rgba(15,23,42,.72);--line:rgba(148,163,184,.16)}
.stApp{background:radial-gradient(circle at 15% 0%,rgba(59,130,246,.16),transparent 30%),radial-gradient(circle at 85% 5%,rgba(139,92,246,.14),transparent 28%),linear-gradient(180deg,#060914,#0b1220);color:#f8fafc}
[data-testid="stSidebar"]{background:rgba(6,9,20,.96);border-right:1px solid var(--line)}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(15,23,42,.9),rgba(15,23,42,.58));border:1px solid var(--line);border-radius:20px;padding:18px;box-shadow:0 18px 50px rgba(0,0,0,.2);transition:.22s}
[data-testid="stMetric"]:hover{transform:translateY(-4px);border-color:rgba(34,211,238,.5);box-shadow:0 20px 60px rgba(34,211,238,.08)}
.ev-hero{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:28px;padding:36px;margin:2px 0 24px;background:linear-gradient(135deg,rgba(59,130,246,.17),rgba(139,92,246,.10)),rgba(15,23,42,.62);box-shadow:0 30px 90px rgba(0,0,0,.28)}
.ev-hero:after{content:"";position:absolute;width:240px;height:240px;right:-70px;top:-100px;border-radius:50%;background:rgba(34,211,238,.16);filter:blur(25px);animation:pulse 4s ease-in-out infinite}
.ev-kicker{display:inline-block;padding:7px 12px;border:1px solid rgba(34,211,238,.24);border-radius:999px;color:#a5f3fc;background:rgba(34,211,238,.07);font-size:12px;letter-spacing:.12em;font-weight:700}
.ev-title{font-size:clamp(38px,5vw,64px);line-height:1;margin:18px 0 12px;font-weight:850;letter-spacing:-.045em;background:linear-gradient(90deg,#fff,#bae6fd 55%,#c4b5fd);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ev-sub{color:#cbd5e1;max-width:760px;font-size:17px;line-height:1.65;margin-bottom:18px}
.ev-live{display:flex;align-items:center;gap:8px;color:#bbf7d0;font-size:13px;font-weight:700}
.ev-dot{width:9px;height:9px;border-radius:50%;background:#22c55e;animation:live 1.8s infinite}
.stButton>button{border-radius:14px;border:1px solid rgba(34,211,238,.22);background:linear-gradient(135deg,#2563eb,#7c3aed);color:white;font-weight:750;min-height:44px;transition:.18s}
.stButton>button:hover{transform:translateY(-2px) scale(1.01);box-shadow:0 12px 34px rgba(59,130,246,.22);color:white}
h1,h2,h3{letter-spacing:-.025em}
@keyframes pulse{50%{transform:scale(1.12);opacity:1}}
@keyframes live{0%{box-shadow:0 0 0 0 rgba(34,197,94,.55)}70%{box-shadow:0 0 0 9px rgba(34,197,94,0)}}
</style>
""", unsafe_allow_html=True)

components.html("""
<div id="trail" style="position:fixed;width:16px;height:16px;border-radius:50%;background:rgba(34,211,238,.7);box-shadow:0 0 25px #22d3ee;pointer-events:none;z-index:999999"></div>
<script>
try{
 const d=window.parent.document,t=document.getElementById('trail');
 d.addEventListener('mousemove',e=>{t.style.left=(e.clientX-8)+'px';t.style.top=(e.clientY-8)+'px';});
}catch(e){}
</script>
""", height=0)

st.sidebar.title("🎓 EduVision")
st.sidebar.write("Smart Classroom Management")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "📋 Smart Attendance",
        "🚪 Smart Occupancy",
        "📊 Reports",
    ],
)

st.sidebar.divider()
st.sidebar.success("● System Online")


# ==========================================
# FILES / CONSTANTS
# ==========================================

STUDENTS_FILE = "data/students.csv"
ATTENDANCE_FILE = "data/attendance.csv"
STUDENT_IMAGES_DIR = "data/student_images"
DEMO_IMAGES_DIR = "data/demo_faces"

STUDENT_COLUMNS = ["student_id", "name"]
ATTENDANCE_COLUMNS = ["student_id", "name", "date", "time", "status"]

ENROLLMENT_SAMPLES = 30
FACE_MODEL = "Facenet512"
FACE_MATCH_THRESHOLD = 0.40
STABLE_CHECKS_REQUIRED = 2
RECOGNITION_EVERY_N_FRAMES = 10
BOX_MEMORY_FRAMES = 5

os.makedirs("data", exist_ok=True)
os.makedirs(DEMO_IMAGES_DIR, exist_ok=True)


# ==========================================
# SAFE CSV LOADER
# ==========================================

def load_csv_safely(file_path, required_columns):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame(columns=required_columns)

    try:
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip()

        for column in required_columns:
            if column not in data.columns:
                data[column] = ""

        return data[required_columns]

    except Exception:
        return pd.DataFrame(columns=required_columns)


# ==========================================
# FACE RECOGNITION
# ==========================================

face_detector = cv2.CascadeClassifier(
    os.path.join("assets", "haarcascade_frontalface_default.xml")
)

if face_detector.empty():
    st.error(
        "Face detector could not be loaded. "
        "Check assets/haarcascade_frontalface_default.xml"
    )
    st.stop()


def get_embedding(image):
    """Return a normalized Facenet512 embedding or None."""
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


def crop_face(image, box, padding=0.15):
    x, y, w, h = [int(v) for v in box]
    pad = int(padding * max(w, h))

    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(image.shape[1], x + w + pad)
    y2 = min(image.shape[0], y + h + pad)

    face = image[y1:y2, x1:x2]

    if face.size == 0:
        return None

    return face.copy()


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

            image = cv2.imread(os.path.join(folder, filename))

            if image is None:
                continue

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=7,
                minSize=(120, 120),
            )

            if len(faces) == 0:
                continue

            largest = max(faces, key=lambda box: box[2] * box[3])
            face = crop_face(image, largest)

            if face is None:
                continue

            embedding = get_embedding(face)

            if embedding is not None:
                embeddings.append(embedding)

        if embeddings:
            database[str(student_id)] = embeddings

    return database


def load_demo_embeddings():
    database = {}

    if not os.path.isdir(DEMO_IMAGES_DIR):
        return database

    for student_id in sorted(os.listdir(DEMO_IMAGES_DIR)):
        folder = os.path.join(DEMO_IMAGES_DIR, student_id)

        if not os.path.isdir(folder):
            continue

        embeddings = []

        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            image = cv2.imread(os.path.join(folder, filename))

            if image is None:
                continue

            embedding = get_embedding(image)

            if embedding is not None:
                embeddings.append(embedding)

        if embeddings:
            database[str(student_id)] = embeddings

    return database


student_names = {}
student_data = load_csv_safely(STUDENTS_FILE, STUDENT_COLUMNS)

for _, row in student_data.iterrows():
    student_id = str(row["student_id"]).strip()
    if student_id:
        student_names[student_id] = str(row["name"]).strip()

student_embeddings = load_student_embeddings()
student_embeddings.update(load_demo_embeddings())


# ==========================================
# AUTOMATIC ATTENDANCE
# ==========================================

attendance_lock = threading.Lock()


def mark_attendance(student_id, name):
    """Mark each student once per day."""
    with attendance_lock:
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        attendance_data = load_csv_safely(
            ATTENDANCE_FILE,
            ATTENDANCE_COLUMNS,
        )

        already_present = False

        if not attendance_data.empty:
            already_present = (
                (
                    attendance_data["student_id"]
                    .astype(str)
                    .str.strip()
                    == str(student_id).strip()
                )
                & (
                    attendance_data["date"]
                    .astype(str)
                    .str.strip()
                    == today_date
                )
            ).any()

        if already_present:
            return False

        new_record = pd.DataFrame(
            [
                {
                    "student_id": student_id,
                    "name": name,
                    "date": today_date,
                    "time": current_time,
                    "status": "Present",
                }
            ]
        )

        attendance_data = pd.concat(
            [attendance_data, new_record],
            ignore_index=True,
        )

        attendance_data.to_csv(ATTENDANCE_FILE, index=False)
        return True


# ==========================================
# 30-SAMPLE ENROLLMENT CAMERA
# ==========================================

class EnrollmentCamera(VideoProcessorBase):
    def __init__(self):
        self.samples = []
        self.frame_number = 0
        self.finished = False
        self.lock = threading.Lock()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.frame_number += 1

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=7,
            minSize=(120, 120),
        )

        if len(faces) == 1:
            x, y, w, h = [int(v) for v in faces[0]]

            cv2.rectangle(
                img,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3,
            )

            with self.lock:
                sample_count = len(self.samples)

                if (
                    not self.finished
                    and self.frame_number % 5 == 0
                    and sample_count < ENROLLMENT_SAMPLES
                ):
                    face = crop_face(img, (x, y, w, h))

                    if face is not None:
                        self.samples.append(face)

                    if len(self.samples) >= ENROLLMENT_SAMPLES:
                        self.finished = True

                sample_count = len(self.samples)
                finished = self.finished

            cv2.putText(
                img,
                f"Samples: {sample_count}/{ENROLLMENT_SAMPLES}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            if finished:
                cv2.putText(
                    img,
                    "30 SAMPLES CAPTURED",
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )

        elif len(faces) > 1:
            cv2.putText(
                img,
                "ONE PERSON ONLY",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),
                2,
            )

        else:
            cv2.putText(
                img,
                "LOOK AT CAMERA",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ==========================================
# ATTENDANCE CAMERA
# ==========================================

class AttendanceCamera(VideoProcessorBase):
    def __init__(self):
        self.frame_number = 0
        self.last_student = None
        self.stable_checks = 0

        self.cached_text = "Scanning..."
        self.cached_color = (0, 255, 255)
        self.cached_distance = None

        self.last_face_box = None
        self.missed_frames = 0
        self.unknown_checks = 0

    def recognize(self, face_bgr):
        query = get_embedding(face_bgr)

        if query is None or not student_embeddings:
            return None, None

        scores = []

        for student_id, embeddings in student_embeddings.items():
            distances = []

            for emb in embeddings:
                distance_value = float(
                    1.0 - np.dot(query, emb)
                )
                distances.append(distance_value)

            if not distances:
                continue

            distances.sort()

            # Do not trust one lucky reference photo.
            # Average up to the best 5 enrolled samples.
            sample_count = min(5, len(distances))
            score = float(
                np.mean(distances[:sample_count])
            )

            scores.append((score, student_id))

        if not scores:
            return None, None

        scores.sort(key=lambda item: item[0])
        best_distance, best_student = scores[0]

        # If two students are almost equally close, treat the face as unknown.
        if len(scores) > 1:
            second_distance = scores[1][0]
            if second_distance - best_distance < 0.03:
                return None, best_distance

        if best_distance <= FACE_MATCH_THRESHOLD:
            return best_student, best_distance

        return None, best_distance

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.frame_number += 1

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        detected_faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=7,
            minSize=(120, 120),
        )

        real_face_count = len(detected_faces)
        display_faces = detected_faces

        # More than one REAL detected face: do not recognize anyone.
        if real_face_count > 1:
            self.last_face_box = None
            self.missed_frames = 0
            self.last_student = None
            self.stable_checks = 0
            self.unknown_checks = 0
            self.cached_text = "ONE PERSON AT A TIME"
            self.cached_color = (0, 165, 255)
            self.cached_distance = None

        # Exactly one face: update the stable box.
        elif real_face_count == 1:
            current_box = detected_faces[0]

            if self.last_face_box is None:
                smooth_box = np.asarray(current_box, dtype=np.float32)
            else:
                previous = np.asarray(self.last_face_box, dtype=np.float32)
                current = np.asarray(current_box, dtype=np.float32)
                smooth_box = (0.70 * previous) + (0.30 * current)

            self.last_face_box = smooth_box.astype(int)
            self.missed_frames = 0
            display_faces = np.array([self.last_face_box])

        # Brief detector miss: keep the last box only for display.
        else:
            if (
                self.last_face_box is not None
                and self.missed_frames < BOX_MEMORY_FRAMES
            ):
                self.missed_frames += 1
                display_faces = np.array([self.last_face_box])
            else:
                self.last_face_box = None
                self.missed_frames = 0
                self.last_student = None
                self.stable_checks = 0
                self.unknown_checks = 0
                self.cached_text = "Scanning..."
                self.cached_color = (0, 255, 255)
                self.cached_distance = None
                display_faces = []

        # Recognition runs only when exactly one face was REALLY detected.
        if (
            real_face_count == 1
            and self.frame_number % RECOGNITION_EVERY_N_FRAMES == 0
        ):
            x, y, w, h = [int(v) for v in detected_faces[0]]
            face = crop_face(img, (x, y, w, h))

            if face is not None:
                student_id, distance = self.recognize(face)
                self.cached_distance = distance

                if student_id is not None:
                    self.unknown_checks = 0

                    if self.last_student == student_id:
                        self.stable_checks += 1
                    else:
                        self.last_student = student_id
                        self.stable_checks = 1

                    name = student_names.get(student_id, student_id)

                    if self.stable_checks >= STABLE_CHECKS_REQUIRED:
                        mark_attendance(student_id, name)
                        self.cached_text = f"{name} | PRESENT"
                    else:
                        self.cached_text = f"{name} | VERIFYING..."

                    self.cached_color = (0, 255, 0)

                else:
                    # Require two failed recognition checks before changing
                    # a previously stable label to UNKNOWN.
                    self.unknown_checks += 1

                    if self.unknown_checks >= 2:
                        self.last_student = None
                        self.stable_checks = 0
                        self.cached_text = "UNKNOWN"
                        self.cached_color = (0, 0, 255)

        for box in display_faces:
            x, y, w, h = [int(v) for v in box]

            cv2.rectangle(
                img,
                (x, y),
                (x + w, y + h),
                self.cached_color,
                3,
            )

            cv2.putText(
                img,
                self.cached_text,
                (x, max(y - 30, 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                self.cached_color,
                2,
            )

            if self.cached_distance is not None:
                cv2.putText(
                    img,
                    f"Match: {self.cached_distance:.3f}",
                    (x, max(y - 8, 50)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    self.cached_color,
                    2,
                )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24",
        )


# ==========================================
# SMART OCCUPANCY CAMERA
# ==========================================

@st.cache_resource
def load_occupancy_model():
    return YOLO("yolo11n.pt")


occupancy_model = load_occupancy_model()


class OccupancyCamera(VideoProcessorBase):
    def __init__(self):
        self.previous_positions = {}
        self.entered = 0
        self.exited = 0
        self.inside = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        height, width = img.shape[:2]
        line_x = width // 2

        results = occupancy_model.track(
            img,
            persist=True,
            classes=[0],
            conf=0.45,
            verbose=False,
        )

        people_detected = 0

        cv2.line(
            img,
            (line_x, 0),
            (line_x, height),
            (255, 255, 255),
            3,
        )

        cv2.putText(
            img,
            "DOOR LINE",
            (line_x + 10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
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

                    cv2.rectangle(
                        img,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2,
                    )

                    cv2.circle(
                        img,
                        (center_x, center_y),
                        5,
                        (0, 255, 255),
                        -1,
                    )

                    cv2.putText(
                        img,
                        f"PERSON {track_id}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

                    if track_id in self.previous_positions:
                        old_x = self.previous_positions[track_id]

                        if old_x < line_x <= center_x:
                            self.entered += 1
                            self.inside += 1

                        elif old_x > line_x >= center_x:
                            self.exited += 1
                            self.inside = max(
                                0,
                                self.inside - 1,
                            )

                    self.previous_positions[track_id] = center_x

        cv2.putText(
            img,
            f"Detected: {people_detected}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            img,
            f"Entered: {self.entered}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            img,
            f"Exited: {self.exited}",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2,
        )

        cv2.putText(
            img,
            f"Inside: {self.inside}",
            (20, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
        )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24",
        )


# ==========================================
# CURRENT DATABASE / STATISTICS
# ==========================================

students = load_csv_safely(
    STUDENTS_FILE,
    STUDENT_COLUMNS,
)

attendance = load_csv_safely(
    ATTENDANCE_FILE,
    ATTENDANCE_COLUMNS,
)

today = datetime.now().strftime("%Y-%m-%d")

if not attendance.empty:
    today_attendance = attendance[
        attendance["date"].astype(str).str.strip() == today
    ]
else:
    today_attendance = pd.DataFrame(
        columns=ATTENDANCE_COLUMNS
    )

total_students = len(students)
present_today = (
    today_attendance["student_id"].nunique()
    if not today_attendance.empty
    else 0
)
absent_today = max(total_students - present_today, 0)


# ==========================================
# SMART ATTENDANCE PAGE
# ==========================================

if page == "📋 Smart Attendance":
    st.title("📋 EduVision Smart Attendance")

    st.subheader("📸 Register Demo Student")

    demo_id = st.text_input(
        "Student ID",
        placeholder="Example: DEMO001",
    )

    demo_name = st.text_input(
        "Student Name",
        placeholder="Enter name",
    )

    st.write("### 🎥 30-Sample Face Registration")

    st.info(
        "1. Enter the ID and name. "
        "2. Press START. "
        "3. Keep only one person in view and slowly look "
        "left, right, up and down. "
        "4. Wait for 30/30, then press Save."
    )

    enrollment_ctx = webrtc_streamer(
        key="eduvision-enrollment-camera",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=EnrollmentCamera,
        media_stream_constraints={
            "video": True,
            "audio": False,
        },
        async_processing=True,
    )

    if st.button("💾 Save 30 Face Samples"):
        processor = enrollment_ctx.video_processor

        if not demo_id.strip() or not demo_name.strip():
            st.warning(
                "Enter Student ID and Student Name first."
            )

        elif processor is None:
            st.warning(
                "Press START on the registration camera first."
            )

        else:
            with processor.lock:
                samples = [
                    sample.copy()
                    for sample in processor.samples[
                        :ENROLLMENT_SAMPLES
                    ]
                ]

            if len(samples) < ENROLLMENT_SAMPLES:
                st.warning(
                    f"Only {len(samples)}/{ENROLLMENT_SAMPLES} "
                    "samples captured."
                )

            else:
                safe_id = "".join(
                    c
                    for c in demo_id.strip()
                    if c.isalnum() or c in ("-", "_")
                )

                if not safe_id:
                    st.error(
                        "Use letters or numbers in the Student ID."
                    )

                else:
                    student_folder = os.path.join(
                        DEMO_IMAGES_DIR,
                        safe_id,
                    )

                    os.makedirs(
                        student_folder,
                        exist_ok=True,
                    )

                    for old_file in os.listdir(student_folder):
                        if old_file.lower().endswith(
                            (".jpg", ".jpeg", ".png")
                        ):
                            try:
                                os.remove(
                                    os.path.join(
                                        student_folder,
                                        old_file,
                                    )
                                )
                            except OSError:
                                pass

                    for i, face in enumerate(
                        samples,
                        start=1,
                    ):
                        cv2.imwrite(
                            os.path.join(
                                student_folder,
                                f"{i:02d}.jpg",
                            ),
                            face,
                        )

                    with st.spinner(
                        "Creating face data from the 30 samples..."
                    ):
                        embeddings = []

                        for face in samples:
                            embedding = get_embedding(face)

                            if embedding is not None:
                                embeddings.append(embedding)

                    if not embeddings:
                        st.error(
                            "Could not create face data. "
                            "Please register again in better lighting."
                        )

                    else:
                        student_embeddings[safe_id] = embeddings
                        student_names[safe_id] = demo_name.strip()

                        students_df = load_csv_safely(
                            STUDENTS_FILE,
                            STUDENT_COLUMNS,
                        )

                        students_df = students_df[
                            students_df["student_id"]
                            .astype(str)
                            .str.strip()
                            != safe_id
                        ]

                        new_student = pd.DataFrame(
                            [
                                {
                                    "student_id": safe_id,
                                    "name": demo_name.strip(),
                                }
                            ]
                        )

                        students_df = pd.concat(
                            [students_df, new_student],
                            ignore_index=True,
                        )

                        students_df.to_csv(
                            STUDENTS_FILE,
                            index=False,
                        )

                        st.success(
                            f"✅ {demo_name.strip()} registered "
                            f"with {len(embeddings)} usable samples!"
                        )

                        st.info(
                            "STOP the registration camera before "
                            "starting the attendance camera."
                        )

    st.divider()

    st.subheader("✅ Automatic Attendance")
    st.write(
        "Stop the registration camera first, then press START below."
    )

    webrtc_streamer(
        key="eduvision-attendance-camera",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=AttendanceCamera,
        media_stream_constraints={
            "video": True,
            "audio": False,
        },
        async_processing=True,
    )

    st.info(
        "EduVision recognizes one person at a time. "
        "Attendance is recorded once per student per day."
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
            "audio": False,
        },
        async_processing=True,
    )

    st.success("🟢 Smart Occupancy System Ready")
    st.stop()


# ==========================================
# REPORTS PAGE
# ==========================================

if page == "📊 Reports":
    st.title("📊 EduVision Reports")

    if st.button("🗑️ Clear Today's Attendance"):
        df = load_csv_safely(
            ATTENDANCE_FILE,
            ATTENDANCE_COLUMNS,
        )

        if not df.empty:
            df = df[
                df["date"].astype(str).str.strip() != today
            ]
            df.to_csv(
                ATTENDANCE_FILE,
                index=False,
            )

        st.success("✅ Today's attendance cleared!")
        st.rerun()

    st.write(
        "View and analyze attendance records recorded by EduVision."
    )

    st.divider()

    total_records = len(attendance)

    if not attendance.empty:
        unique_students = attendance[
            "student_id"
        ].nunique()
        total_days = attendance["date"].nunique()
    else:
        unique_students = 0
        total_days = 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📋 Attendance Records",
            total_records,
        )

    with col2:
        st.metric(
            "👨‍🎓 Students Recorded",
            unique_students,
        )

    with col3:
        st.metric(
            "📅 School Days Recorded",
            total_days,
        )

    st.divider()
    st.subheader("📋 Attendance History")

    if not attendance.empty:
        st.dataframe(
            attendance[
                [
                    "student_id",
                    "name",
                    "date",
                    "time",
                    "status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No attendance records are available yet."
        )

    st.divider()
    st.subheader("👨‍🎓 Student Attendance Summary")

    if not attendance.empty:
        student_summary = (
            attendance.groupby(
                ["student_id", "name"]
            )
            .size()
            .reset_index(name="Days Present")
        )

        st.dataframe(
            student_summary,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "Attendance will appear here after "
            "students are marked present."
        )

    st.divider()
    st.caption(
        "EduVision • Attendance Reporting System"
    )
    st.stop()


# ==========================================
# DASHBOARD
# ==========================================

current_time = datetime.now().strftime("%d %B %Y • %I:%M %p")
st.markdown(f"""
<div class="ev-hero">
<div class="ev-kicker">✦ AI CLASSROOM OPERATING SYSTEM</div>
<div class="ev-title">EduVision</div>
<div class="ev-sub">AI-powered attendance, classroom occupancy and reporting in one premium smart-classroom dashboard.</div>
<div class="ev-live"><span class="ev-dot"></span>SYSTEM ONLINE &nbsp; • &nbsp; {current_time}</div>
</div>
""", unsafe_allow_html=True)

st.header("📊 Today's Classroom Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "👨‍🎓 Total Students",
        total_students,
    )

with col2:
    st.metric(
        "✅ Present",
        present_today,
    )

with col3:
    st.metric(
        "❌ Absent",
        absent_today,
    )

with col4:
    st.metric(
        "🚪 Room Occupancy",
        "Not Active",
    )

st.divider()

st.header("🧠 EduVision AI Systems")

left, right = st.columns(2)

with left:
    st.subheader("📋 Smart Attendance")
    st.write(
        "Recognizes enrolled students and "
        "records their attendance automatically."
    )
    st.write("✅ Face Detection")
    st.write("✅ 30-Sample Student Recognition")
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

st.header("📋 Today's Attendance")

if not today_attendance.empty:
    st.dataframe(
        today_attendance[
            [
                "student_id",
                "name",
                "time",
                "status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "No attendance has been recorded today."
    )

st.divider()

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

st.caption(
    "EduVision • AI-Powered Smart Classroom Management"
)

import json
import threading
from datetime import datetime
from pathlib import Path

import av
import cv2
import pandas as pd
import streamlit as st

from streamlit_webrtc import (
    VideoProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "data" / "model" / "face_model.yml"
LABEL_PATH = BASE_DIR / "data" / "model" / "labels.json"
STUDENTS_PATH = BASE_DIR / "data" / "students.csv"
ATTENDANCE_PATH = BASE_DIR / "data" / "attendance.csv"

STUDENT_COLUMNS = [
    "student_id",
    "name",
    "class_name",
    "roll_no",
    "status",
]

ATTENDANCE_COLUMNS = [
    "student_id",
    "name",
    "class_name",
    "date",
    "time",
    "status",
]


# ============================================================
# GLOBAL DATA
# ============================================================

students = {}
label_map = {}

recognizer = None
face_detector = None

attendance_lock = threading.Lock()


# ============================================================
# LOAD STUDENTS
# ============================================================

def load_student_data():

    global students

    students = {}

    if not STUDENTS_PATH.exists():
        return False

    try:

        df = pd.read_csv(
            STUDENTS_PATH,
            dtype=str
        ).fillna("")

        # Support older CSV files
        if (
            "class" in df.columns
            and
            "class_name" not in df.columns
        ):
            df = df.rename(
                columns={
                    "class": "class_name"
                }
            )

        if (
            "student_name" in df.columns
            and
            "name" not in df.columns
        ):
            df = df.rename(
                columns={
                    "student_name": "name"
                }
            )

        for column in STUDENT_COLUMNS:

            if column not in df.columns:
                df[column] = ""

        for _, row in df.iterrows():

            student_id = str(
                row.get(
                    "student_id",
                    ""
                )
            ).strip()

            if not student_id:
                continue

            students[student_id] = {
                "name": str(
                    row.get(
                        "name",
                        student_id
                    )
                ).strip(),

                "class_name": str(
                    row.get(
                        "class_name",
                        ""
                    )
                ).strip()
            }

        return True

    except Exception as error:

        print(
            "Student loading error:",
            error
        )

        return False


# ============================================================
# LOAD LABEL MAP
# ============================================================

def load_labels():

    global label_map

    label_map = {}

    if not LABEL_PATH.exists():
        return False

    try:

        with open(
            LABEL_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            raw_labels = json.load(
                file
            )

        label_map = {
            int(label): str(student_id)
            for label, student_id
            in raw_labels.items()
        }

        return True

    except Exception as error:

        print(
            "Label loading error:",
            error
        )

        return False


# ============================================================
# LOAD FACE MODEL
# ============================================================

def load_face_model():

    global recognizer
    global face_detector

    recognizer = None
    face_detector = None

    # cv2.face comes from opencv-contrib
    if not hasattr(
        cv2,
        "face"
    ):

        return False

    if not MODEL_PATH.exists():

        return False

    try:

        recognizer = (
            cv2.face
            .LBPHFaceRecognizer_create()
        )

        recognizer.read(
            str(MODEL_PATH)
        )

        # First try our assets folder
        cascade_path = (
            BASE_DIR
            / "assets"
            / "haarcascade_frontalface_default.xml"
        )

        if cascade_path.exists():

            face_detector = (
                cv2.CascadeClassifier(
                    str(cascade_path)
                )
            )

        else:

            # Fallback to OpenCV's built-in cascade
            face_detector = (
                cv2.CascadeClassifier(
                    cv2.data.haarcascades
                    +
                    "haarcascade_frontalface_default.xml"
                )
            )

        if face_detector.empty():

            recognizer = None
            face_detector = None

            return False

        return True

    except Exception as error:

        print(
            "Face model loading error:",
            error
        )

        recognizer = None
        face_detector = None

        return False


# ============================================================
# ATTENDANCE FILE
# ============================================================

def ensure_attendance_file():

    ATTENDANCE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not ATTENDANCE_PATH.exists():

        pd.DataFrame(
            columns=ATTENDANCE_COLUMNS
        ).to_csv(
            ATTENDANCE_PATH,
            index=False
        )

        return

    try:

        df = pd.read_csv(
            ATTENDANCE_PATH,
            dtype=str
        ).fillna("")

        # Support old attendance format
        if (
            "class" in df.columns
            and
            "class_name" not in df.columns
        ):
            df = df.rename(
                columns={
                    "class": "class_name"
                }
            )

        for column in ATTENDANCE_COLUMNS:

            if column not in df.columns:
                df[column] = ""

        df[
            ATTENDANCE_COLUMNS
        ].to_csv(
            ATTENDANCE_PATH,
            index=False
        )

    except Exception:

        pd.DataFrame(
            columns=ATTENDANCE_COLUMNS
        ).to_csv(
            ATTENDANCE_PATH,
            index=False
        )


# ============================================================
# MARK ATTENDANCE
# ============================================================

def mark_attendance(
    student_id,
    name,
    class_name=""
):

    ensure_attendance_file()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    with attendance_lock:

        try:

            attendance = pd.read_csv(
                ATTENDANCE_PATH,
                dtype=str
            ).fillna("")

        except Exception:

            attendance = pd.DataFrame(
                columns=ATTENDANCE_COLUMNS
            )

        for column in ATTENDANCE_COLUMNS:

            if column not in attendance.columns:
                attendance[column] = ""

        # Do not mark same student twice today
        if not attendance.empty:

            already_marked = (
                (
                    attendance[
                        "student_id"
                    ]
                    ==
                    str(student_id)
                )
                &
                (
                    attendance[
                        "date"
                    ]
                    ==
                    today
                )
            ).any()

            if already_marked:

                return False

        now = datetime.now()

        new_record = pd.DataFrame(
            [
                {
                    "student_id":
                        str(student_id),

                    "name":
                        str(name),

                    "class_name":
                        str(class_name),

                    "date":
                        today,

                    "time":
                        now.strftime(
                            "%H:%M:%S"
                        ),

                    "status":
                        "Present"
                }
            ]
        )

        attendance = pd.concat(
            [
                attendance[
                    ATTENDANCE_COLUMNS
                ],
                new_record
            ],
            ignore_index=True
        )

        attendance.to_csv(
            ATTENDANCE_PATH,
            index=False
        )

        print(
            f"Attendance marked: "
            f"{student_id} - {name}"
        )

        return True


# ============================================================
# VIDEO PROCESSOR
# ============================================================

class AttendanceProcessor(
    VideoProcessorBase
):

    def __init__(self):

        # Number of consecutive successful
        # recognitions for each student
        self.recognition_counts = {}

        # Stops repeated writes during same
        # camera session
        self.marked_this_session = set()


    def recv(
        self,
        frame
    ):

        img = frame.to_ndarray(
            format="bgr24"
        )

        if (
            recognizer is None
            or
            face_detector is None
        ):

            cv2.putText(
                img,
                "FACE MODEL NOT READY",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            return (
                av.VideoFrame
                .from_ndarray(
                    img,
                    format="bgr24"
                )
            )

        # Convert camera frame to grayscale
        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        # Detect faces
        faces = (
            face_detector
            .detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=6,
                minSize=(
                    100,
                    100
                )
            )
        )

        currently_seen = set()

        for (
            x,
            y,
            w,
            h
        ) in faces:

            face = gray[
                y:y + h,
                x:x + w
            ]

            face = cv2.resize(
                face,
                (
                    200,
                    200
                )
            )

            try:

                label, confidence = (
                    recognizer.predict(
                        face
                    )
                )

            except Exception:

                continue


            # ==================================================
            # LBPH RECOGNITION
            # LOWER distance = better match
            # ==================================================

            recognized = (
                confidence < 45
                and
                label in label_map
            )


            if recognized:

                student_id = (
                    label_map[
                        label
                    ]
                )

                student = students.get(
                    student_id,
                    {}
                )

                name = student.get(
                    "name",
                    student_id
                )

                class_name = student.get(
                    "class_name",
                    ""
                )

                display_name = name

                box_color = (
                    0,
                    255,
                    0
                )

                currently_seen.add(
                    student_id
                )


                # ==============================================
                # COUNT SUCCESSFUL FRAMES
                # ==============================================

                count = (
                    self.recognition_counts
                    .get(
                        student_id,
                        0
                    )
                    +
                    1
                )

                self.recognition_counts[
                    student_id
                ] = count


                # ==============================================
                # AUTO MARK AFTER 10 RECOGNITIONS
                # ==============================================

                if (
                    count >= 10
                    and
                    student_id
                    not in
                    self.marked_this_session
                ):

                    mark_attendance(
                        student_id,
                        name,
                        class_name
                    )

                    self.marked_this_session.add(
                        student_id
                    )


                # Student ID under box
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

                display_name = (
                    "UNKNOWN"
                )

                box_color = (
                    0,
                    0,
                    255
                )


            # ==================================================
            # FACE BOX
            # ==================================================

            cv2.rectangle(
                img,
                (
                    x,
                    y
                ),
                (
                    x + w,
                    y + h
                ),
                box_color,
                3
            )


            # ==================================================
            # NAME
            # ==================================================

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


            # ==================================================
            # DISTANCE
            # ==================================================

            cv2.putText(
                img,
                f"Distance: {confidence:.1f}",
                (
                    x,
                    y + h + 48
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                box_color,
                1
            )


        # Reset recognition counter when
        # student disappears from camera
        for student_id in list(
            self.recognition_counts.keys()
        ):

            if (
                student_id
                not in
                currently_seen
            ):

                self.recognition_counts[
                    student_id
                ] = 0


        return (
            av.VideoFrame
            .from_ndarray(
                img,
                format="bgr24"
            )
        )


# ============================================================
# TODAY'S ATTENDANCE
# ============================================================

def show_today_attendance():

    ensure_attendance_file()

    try:

        attendance = pd.read_csv(
            ATTENDANCE_PATH,
            dtype=str
        ).fillna("")

    except Exception as error:

        st.error(
            f"Could not load attendance: {error}"
        )

        return


    if attendance.empty:

        st.info(
            "No attendance recorded yet."
        )

        return


    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    today_data = attendance[
        attendance[
            "date"
        ]
        ==
        today
    ]


    present_count = len(
        today_data[
            today_data[
                "status"
            ]
            ==
            "Present"
        ]
    )


    st.metric(
        "✅ Students Present Today",
        present_count
    )


    if today_data.empty:

        st.info(
            "No attendance recorded today."
        )

    else:

        st.dataframe(
            today_data,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# MAIN ATTENDANCE PAGE
# ============================================================

def render_page():

    load_student_data()

    labels_ready = (
        load_labels()
    )

    model_ready = (
        load_face_model()
    )

    ensure_attendance_file()


    st.subheader(
        "🤖 Automatic Face Recognition"
    )

    st.write(
        "Look at the camera. EduVision recognizes "
        "registered students and automatically marks "
        "them present."
    )


    st.warning(
        "⚠️ Face recognition can make mistakes. "
        "Teachers should review the attendance results."
    )


    # ========================================================
    # STUDENT CHECK
    # ========================================================

    if not STUDENTS_PATH.exists():

        st.error(
            "students.csv was not found."
        )

        return


    if not students:

        st.warning(
            "No registered students found."
        )

        return


    # ========================================================
    # LABEL CHECK
    # ========================================================

    if not labels_ready:

        st.error(
            "Face labels were not found. "
            "Train student faces first."
        )

        return


    # ========================================================
    # MODEL CHECK
    # ========================================================

    if not model_ready:

        if not hasattr(
            cv2,
            "face"
        ):

            st.error(
                "OpenCV face recognition is unavailable."
            )

            st.info(
                "requirements.txt must contain "
                "opencv-contrib-python-headless."
            )

        elif not MODEL_PATH.exists():

            st.error(
                "face_model.yml was not found."
            )

            st.info(
                "Train the registered student faces first."
            )

        else:

            st.error(
                "Face recognition model could not be loaded."
            )

        return


    # ========================================================
    # CAMERA
    # ========================================================

    st.subheader(
        "🎥 Scan Class"
    )

    st.info(
        "Press START and allow camera permission."
    )


    try:

        webrtc_streamer(

            key="eduvision-attendance-camera",

            mode=WebRtcMode.SENDRECV,

            video_processor_factory=AttendanceProcessor,

            media_stream_constraints={
                "video": True,
                "audio": False
            },

            async_processing=True
        )

    except Exception as error:

        st.error(
            "Camera could not start."
        )

        st.info(
            "Allow camera permission in your browser "
            "and refresh EduVision."
        )

        st.code(
            str(error)
        )


    # ========================================================
    # ATTENDANCE TABLE
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Today's Attendance"
    )

    show_today_attendance()


# ============================================================
# RUN DIRECTLY FOR TESTING
# ============================================================

if __name__ == "__main__":

    st.set_page_config(
        page_title="EduVision Attendance",
        page_icon="🎓",
        layout="wide"
    )

    render_page()

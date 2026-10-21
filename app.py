import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# EDVISION - LIGHTWEIGHT VERSION
# Super Admin + Teacher
# No School Admin / Student Login / WebRTC
# ============================================================

st.set_page_config(
    page_title="EduVision",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# FILES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

STUDENTS_FILE = DATA_DIR / "students.csv"
ATTENDANCE_FILE = DATA_DIR / "attendance.csv"
USERS_FILE = DATA_DIR / "users.json"


# Demo login
ADMIN_ID = os.getenv("EDUVISION_ADMIN_ID", "12126")
ADMIN_PASSWORD = os.getenv("EDUVISION_ADMIN_PASSWORD", "12126")


# ============================================================
# DATA
# ============================================================

def password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def setup_files():

    if not STUDENTS_FILE.exists():
        pd.DataFrame(
            columns=[
                "student_id",
                "name",
                "class_name",
                "roll_no",
                "status"
            ]
        ).to_csv(STUDENTS_FILE, index=False)

    if not ATTENDANCE_FILE.exists():
        pd.DataFrame(
            columns=[
                "student_id",
                "name",
                "class_name",
                "date",
                "time",
                "status"
            ]
        ).to_csv(ATTENDANCE_FILE, index=False)

    if not USERS_FILE.exists():

        data = {
            "admin": {
                "id": ADMIN_ID,
                "password_hash": password_hash(ADMIN_PASSWORD)
            },
            "teachers": {}
        }

        USERS_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )


def load_users():

    try:
        return json.loads(
            USERS_FILE.read_text(encoding="utf-8")
        )

    except Exception:

        return {
            "admin": {
                "id": ADMIN_ID,
                "password_hash": password_hash(ADMIN_PASSWORD)
            },
            "teachers": {}
        }


def save_users(data):

    USERS_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )


def load_students():

    try:
        return pd.read_csv(
            STUDENTS_FILE,
            dtype=str
        ).fillna("")

    except Exception:

        return pd.DataFrame(
            columns=[
                "student_id",
                "name",
                "class_name",
                "roll_no",
                "status"
            ]
        )


def save_students(df):

    df.to_csv(
        STUDENTS_FILE,
        index=False
    )


def load_attendance():

    try:
        return pd.read_csv(
            ATTENDANCE_FILE,
            dtype=str
        ).fillna("")

    except Exception:

        return pd.DataFrame(
            columns=[
                "student_id",
                "name",
                "class_name",
                "date",
                "time",
                "status"
            ]
        )


def save_attendance(df):

    df.to_csv(
        ATTENDANCE_FILE,
        index=False
    )


setup_files()


# ============================================================
# MAGIC UI INSPIRED CSS
# ============================================================

st.markdown(
    """
<style>

:root {
    --bg:#020617;
    --panel:#0f172a;
    --panel2:#111827;
    --blue:#3b82f6;
    --cyan:#22d3ee;
    --purple:#8b5cf6;
    --pink:#ec4899;
    --text:#f8fafc;
    --muted:#94a3b8;
}


/* BACKGROUND */

.stApp {

    color:white;

    background:

    radial-gradient(
        circle at 15% 20%,
        rgba(139,92,246,.18),
        transparent 25%
    ),

    radial-gradient(
        circle at 85% 70%,
        rgba(34,211,238,.15),
        transparent 30%
    ),

    linear-gradient(
        135deg,
        #020617,
        #071426,
        #020617
    );

    background-size:200% 200%;

    animation:bgMove 14s ease infinite;
}


@keyframes bgMove {

    0%,100% {
        background-position:0% 50%;
    }

    50% {
        background-position:100% 50%;
    }

}


/* MAIN WIDTH */

.block-container {

    max-width:1400px;

    padding-top:1.2rem;

}


/* HERO */

.ev-hero {

    position:relative;

    overflow:hidden;

    padding:38px 42px;

    margin-bottom:25px;

    border-radius:30px;

    border:1px solid rgba(34,211,238,.18);

    background:

    linear-gradient(
        125deg,
        rgba(15,23,42,.96),
        rgba(15,23,42,.72)
    );

    box-shadow:
        0 25px 70px rgba(0,0,0,.4);

}


/* LIGHT RAY */

.ev-hero:after {

    content:"";

    position:absolute;

    inset:-100% -50%;

    background:

    linear-gradient(
        110deg,
        transparent 43%,
        rgba(255,255,255,.10) 50%,
        transparent 57%
    );

    animation:shine 7s linear infinite;

    pointer-events:none;

}


@keyframes shine {

    0% {
        transform:translateX(-40%);
    }

    100% {
        transform:translateX(40%);
    }

}


/* TITLE */

.ev-kicker {

    color:#67e8f9;

    font-size:.78rem;

    font-weight:900;

    letter-spacing:.18em;

}


.ev-title {

    font-size:3.5rem;

    font-weight:950;

    letter-spacing:-2px;

    margin-top:6px;

    background:

    linear-gradient(
        90deg,
        #ffffff,
        #a78bfa,
        #22d3ee
    );

    background-size:200%;

    -webkit-background-clip:text;

    color:transparent;

    animation:titleMove 5s linear infinite;

}


@keyframes titleMove {

    to {
        background-position:200%;
    }

}


.ev-sub {

    color:#cbd5e1;

    max-width:750px;

    margin-top:12px;

    font-size:1.05rem;

}


/* STATUS */

.ev-online {

    display:inline-flex;

    align-items:center;

    margin-top:18px;

    padding:7px 12px;

    border-radius:999px;

    background:rgba(34,197,94,.08);

    border:1px solid rgba(34,197,94,.20);

    color:#bbf7d0;

}


.ev-dot {

    width:8px;

    height:8px;

    margin-right:8px;

    border-radius:50%;

    background:#22c55e;

    box-shadow:
        0 0 15px #22c55e;

}


/* INPUTS */

div[data-baseweb="input"] {

    background:#ffffff !important;

    border-radius:12px !important;

}


div[data-baseweb="input"] input {

    color:#000000 !important;

    background:#ffffff !important;

    -webkit-text-fill-color:#000000 !important;

}


input[type="text"],
input[type="password"],
input[type="number"],
input[type="email"] {

    color:#000000 !important;

    background:#ffffff !important;

    -webkit-text-fill-color:#000000 !important;

}


input::placeholder {

    color:#64748b !important;

    -webkit-text-fill-color:#64748b !important;

}


/* SELECT BOX */

div[data-baseweb="select"] > div {

    background:#ffffff !important;

    color:#000000 !important;

    border-radius:12px !important;

}


div[data-baseweb="select"] span {

    color:#000000 !important;

}


ul[role="listbox"] {

    background:#ffffff !important;

}


li[role="option"] {

    color:#000000 !important;

    background:#ffffff !important;

}


li[role="option"]:hover {

    background:#e2e8f0 !important;

}


/* BUTTON - SHIMMER STYLE */

div.stButton > button {

    width:100%;

    position:relative;

    overflow:hidden;

    color:white !important;

    font-weight:850;

    border-radius:14px;

    border:

    1px solid rgba(
        34,
        211,
        238,
        .40
    );

    background:

    linear-gradient(
        90deg,
        #2563eb,
        #7c3aed,
        #0891b2
    );

    background-size:200%;

    box-shadow:

        0 8px 25px
        rgba(37,99,235,.18);

    transition:.2s;

}


div.stButton > button:hover {

    transform:

        translateY(-2px)
        scale(1.025);

    background-position:100%;

    border-color:#67e8f9;

    box-shadow:

        0 15px 35px
        rgba(34,211,238,.20);

}


/* METRIC MAGIC CARDS */

[data-testid="stMetric"] {

    padding:18px;

    border-radius:20px;

    background:

    linear-gradient(
        145deg,
        rgba(15,23,42,.95),
        rgba(30,41,59,.72)
    );

    border:

    1px solid
    rgba(139,92,246,.18);

    box-shadow:

    0 12px 30px
    rgba(0,0,0,.25);

    transition:.2s;

}


[data-testid="stMetric"]:hover {

    transform:translateY(-4px);

    border-color:

    rgba(34,211,238,.50);

}


[data-testid="stMetricValue"] {

    color:white;

}


/* SIDEBAR */

[data-testid="stSidebar"] {

    background:

    rgba(2,6,23,.97);

    border-right:

    1px solid
    rgba(34,211,238,.12);

}


[data-testid="stSidebar"] * {

    color:white;

}


/* CAMERA */

[data-testid="stCameraInput"] {

    padding:12px;

    border-radius:20px;

    border:

    1px solid
    rgba(34,211,238,.25);

    background:

    rgba(15,23,42,.80);

}


/* DATAFRAME */

[data-testid="stDataFrame"] {

    border-radius:16px;

    overflow:hidden;

}


/* TABS */

.stTabs [data-baseweb="tab"] {

    background:#111827;

    border-radius:12px;

    color:white;

    padding:8px 18px;

}


/* ALERTS */

[data-testid="stAlert"] {

    border-radius:14px;

}


/* LABELS */

label {

    color:white !important;

}


/* HIDE STREAMLIT FOOTER */

footer {

    visibility:hidden;

}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None


# ============================================================
# LOGIN
# ============================================================

def login_page():

    st.markdown(
        """
        <div class="ev-hero">

            <div class="ev-kicker">
                AI • SMART CLASSROOM
            </div>

            <div class="ev-title">
                EduVision
            </div>

            <div class="ev-sub">
                Smarter classrooms through fast attendance,
                classroom monitoring and simple management.
            </div>

            <div class="ev-online">
                <span class="ev-dot"></span>
                System Online
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(
        [1, 1.15, 1]
    )

    with c2:

        st.markdown(
            "## ✨ Welcome Back"
        )

        role = st.selectbox(
            "Login as",
            [
                "Super Admin",
                "Teacher"
            ]
        )

        user_id = st.text_input(
            "ID"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "✨ Sign In",
            use_container_width=True
        ):

            users = load_users()

            valid = False

            if role == "Super Admin":

                admin = users.get(
                    "admin",
                    {}
                )

                valid = (

                    user_id
                    ==
                    admin.get("id")

                    and

                    password_hash(password)
                    ==
                    admin.get(
                        "password_hash"
                    )

                )

            else:

                teacher = (
                    users
                    .get(
                        "teachers",
                        {}
                    )
                    .get(
                        user_id,
                        {}
                    )
                )

                valid = (

                    bool(teacher)

                    and

                    teacher.get(
                        "enabled",
                        True
                    )

                    and

                    password_hash(password)
                    ==
                    teacher.get(
                        "password_hash"
                    )

                )

            if valid:

                st.session_state.logged_in = True

                st.session_state.role = role

                st.session_state.user_id = user_id

                st.rerun()

            else:

                st.error(
                    "Incorrect ID or password."
                )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    students = load_students()

    attendance = load_attendance()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if not attendance.empty:

        today_data = attendance[
            attendance["date"] == today
        ]

    else:

        today_data = attendance

    present = 0

    if not today_data.empty:

        present = len(
            today_data[
                today_data["status"]
                ==
                "Present"
            ]
        )

    st.markdown(
        """
        <div class="ev-hero">

            <div class="ev-kicker">
                SMART CLASSROOM MANAGEMENT
            </div>

            <div class="ev-title">
                EduVision
            </div>

            <div class="ev-sub">
                Your lightweight classroom management dashboard.
            </div>

            <div class="ev-online">
                <span class="ev-dot"></span>
                System Online
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "🎓 Students",
        len(students)
    )

    b.metric(
        "✅ Present Today",
        present
    )

    c.metric(
        "📋 Attendance Records",
        len(attendance)
    )

    d.metric(
        "👤 Access",
        st.session_state.role
    )

    st.markdown(
        "## ⚡ Quick Actions"
    )

    st.info(
        "Use the sidebar to manage students, "
        "open the camera, take attendance and manage teachers."
    )


# ============================================================
# STUDENTS
# ============================================================

def students_page():

    students = load_students()

    st.markdown(
        "## 🎓 Student Management"
    )

    if (
        st.session_state.role
        ==
        "Super Admin"
    ):

        with st.expander(
            "➕ Add New Student"
        ):

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID"
                )

                name = st.text_input(
                    "Full Name"
                )

            with c2:

                class_name = st.text_input(
                    "Class"
                )

                roll_no = st.text_input(
                    "Roll Number"
                )

            if st.button(
                "✨ Add Student"
            ):

                student_id = (
                    student_id.strip()
                )

                name = name.strip()

                if not student_id:

                    st.error(
                        "Enter Student ID."
                    )

                elif not name:

                    st.error(
                        "Enter student name."
                    )

                elif (
                    not students.empty
                    and
                    student_id
                    in students[
                        "student_id"
                    ].tolist()
                ):

                    st.error(
                        "Student ID already exists."
                    )

                else:

                    new_student = pd.DataFrame(
                        [
                            {
                                "student_id":
                                    student_id,

                                "name":
                                    name,

                                "class_name":
                                    class_name,

                                "roll_no":
                                    roll_no,

                                "status":
                                    "Active"
                            }
                        ]
                    )

                    students = pd.concat(
                        [
                            students,
                            new_student
                        ],
                        ignore_index=True
                    )

                    save_students(
                        students
                    )

                    st.success(
                        "Student added successfully."
                    )

                    st.rerun()

    st.markdown(
        "### Student List"
    )

    if students.empty:

        st.info(
            "No students added yet."
        )

    else:

        st.dataframe(
            students,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# CAMERA
# ============================================================

def camera_page():

    st.markdown(
        "## 📷 Classroom Camera"
    )

    st.caption(
        "Click the camera button below and allow camera permission in your browser."
    )

    st.info(
        "This lightweight version uses Streamlit's built-in camera "
        "instead of WebRTC, removing the PyArrow/WebRTC crash."
    )

    try:

        picture = st.camera_input(
            "📷 Open Camera / Capture"
        )

        if picture is not None:

            st.success(
                "✅ Camera is working!"
            )

            st.image(
                picture,
                caption="Latest Capture",
                use_container_width=True
            )

            st.session_state[
                "latest_camera_photo"
            ] = picture.getvalue()

    except Exception as error:

        st.error(
            "Camera could not open."
        )

        st.warning(
            "Allow Camera permission for this website "
            "in your browser and refresh the page."
        )


# ============================================================
# ATTENDANCE
# ============================================================

def attendance_page():

    students = load_students()

    attendance = load_attendance()

    st.markdown(
        "## ✅ Smart Attendance"
    )

    tab1, tab2 = st.tabs(
        [
            "📷 Scan / Camera",
            "✋ Manual Attendance"
        ]
    )

    with tab1:

        camera_page()

        st.caption(
            "For the presentation, capture the student first, "
            "then confirm their attendance from the Manual Attendance tab."
        )

    with tab2:

        if students.empty:

            st.warning(
                "Add at least one student first."
            )

            return

        options = {}

        for _, student in students.iterrows():

            label = (
                f"{student['student_id']} — "
                f"{student['name']} — "
                f"{student['class_name']}"
            )

            options[label] = student

        selected = st.selectbox(
            "Select Student",
            list(options.keys())
        )

        status = st.selectbox(
            "Attendance Status",
            [
                "Present",
                "Late",
                "Absent"
            ]
        )

        if st.button(
            "✅ Save Attendance"
        ):

            student = options[
                selected
            ]

            now = datetime.now()

            date = now.strftime(
                "%Y-%m-%d"
            )

            time = now.strftime(
                "%H:%M:%S"
            )

            existing = (

                attendance[
                    (
                        attendance[
                            "student_id"
                        ]
                        ==
                        student[
                            "student_id"
                        ]
                    )
                    &
                    (
                        attendance[
                            "date"
                        ]
                        ==
                        date
                    )
                ]

                if not attendance.empty

                else

                pd.DataFrame()

            )

            new_record = {

                "student_id":
                    student[
                        "student_id"
                    ],

                "name":
                    student[
                        "name"
                    ],

                "class_name":
                    student[
                        "class_name"
                    ],

                "date":
                    date,

                "time":
                    time,

                "status":
                    status

            }

            if not existing.empty:

                mask = (

                    (
                        attendance[
                            "student_id"
                        ]
                        ==
                        student[
                            "student_id"
                        ]
                    )

                    &

                    (
                        attendance[
                            "date"
                        ]
                        ==
                        date
                    )

                )

                for key, value in (
                    new_record.items()
                ):

                    attendance.loc[
                        mask,
                        key
                    ] = value

            else:

                attendance = pd.concat(
                    [
                        attendance,

                        pd.DataFrame(
                            [new_record]
                        )
                    ],
                    ignore_index=True
                )

            save_attendance(
                attendance
            )

            st.success(
                f"{student['name']} marked {status}."
            )

    st.markdown(
        "### 📋 Attendance History"
    )

    attendance = load_attendance()

    if attendance.empty:

        st.info(
            "No attendance records yet."
        )

    else:

        st.dataframe(
            attendance.iloc[::-1],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TEACHER MANAGEMENT
# ============================================================

def teacher_management():

    st.markdown(
        "## 👨‍🏫 Teacher Accounts"
    )

    users = load_users()

    teachers = users.setdefault(
        "teachers",
        {}
    )

    with st.expander(
        "➕ Add Teacher"
    ):

        teacher_id = st.text_input(
            "Teacher ID"
        )

        teacher_name = st.text_input(
            "Teacher Name"
        )

        teacher_password = st.text_input(
            "Temporary Password",
            type="password"
        )

        if st.button(
            "Create Teacher Account"
        ):

            teacher_id = (
                teacher_id.strip()
            )

            if not teacher_id:

                st.error(
                    "Enter Teacher ID."
                )

            elif not teacher_name.strip():

                st.error(
                    "Enter teacher name."
                )

            elif len(
                teacher_password
            ) < 4:

                st.error(
                    "Password must have at least 4 characters."
                )

            elif teacher_id in teachers:

                st.error(
                    "Teacher ID already exists."
                )

            else:

                teachers[
                    teacher_id
                ] = {

                    "name":
                        teacher_name.strip(),

                    "password_hash":
                        password_hash(
                            teacher_password
                        ),

                    "enabled":
                        True

                }

                save_users(
                    users
                )

                st.success(
                    "Teacher account created."
                )

                st.rerun()

    if not teachers:

        st.info(
            "No teacher accounts yet."
        )

        return

    teacher_rows = []

    for teacher_id, info in (
        teachers.items()
    ):

        teacher_rows.append(
            {
                "Teacher ID":
                    teacher_id,

                "Name":
                    info.get(
                        "name",
                        ""
                    ),

                "Status":
                    (
                        "Enabled"
                        if info.get(
                            "enabled",
                            True
                        )
                        else
                        "Disabled"
                    )
            }
        )

    st.dataframe(
        pd.DataFrame(
            teacher_rows
        ),
        use_container_width=True,
        hide_index=True
    )

    st.markdown(
        "### Manage Account"
    )

    selected_teacher = st.selectbox(
        "Teacher",
        list(
            teachers.keys()
        )
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "Enable / Disable"
        ):

            teachers[
                selected_teacher
            ][
                "enabled"
            ] = not teachers[
                selected_teacher
            ].get(
                "enabled",
                True
            )

            save_users(
                users
            )

            st.rerun()

    with c2:

        if st.button(
            "🗑 Delete Teacher"
        ):

            del teachers[
                selected_teacher
            ]

            save_users(
                users
            )

            st.rerun()


# ============================================================
# CHANGE OWN PASSWORD
# ============================================================

def settings_page():

    st.markdown(
        "## ⚙️ Settings"
    )

    st.markdown(
        "### 🔐 Change My Password"
    )

    new_password = st.text_input(
        "New Password",
        type="password"
    )

    confirm_password = st.text_input(
        "Confirm Password",
        type="password"
    )

    if st.button(
        "Update My Password"
    ):

        if len(
            new_password
        ) < 4:

            st.error(
                "Password must have at least 4 characters."
            )

        elif (
            new_password
            !=
            confirm_password
        ):

            st.error(
                "Passwords do not match."
            )

        else:

            users = load_users()

            if (
                st.session_state.role
                ==
                "Super Admin"
            ):

                users[
                    "admin"
                ][
                    "password_hash"
                ] = password_hash(
                    new_password
                )

            else:

                users[
                    "teachers"
                ][
                    st.session_state.user_id
                ][
                    "password_hash"
                ] = password_hash(
                    new_password
                )

            save_users(
                users
            )

            st.success(
                "✅ Password changed successfully."
            )

    st.divider()

    st.markdown(
        "### 💾 Data Storage"
    )

    st.warning(
        "IMPORTANT: This version saves data to files on the server. "
        "Render can reset these files during redeploy/restart. "
        "For data that permanently follows you to every computer, "
        "EduVision needs a cloud database."
    )


# ============================================================
# REPORTS
# ============================================================

def reports_page():

    st.markdown(
        "## 📊 Reports"
    )

    students = load_students()

    attendance = load_attendance()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Students",
        len(students)
    )

    c2.metric(
        "Attendance Records",
        len(attendance)
    )

    if not attendance.empty:

        present = len(
            attendance[
                attendance[
                    "status"
                ]
                ==
                "Present"
            ]
        )

        percentage = round(
            (
                present
                /
                len(attendance)
            )
            *
            100,
            1
        )

    else:

        percentage = 0

    c3.metric(
        "Overall Present %",
        f"{percentage}%"
    )

    if not attendance.empty:

        st.markdown(
            "### Attendance Data"
        )

        st.dataframe(
            attendance.iloc[::-1],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# LOGOUT
# ============================================================

def logout():

    st.session_state.logged_in = False

    st.session_state.role = None

    st.session_state.user_id = None

    st.rerun()


# ============================================================
# MAIN APP
# ============================================================

def app():

    with st.sidebar:

        st.markdown(
            "# 🎓 EduVision"
        )

        st.caption(
            st.session_state.role
        )

        st.divider()

        if (
            st.session_state.role
            ==
            "Super Admin"
        ):

            pages = [

                "🏠 Dashboard",

                "🎓 Students",

                "📷 Attendance + Camera",

                "👨‍🏫 Teachers",

                "📊 Reports",

                "⚙️ Settings"

            ]

        else:

            pages = [

                "🏠 Dashboard",

                "🎓 Students",

                "📷 Attendance + Camera",

                "📊 Reports",

                "⚙️ Settings"

            ]

        page = st.radio(
            "Navigation",
            pages
        )

        st.divider()

        if st.button(
            "🚪 Log Out"
        ):

            logout()

    if page == "🏠 Dashboard":

        dashboard()

    elif page == "🎓 Students":

        students_page()

    elif page == "📷 Attendance + Camera":

        attendance_page()

    elif page == "👨‍🏫 Teachers":

        teacher_management()

    elif page == "📊 Reports":

        reports_page()

    elif page == "⚙️ Settings":

        settings_page()


# ============================================================
# START
# ============================================================

if not st.session_state.logged_in:

    login_page()

else:

    app()

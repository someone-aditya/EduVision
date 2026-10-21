import os
import json
import hashlib
import importlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# EDVISION
# Admin + Teacher
# Attendance + Camera + Smart Occupancy
# ============================================================

st.set_page_config(
    page_title="EduVision",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

STUDENTS_FILE = DATA_DIR / "students.csv"
ATTENDANCE_FILE = DATA_DIR / "attendance.csv"
USERS_FILE = DATA_DIR / "users.json"


# ============================================================
# ADMIN LOGIN
# ============================================================

ADMIN_ID = os.getenv(
    "EDUVISION_ADMIN_ID",
    "12126"
)

ADMIN_PASSWORD = os.getenv(
    "EDUVISION_ADMIN_PASSWORD",
    "12126"
)


# ============================================================
# PASSWORD
# ============================================================

def password_hash(password):
    return hashlib.sha256(
        str(password).encode("utf-8")
    ).hexdigest()


# ============================================================
# REQUIRED COLUMNS
# ============================================================

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
# INITIAL SETUP
# ============================================================

def setup_files():

    if not STUDENTS_FILE.exists():

        pd.DataFrame(
            columns=STUDENT_COLUMNS
        ).to_csv(
            STUDENTS_FILE,
            index=False
        )

    if not ATTENDANCE_FILE.exists():

        pd.DataFrame(
            columns=ATTENDANCE_COLUMNS
        ).to_csv(
            ATTENDANCE_FILE,
            index=False
        )

    if not USERS_FILE.exists():

        users = {
            "admin": {
                "id": ADMIN_ID,
                "password_hash": password_hash(
                    ADMIN_PASSWORD
                )
            },
            "teachers": {}
        }

        USERS_FILE.write_text(
            json.dumps(
                users,
                indent=2
            ),
            encoding="utf-8"
        )


# ============================================================
# USERS
# ============================================================

def load_users():

    try:

        users = json.loads(
            USERS_FILE.read_text(
                encoding="utf-8"
            )
        )

        if "admin" not in users:
            users["admin"] = {
                "id": ADMIN_ID,
                "password_hash": password_hash(
                    ADMIN_PASSWORD
                )
            }

        if "teachers" not in users:
            users["teachers"] = {}

        return users

    except Exception:

        return {
            "admin": {
                "id": ADMIN_ID,
                "password_hash": password_hash(
                    ADMIN_PASSWORD
                )
            },
            "teachers": {}
        }


def save_users(users):

    USERS_FILE.write_text(
        json.dumps(
            users,
            indent=2
        ),
        encoding="utf-8"
    )


# ============================================================
# STUDENTS
# ============================================================

def load_students():

    try:

        df = pd.read_csv(
            STUDENTS_FILE,
            dtype=str
        ).fillna("")

        # ----------------------------------------
        # Repair older EduVision CSV structures
        # ----------------------------------------

        rename_map = {}

        if (
            "class" in df.columns
            and
            "class_name" not in df.columns
        ):
            rename_map["class"] = "class_name"

        if (
            "student_name" in df.columns
            and
            "name" not in df.columns
        ):
            rename_map["student_name"] = "name"

        if (
            "id" in df.columns
            and
            "student_id" not in df.columns
        ):
            rename_map["id"] = "student_id"

        if rename_map:
            df = df.rename(
                columns=rename_map
            )

        for column in STUDENT_COLUMNS:

            if column not in df.columns:
                df[column] = ""

        df = df[
            STUDENT_COLUMNS
        ].copy()

        df.to_csv(
            STUDENTS_FILE,
            index=False
        )

        return df

    except Exception:

        return pd.DataFrame(
            columns=STUDENT_COLUMNS
        )


def save_students(df):

    for column in STUDENT_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    df[
        STUDENT_COLUMNS
    ].to_csv(
        STUDENTS_FILE,
        index=False
    )


# ============================================================
# ATTENDANCE
# ============================================================

def load_attendance():

    try:

        df = pd.read_csv(
            ATTENDANCE_FILE,
            dtype=str
        ).fillna("")

        if (
            "class" in df.columns
            and
            "class_name" not in df.columns
        ):

            df = df.rename(
                columns={
                    "class":
                    "class_name"
                }
            )

        for column in ATTENDANCE_COLUMNS:

            if column not in df.columns:
                df[column] = ""

        df = df[
            ATTENDANCE_COLUMNS
        ].copy()

        df.to_csv(
            ATTENDANCE_FILE,
            index=False
        )

        return df

    except Exception:

        return pd.DataFrame(
            columns=ATTENDANCE_COLUMNS
        )


def save_attendance(df):

    for column in ATTENDANCE_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    df[
        ATTENDANCE_COLUMNS
    ].to_csv(
        ATTENDANCE_FILE,
        index=False
    )


setup_files()


# ============================================================
# UI / MAGIC-UI INSPIRED CSS
# No custom HTML hero sections are used.
# ============================================================

st.markdown(
    """
<style>

:root {
    --bg: #020617;
    --panel: #0f172a;
    --panel2: #111827;
    --blue: #3b82f6;
    --cyan: #22d3ee;
    --purple: #8b5cf6;
    --text: #f8fafc;
    --muted: #94a3b8;
}


/* BACKGROUND */

.stApp {
    color: white;

    background:
        radial-gradient(
            circle at 12% 15%,
            rgba(139,92,246,.16),
            transparent 28%
        ),
        radial-gradient(
            circle at 88% 70%,
            rgba(34,211,238,.13),
            transparent 30%
        ),
        linear-gradient(
            135deg,
            #020617,
            #071426,
            #020617
        );

    background-size: 200% 200%;

    animation:
        eduBackground 14s ease infinite;
}


@keyframes eduBackground {

    0%,100% {
        background-position:
            0% 50%;
    }

    50% {
        background-position:
            100% 50%;
    }
}


/* PAGE */

.block-container {
    max-width: 1400px;
    padding-top: 1.4rem;
}


/* HEADINGS */

h1 {
    font-weight: 900 !important;
    letter-spacing: -1px !important;
}

h2,
h3 {
    color: #f8fafc !important;
}


/* INPUTS */

div[data-baseweb="input"] {
    background: white !important;
    border-radius: 12px !important;
}

div[data-baseweb="input"] input {
    color: black !important;
    background: white !important;
    -webkit-text-fill-color:
        black !important;
}

input[type="text"],
input[type="password"],
input[type="number"],
input[type="email"] {
    color: black !important;
    background: white !important;
    -webkit-text-fill-color:
        black !important;
}

input::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color:
        #64748b !important;
}


/* SELECT BOX */

div[data-baseweb="select"] > div {
    background: white !important;
    color: black !important;
    border-radius: 12px !important;
}

div[data-baseweb="select"] span {
    color: black !important;
}

ul[role="listbox"] {
    background: white !important;
}

li[role="option"] {
    color: black !important;
    background: white !important;
}

li[role="option"]:hover {
    background: #e2e8f0 !important;
}


/* BUTTONS */

div.stButton > button {
    width: 100%;

    color: white !important;

    font-weight: 800;

    border-radius: 14px;

    border:
        1px solid
        rgba(34,211,238,.40);

    background:
        linear-gradient(
            90deg,
            #2563eb,
            #7c3aed,
            #0891b2
        );

    background-size:
        200% 100%;

    box-shadow:
        0 8px 25px
        rgba(37,99,235,.18);

    transition:
        all .20s ease;
}


div.stButton > button:hover {

    transform:
        translateY(-2px)
        scale(1.025);

    background-position:
        100% 0;

    border-color:
        #67e8f9;

    box-shadow:
        0 15px 35px
        rgba(34,211,238,.20);
}


/* METRIC CARDS */

[data-testid="stMetric"] {

    padding: 18px;

    border-radius: 20px;

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

    transition:
        transform .2s ease,
        border-color .2s ease;
}


[data-testid="stMetric"]:hover {

    transform:
        translateY(-4px);

    border-color:
        rgba(34,211,238,.50);
}


[data-testid="stMetricValue"] {
    color: white;
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
    color: white;
}


/* CAMERA */

[data-testid="stCameraInput"] {

    padding: 12px;

    border-radius: 20px;

    border:
        1px solid
        rgba(34,211,238,.25);

    background:
        rgba(15,23,42,.80);
}


/* TABLE */

[data-testid="stDataFrame"] {

    border-radius: 16px;

    overflow: hidden;
}


/* TABS */

.stTabs [data-baseweb="tab"] {

    background:
        #111827;

    border-radius:
        12px;

    color:
        white;

    padding:
        8px 18px;
}


/* ALERT */

[data-testid="stAlert"] {
    border-radius: 14px;
}


/* LABELS */

label {
    color: white !important;
}


/* FOOTER */

footer {
    visibility: hidden;
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None


# ============================================================
# LOGIN PAGE
# ============================================================

def login_page():

    # Normal Streamlit components.
    # No <div> hero, so raw HTML cannot appear.

    st.title("🎓 EduVision")

    st.subheader(
        "AI • SMART CLASSROOM"
    )

    st.write(
        "Smarter classrooms through automated attendance, "
        "classroom monitoring and simple management."
    )

    st.success(
        "🟢 System Online"
    )

    st.divider()

    left, middle, right = st.columns(
        [1, 1.2, 1]
    )

    with middle:

        st.subheader(
            "✨ Welcome Back"
        )

        role = st.selectbox(
            "Login as",
            [
                "Admin",
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

            if role == "Admin":

                admin = users.get(
                    "admin",
                    {}
                )

                valid = (
                    user_id
                    ==
                    admin.get("id")

                    and

                    password_hash(
                        password
                    )
                    ==
                    admin.get(
                        "password_hash"
                    )
                )

            elif role == "Teacher":

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

                    password_hash(
                        password
                    )
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
            attendance["date"]
            ==
            today
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

    # Normal Python Streamlit UI
    st.title("🎓 EduVision")

    st.subheader(
        "Smart Classroom Management"
    )

    st.write(
        "Automated attendance and classroom monitoring "
        "so teachers can spend more time teaching."
    )

    st.success(
        "🟢 System Online"
    )

    st.divider()

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

    st.subheader(
        "⚡ Quick Actions"
    )

    st.info(
        "Use the sidebar to manage students, "
        "take attendance and open Smart Occupancy."
    )


# ============================================================
# STUDENT MANAGEMENT
# ============================================================

def students_page():

    students = load_students()

    st.title(
        "🎓 Student Management"
    )

    if (
        st.session_state.role
        ==
        "Admin"
    ):

        with st.expander(
            "➕ Add New Student",
            expanded=False
        ):

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID",
                    key="new_student_id"
                )

                name = st.text_input(
                    "Full Name",
                    key="new_student_name"
                )

            with c2:

                class_name = st.text_input(
                    "Class",
                    key="new_student_class"
                )

                roll_no = st.text_input(
                    "Roll Number",
                    key="new_student_roll"
                )

            if st.button(
                "✨ Add Student"
            ):

                student_id = (
                    student_id.strip()
                )

                name = name.strip()

                class_name = (
                    class_name.strip()
                )

                roll_no = (
                    roll_no.strip()
                )

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
                    in
                    students[
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

    st.subheader(
        "Student List"
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

        if (
            st.session_state.role
            ==
            "Admin"
        ):

            st.divider()

            st.subheader(
                "🗑️ Remove Student"
            )

            student_options = {}

            for _, student in (
                students.iterrows()
            ):

                label = (
                    f"{student['student_id']} — "
                    f"{student['name']}"
                )

                student_options[
                    label
                ] = student[
                    "student_id"
                ]

            selected = st.selectbox(
                "Select Student",
                list(
                    student_options.keys()
                ),
                key="delete_student"
            )

            if st.button(
                "Remove Selected Student"
            ):

                sid = student_options[
                    selected
                ]

                students = students[
                    students[
                        "student_id"
                    ]
                    !=
                    sid
                ]

                save_students(
                    students
                )

                st.success(
                    "Student removed."
                )

                st.rerun()


# ============================================================
# CAMERA
# ============================================================

def camera_capture(
    key="classroom_camera"
):

    st.subheader(
        "📷 Classroom Camera"
    )

    st.caption(
        "Allow camera access when your browser asks for permission."
    )

    try:

        picture = st.camera_input(
            "Open Camera / Capture",
            key=key
        )

        if picture is not None:

            st.success(
                "✅ Camera is working."
            )

            st.image(
                picture,
                caption="Latest Capture",
                use_container_width=True
            )

            return picture

    except Exception as error:

        st.error(
            "Camera could not open."
        )

        st.info(
            "Check the browser camera permission "
            "and refresh the page."
        )

        st.caption(
            str(error)
        )

    return None


# ============================================================
# ATTENDANCE
# ============================================================

def attendance_page():

    students = load_students()
    attendance = load_attendance()

    st.title(
        "📷 Smart Attendance"
    )

    st.write(
        "Use the classroom camera and attendance tools "
        "to reduce time spent taking attendance manually."
    )

    camera_tab, manual_tab, history_tab = st.tabs(
        [
            "📷 Camera",
            "✋ Attendance",
            "📋 History"
        ]
    )

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

   with camera_tab:

    try:
        from smart_attendance import render_page

        render_page()

    except Exception as error:

        st.error(
            "AI Attendance could not start."
        )

        st.code(str(error))

    # --------------------------------------------------------
    # ATTENDANCE
    # --------------------------------------------------------

    with manual_tab:

        if students.empty:

            st.warning(
                "Add at least one student first."
            )

        else:

            student_options = {}

            for _, student in (
                students.iterrows()
            ):

                class_name = student.get(
                    "class_name",
                    ""
                )

                label = (
                    f"{student.get('student_id', '')} — "
                    f"{student.get('name', '')}"
                )

                if class_name:
                    label += (
                        f" — {class_name}"
                    )

                student_options[
                    label
                ] = student

            selected = st.selectbox(
                "Select Student",
                list(
                    student_options.keys()
                ),
                key="attendance_student"
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

                student = (
                    student_options[
                        selected
                    ]
                )

                now = datetime.now()

                date = now.strftime(
                    "%Y-%m-%d"
                )

                time = now.strftime(
                    "%H:%M:%S"
                )

                student_id = student.get(
                    "student_id",
                    ""
                )

                existing_mask = (
                    (
                        attendance[
                            "student_id"
                        ]
                        ==
                        student_id
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

                record = {
                    "student_id":
                        student_id,

                    "name":
                        student.get(
                            "name",
                            ""
                        ),

                    "class_name":
                        student.get(
                            "class_name",
                            ""
                        ),

                    "date":
                        date,

                    "time":
                        time,

                    "status":
                        status
                }

                if (
                    not attendance.empty
                    and
                    existing_mask.any()
                ):

                    for key, value in (
                        record.items()
                    ):

                        attendance.loc[
                            existing_mask,
                            key
                        ] = value

                else:

                    attendance = pd.concat(
                        [
                            attendance,
                            pd.DataFrame(
                                [record]
                            )
                        ],
                        ignore_index=True
                    )

                save_attendance(
                    attendance
                )

                st.success(
                    f"{record['name']} marked {status}."
                )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    with history_tab:

        attendance = (
            load_attendance()
        )

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
# SMART OCCUPANCY
# ============================================================

def smart_occupancy_page():

    st.title(
        "👥 Smart Occupancy"
    )

    st.write(
        "AI-powered classroom occupancy monitoring using YOLO."
    )

    st.info(
        "EduVision can use your existing smart_occupancy.py "
        "module for person detection and classroom occupancy."
    )

    module_path = (
        BASE_DIR /
        "smart_occupancy.py"
    )

    if not module_path.exists():

        st.error(
            "smart_occupancy.py was not found in the repository."
        )

        return

    try:

        smart_occupancy = (
            importlib.import_module(
                "smart_occupancy"
            )
        )

    except Exception as error:

        st.error(
            "Smart Occupancy could not be loaded."
        )

        st.code(
            str(error)
        )

        st.warning(
            "Check requirements.txt for the packages "
            "used by smart_occupancy.py."
        )

        return

    # Try common entry function names.

    possible_functions = [
        "main",
        "run",
        "app",
        "smart_occupancy",
        "show"
    ]

    for function_name in (
        possible_functions
    ):

        function = getattr(
            smart_occupancy,
            function_name,
            None
        )

        if callable(function):

            try:

                function()

            except Exception as error:

                st.error(
                    "Smart Occupancy started but encountered an error."
                )

                st.code(
                    str(error)
                )

            return

    st.warning(
        "smart_occupancy.py exists, but EduVision could not find "
        "a main(), run(), app(), smart_occupancy() or show() function."
    )

    st.caption(
        "The occupancy file needs one callable function "
        "so app.py can open it from this page."
    )


# ============================================================
# TEACHER MANAGEMENT
# ============================================================

def teacher_management():

    st.title(
        "👨‍🏫 Teacher Accounts"
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

            teacher_name = (
                teacher_name.strip()
            )

            if not teacher_id:

                st.error(
                    "Enter Teacher ID."
                )

            elif not teacher_name:

                st.error(
                    "Enter Teacher Name."
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
                        teacher_name,

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

    rows = []

    for teacher_id, info in (
        teachers.items()
    ):

        rows.append(
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
            rows
        ),
        use_container_width=True,
        hide_index=True
    )

    st.subheader(
        "Manage Account"
    )

    selected_teacher = st.selectbox(
        "Teacher",
        list(
            teachers.keys()
        ),
        key="manage_teacher"
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
# REPORTS
# ============================================================

def reports_page():

    st.title(
        "📊 Reports"
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
                attendance["status"]
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

    st.divider()

    if attendance.empty:

        st.info(
            "No attendance data yet."
        )

    else:

        # Filter by class

        classes = sorted(
            [
                value
                for value
                in
                attendance[
                    "class_name"
                ].unique()
                if value
            ]
        )

        class_filter = st.selectbox(
            "Class Filter",
            [
                "All Classes"
            ]
            +
            classes
        )

        report = attendance.copy()

        if (
            class_filter
            !=
            "All Classes"
        ):

            report = report[
                report[
                    "class_name"
                ]
                ==
                class_filter
            ]

        st.dataframe(
            report.iloc[::-1],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SETTINGS
# ============================================================

def settings_page():

    st.title(
        "⚙️ Settings"
    )

    st.subheader(
        "🔐 Change My Password"
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
                "Admin"
            ):

                users[
                    "admin"
                ][
                    "password_hash"
                ] = password_hash(
                    new_password
                )

            else:

                teacher_id = (
                    st.session_state.user_id
                )

                if (
                    teacher_id
                    in
                    users.get(
                        "teachers",
                        {}
                    )
                ):

                    users[
                        "teachers"
                    ][
                        teacher_id
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

    st.subheader(
        "💾 Data"
    )

    st.warning(
        "CSV/JSON files stored directly on Render may reset "
        "when the service is redeployed or restarted. "
        "Permanent cross-device storage requires a cloud database."
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

        st.title(
            "🎓 EduVision"
        )

        st.caption(
            f"Logged in as: "
            f"{st.session_state.role}"
        )

        st.divider()

        if (
            st.session_state.role
            ==
            "Admin"
        ):

            pages = [
                "🏠 Dashboard",
                "🎓 Students",
                "📷 Smart Attendance",
                "👥 Smart Occupancy",
                "👨‍🏫 Teachers",
                "📊 Reports",
                "⚙️ Settings",
            ]

        else:

            pages = [
                "🏠 Dashboard",
                "🎓 Students",
                "📷 Smart Attendance",
                "👥 Smart Occupancy",
                "📊 Reports",
                "⚙️ Settings",
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

    elif page == "📷 Smart Attendance":

        attendance_page()

    elif page == "👥 Smart Occupancy":

        smart_occupancy_page()

    elif page == "👨‍🏫 Teachers":

        if (
            st.session_state.role
            ==
            "Admin"
        ):

            teacher_management()

        else:

            st.error(
                "Admin access required."
            )

    elif page == "📊 Reports":

        reports_page()

    elif page == "⚙️ Settings":

        settings_page()


# ============================================================
# START EDVISION
# ============================================================

if not st.session_state.logged_in:

    login_page()

else:

    app()

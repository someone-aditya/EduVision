import os
import hashlib
import secrets
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from supabase import create_client


# ============================================================
# EDVISION
# ============================================================

st.set_page_config(
    page_title="EduVision",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Main EduVision administrator.
# You can change these later in Render Environment Variables.
EDUVISION_ADMIN_ID = os.getenv(
    "EDUVISION_ADMIN_ID",
    "12126"
)

EDUVISION_ADMIN_PASSWORD = os.getenv(
    "EDUVISION_ADMIN_PASSWORD",
    "12126"
)


# ============================================================
# DESIGN
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at 10% 10%,
                rgba(124,58,237,.18),
                transparent 28%
            ),
            radial-gradient(
                circle at 90% 75%,
                rgba(6,182,212,.13),
                transparent 30%
            ),
            linear-gradient(
                135deg,
                #020617,
                #071426,
                #020617
            );

        color: white;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: #f8fafc !important;
    }

    p {
        color: #cbd5e1;
    }

    div[data-baseweb="input"] {
        background: white !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="input"] input {
        color: #020617 !important;
        background: white !important;
        -webkit-text-fill-color: #020617 !important;
    }

    input::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
    }

    div[data-baseweb="select"] > div {
        background: white !important;
        color: black !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="select"] span {
        color: black !important;
    }

    li[role="option"] {
        color: black !important;
        background: white !important;
    }

    div.stButton > button {
        width: 100%;
        min-height: 45px;

        color: white !important;
        font-weight: 800;

        border-radius: 14px;

        border:
            1px solid
            rgba(34,211,238,.35);

        background:
            linear-gradient(
                90deg,
                #2563eb,
                #7c3aed,
                #0891b2
            );
    }

    div.stButton > button:hover {
        border:
            1px solid
            rgba(255,255,255,.65);
    }

    [data-testid="stMetric"] {
        padding: 18px;
        border-radius: 18px;

        background:
            rgba(15,23,42,.82);

        border:
            1px solid
            rgba(139,92,246,.22);
    }

    [data-testid="stMetricValue"] {
        color: white;
    }

    [data-testid="stSidebar"] {
        background:
            rgba(2,6,23,.98);
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    label {
        color: white !important;
    }

    footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SUPABASE
# ============================================================

@st.cache_resource
def get_database():

    if not SUPABASE_URL:
        raise RuntimeError(
            "SUPABASE_URL is missing from Render."
        )

    if not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_KEY is missing from Render."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


try:

    db = get_database()

except Exception as error:

    st.error(
        "EduVision could not connect to its database."
    )

    st.code(
        str(error)
    )

    st.stop()


# ============================================================
# SECURITY
# ============================================================

def hash_password(password):

    return hashlib.sha256(
        str(password).encode("utf-8")
    ).hexdigest()


def generate_school_id():

    return (
        "SCH-"
        +
        secrets.token_hex(3).upper()
    )


# ============================================================
# SESSION
# ============================================================

DEFAULT_SESSION = {
    "screen": "home",
    "logged_in": False,
    "role": None,
    "school_id": None,
    "school_name": None,
    "user_id": None,
    "user_name": None,
}


for key, value in DEFAULT_SESSION.items():

    if key not in st.session_state:

        st.session_state[key] = value


def clear_login():

    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.school_id = None
    st.session_state.school_name = None
    st.session_state.user_id = None
    st.session_state.user_name = None


def go_home():

    clear_login()

    st.session_state.screen = "home"

    st.rerun()


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_school(school_id):

    try:

        response = (
            db.table("schools")
            .select("*")
            .eq(
                "school_id",
                school_id.strip()
            )
            .execute()
        )

        if response.data:

            return response.data[0]

    except Exception:

        pass

    return None


def get_school_by_admin(
    school_id,
    admin_id
):

    try:

        response = (
            db.table("schools")
            .select("*")
            .eq(
                "school_id",
                school_id
            )
            .eq(
                "admin_id",
                admin_id
            )
            .execute()
        )

        if response.data:

            return response.data[0]

    except Exception:

        pass

    return None


def get_teacher(
    school_id,
    teacher_id
):

    try:

        response = (
            db.table("teachers")
            .select("*")
            .eq(
                "school_id",
                school_id
            )
            .eq(
                "teacher_id",
                teacher_id
            )
            .execute()
        )

        if response.data:

            return response.data[0]

    except Exception:

        pass

    return None


def load_students():

    try:

        response = (
            db.table("students")
            .select("*")
            .eq(
                "school_id",
                st.session_state.school_id
            )
            .order(
                "name"
            )
            .execute()
        )

        if response.data:

            return pd.DataFrame(
                response.data
            )

    except Exception as error:

        st.error(
            f"Could not load students: {error}"
        )

    return pd.DataFrame()


def load_attendance():

    try:

        response = (
            db.table("attendance")
            .select("*")
            .eq(
                "school_id",
                st.session_state.school_id
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        if response.data:

            return pd.DataFrame(
                response.data
            )

    except Exception as error:

        st.error(
            f"Could not load attendance: {error}"
        )

    return pd.DataFrame()


# ============================================================
# HOME
# ============================================================

def home_page():

    st.title(
        "🎓 EduVision"
    )

    st.subheader(
        "AI • SMART CLASSROOM"
    )

    st.write(
        "Smarter classrooms through automated "
        "attendance, classroom monitoring and "
        "simple school management."
    )

    st.success(
        "🟢 EduVision Online"
    )

    st.divider()

    st.subheader(
        "Welcome to EduVision"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "🏫 School"
        )

        st.write(
            "Register a school or open an "
            "approved school."
        )

        if st.button(
            "🏫 School Portal",
            use_container_width=True
        ):

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    with col2:

        st.subheader(
            "👑 EduVision Admin"
        )

        st.write(
            "Review and approve school "
            "registration requests."
        )

        if st.button(
            "👑 Admin Portal",
            use_container_width=True
        ):

            st.session_state.screen = (
                "platform_admin_login"
            )

            st.rerun()


# ============================================================
# SCHOOL PORTAL
# ============================================================

def school_portal():

    st.title(
        "🏫 School Portal"
    )

    st.write(
        "Register your school or open an "
        "existing approved school."
    )

    if st.button(
        "← Back to EduVision"
    ):

        go_home()

    st.divider()

    register_tab, open_tab = st.tabs(
        [
            "📝 Register School",
            "🏫 Open School",
        ]
    )

    # --------------------------------------------------------
    # REGISTER SCHOOL
    # --------------------------------------------------------

    with register_tab:

        st.subheader(
            "Register Your School"
        )

        st.info(
            "After registration, an EduVision "
            "Admin must approve your school."
        )

        school_name = st.text_input(
            "School Name",
            key="register_school_name"
        )

        admin_id = st.text_input(
            "School Admin ID",
            key="register_admin_id"
        )

        admin_password = st.text_input(
            "Admin Password",
            type="password",
            key="register_admin_password"
        )

        confirm_password = st.text_input(
            "Confirm Admin Password",
            type="password",
            key="register_admin_confirm"
        )

        if st.button(
            "✨ Submit School Registration"
        ):

            school_name = (
                school_name.strip()
            )

            admin_id = (
                admin_id.strip()
            )

            if not school_name:

                st.error(
                    "Enter your school name."
                )

            elif not admin_id:

                st.error(
                    "Enter an Admin ID."
                )

            elif len(admin_password) < 6:

                st.error(
                    "Use a password with at least "
                    "6 characters."
                )

            elif (
                admin_password
                !=
                confirm_password
            ):

                st.error(
                    "Passwords do not match."
                )

            else:

                school_id = (
                    generate_school_id()
                )

                try:

                    db.table(
                        "schools"
                    ).insert(
                        {
                            "school_id":
                                school_id,

                            "school_name":
                                school_name,

                            "admin_id":
                                admin_id,

                            "admin_password_hash":
                                hash_password(
                                    admin_password
                                ),

                            "approval_status":
                                "pending",
                        }
                    ).execute()

                    st.success(
                        "🎉 School registration "
                        "submitted!"
                    )

                    st.info(
                        f"Your School ID is: "
                        f"{school_id}"
                    )

                    st.warning(
                        "SAVE THIS SCHOOL ID. "
                        "You will need it to open "
                        "your school after approval."
                    )

                except Exception as error:

                    st.error(
                        "School registration failed."
                    )

                    st.code(
                        str(error)
                    )

    # --------------------------------------------------------
    # OPEN SCHOOL
    # --------------------------------------------------------

    with open_tab:

        st.subheader(
            "Open School"
        )

        school_id = st.text_input(
            "School ID",
            placeholder="SCH-XXXXXX",
            key="open_school_id"
        )

        if st.button(
            "🏫 Open School"
        ):

            school_id = (
                school_id
                .strip()
                .upper()
            )

            school = get_school(
                school_id
            )

            if not school:

                st.error(
                    "School ID not found."
                )

            else:

                status = school.get(
                    "approval_status",
                    "pending"
                )

                if status == "pending":

                    st.warning(
                        "⏳ This school is waiting "
                        "for EduVision Admin approval."
                    )

                elif status == "rejected":

                    st.error(
                        "❌ This school registration "
                        "was rejected."
                    )

                elif status != "approved":

                    st.warning(
                        "This school is not active yet."
                    )

                else:

                    st.session_state.school_id = (
                        school["school_id"]
                    )

                    st.session_state.school_name = (
                        school["school_name"]
                    )

                    st.session_state.screen = (
                        "school_login"
                    )

                    st.rerun()


# ============================================================
# MAIN EDVISION ADMIN LOGIN
# ============================================================

def platform_admin_login():

    st.title(
        "👑 EduVision Admin"
    )

    st.write(
        "Approve and manage schools using EduVision."
    )

    if st.button(
        "← Back"
    ):

        go_home()

    st.divider()

    admin_id = st.text_input(
        "EduVision Admin ID"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "🔐 Admin Login"
    ):

        if (
            admin_id
            ==
            EDUVISION_ADMIN_ID
            and
            password
            ==
            EDUVISION_ADMIN_PASSWORD
        ):

            st.session_state.logged_in = True
            st.session_state.role = (
                "EduVision Admin"
            )

            st.session_state.user_id = (
                admin_id
            )

            st.session_state.screen = (
                "platform_admin"
            )

            st.rerun()

        else:

            st.error(
                "Incorrect EduVision Admin login."
            )


# ============================================================
# MAIN EDVISION ADMIN PANEL
# ============================================================

def platform_admin_page():

    st.title(
        "👑 EduVision Administration"
    )

    st.write(
        "Review school registrations and control "
        "which schools can use EduVision."
    )

    try:

        response = (
            db.table("schools")
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        schools = response.data or []

    except Exception as error:

        st.error(
            str(error)
        )

        schools = []

    pending = [
        school
        for school in schools
        if school.get(
            "approval_status"
        )
        ==
        "pending"
    ]

    approved = [
        school
        for school in schools
        if school.get(
            "approval_status"
        )
        ==
        "approved"
    ]

    rejected = [
        school
        for school in schools
        if school.get(
            "approval_status"
        )
        ==
        "rejected"
    ]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "⏳ Pending",
        len(pending)
    )

    c2.metric(
        "✅ Approved",
        len(approved)
    )

    c3.metric(
        "❌ Rejected",
        len(rejected)
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "⏳ School Requests",
            "✅ Approved Schools",
            "❌ Rejected",
        ]
    )

    # --------------------------------------------------------
    # PENDING
    # --------------------------------------------------------

    with tab1:

        if not pending:

            st.info(
                "No pending school requests."
            )

        for school in pending:

            st.subheader(
                school.get(
                    "school_name",
                    "School"
                )
            )

            st.write(
                "School ID:",
                school.get(
                    "school_id"
                )
            )

            st.write(
                "School Admin ID:",
                school.get(
                    "admin_id"
                )
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "✅ Approve",
                    key=(
                        "approve_"
                        +
                        school["school_id"]
                    )
                ):

                    try:

                        db.table(
                            "schools"
                        ).update(
                            {
                                "approval_status":
                                    "approved",

                                "approved_at":
                                    datetime.now(
                                        timezone.utc
                                    ).isoformat(),

                                "approved_by":
                                    st.session_state.user_id,
                            }
                        ).eq(
                            "school_id",
                            school[
                                "school_id"
                            ]
                        ).execute()

                        st.success(
                            "School approved."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

            with col2:

                if st.button(
                    "❌ Reject",
                    key=(
                        "reject_"
                        +
                        school["school_id"]
                    )
                ):

                    try:

                        db.table(
                            "schools"
                        ).update(
                            {
                                "approval_status":
                                    "rejected"
                            }
                        ).eq(
                            "school_id",
                            school[
                                "school_id"
                            ]
                        ).execute()

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

            st.divider()

    # --------------------------------------------------------
    # APPROVED
    # --------------------------------------------------------

    with tab2:

        if not approved:

            st.info(
                "No approved schools yet."
            )

        else:

            rows = []

            for school in approved:

                rows.append(
                    {
                        "School":
                            school.get(
                                "school_name",
                                ""
                            ),

                        "School ID":
                            school.get(
                                "school_id",
                                ""
                            ),

                        "Admin ID":
                            school.get(
                                "admin_id",
                                ""
                            ),

                        "Status":
                            "Approved",
                    }
                )

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------------
    # REJECTED
    # --------------------------------------------------------

    with tab3:

        if not rejected:

            st.info(
                "No rejected schools."
            )

        else:

            for school in rejected:

                st.write(
                    f"❌ "
                    f"{school.get('school_name')} "
                    f"— {school.get('school_id')}"
                )

                if st.button(
                    "Restore to Pending",
                    key=(
                        "restore_"
                        +
                        school["school_id"]
                    )
                ):

                    db.table(
                        "schools"
                    ).update(
                        {
                            "approval_status":
                                "pending"
                        }
                    ).eq(
                        "school_id",
                        school[
                            "school_id"
                        ]
                    ).execute()

                    st.rerun()

    st.divider()

    if st.button(
        "🚪 Log Out"
    ):

        go_home()


# ============================================================
# SCHOOL LOGIN
# ============================================================

def school_login():

    school_id = (
        st.session_state.school_id
    )

    school = get_school(
        school_id
    )

    if not school:

        st.error(
            "School could not be found."
        )

        if st.button(
            "Return Home"
        ):

            go_home()

        return

    st.title(
        f"🏫 {school['school_name']}"
    )

    st.write(
        f"School ID: {school_id}"
    )

    if st.button(
        "← Change School"
    ):

        clear_login()

        st.session_state.screen = (
            "school_portal"
        )

        st.rerun()

    st.divider()

    admin_tab, teacher_tab = st.tabs(
        [
            "👨‍💼 School Admin",
            "👨‍🏫 Teacher",
        ]
    )

    # --------------------------------------------------------
    # SCHOOL ADMIN
    # --------------------------------------------------------

    with admin_tab:

        st.subheader(
            "School Admin Login"
        )

        admin_id = st.text_input(
            "Admin ID",
            key="school_admin_id"
        )

        password = st.text_input(
            "Admin Password",
            type="password",
            key="school_admin_password"
        )

        if st.button(
            "Login as Admin"
        ):

            admin_id = admin_id.strip()

            school_account = (
                get_school_by_admin(
                    school_id,
                    admin_id
                )
            )

            if (
                school_account
                and
                hash_password(password)
                ==
                school_account.get(
                    "admin_password_hash"
                )
            ):

                st.session_state.logged_in = True
                st.session_state.role = (
                    "School Admin"
                )

                st.session_state.user_id = (
                    admin_id
                )

                st.session_state.user_name = (
                    school["school_name"]
                    +
                    " Admin"
                )

                st.session_state.screen = (
                    "school_app"
                )

                st.rerun()

            else:

                st.error(
                    "Incorrect Admin ID or password."
                )

    # --------------------------------------------------------
    # TEACHER
    # --------------------------------------------------------

    with teacher_tab:

        st.subheader(
            "Teacher Login"
        )

        teacher_id = st.text_input(
            "Teacher ID",
            key="teacher_login_id"
        )

        password = st.text_input(
            "Teacher Password",
            type="password",
            key="teacher_login_password"
        )

        if st.button(
            "Login as Teacher"
        ):

            teacher_id = (
                teacher_id.strip()
            )

            teacher = get_teacher(
                school_id,
                teacher_id
            )

            if not teacher:

                st.error(
                    "Teacher account not found."
                )

            elif not teacher.get(
                "enabled",
                True
            ):

                st.error(
                    "This teacher account "
                    "is disabled."
                )

            elif (
                hash_password(password)
                !=
                teacher.get(
                    "password_hash"
                )
            ):

                st.error(
                    "Incorrect password."
                )

            else:

                st.session_state.logged_in = True
                st.session_state.role = "Teacher"

                st.session_state.user_id = (
                    teacher_id
                )

                st.session_state.user_name = (
                    teacher.get(
                        "teacher_name",
                        teacher_id
                    )
                )

                st.session_state.screen = (
                    "school_app"
                )

                st.rerun()


# ============================================================
# SCHOOL DASHBOARD
# ============================================================

def dashboard_page():

    students = load_students()
    attendance = load_attendance()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    present_today = 0

    if not attendance.empty:

        if "attendance_date" in attendance.columns:

            today_rows = attendance[
                attendance[
                    "attendance_date"
                ].astype(str)
                ==
                today
            ]

            if "status" in today_rows.columns:

                present_today = len(
                    today_rows[
                        today_rows["status"]
                        ==
                        "Present"
                    ]
                )

    st.title(
        f"🏫 {st.session_state.school_name}"
    )

    st.subheader(
        "EduVision Smart Classroom"
    )

    st.success(
        "🟢 System Online"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🎓 Students",
        len(students)
    )

    c2.metric(
        "✅ Present Today",
        present_today
    )

    c3.metric(
        "📋 Attendance Records",
        len(attendance)
    )

    c4.metric(
        "👤 Account",
        st.session_state.role
    )

    st.divider()

    st.subheader(
        "Welcome"
    )

    st.write(
        f"Signed in as "
        f"{st.session_state.user_name or st.session_state.user_id}."
    )

    st.info(
        "Use the sidebar to open Smart Attendance, "
        "Smart Occupancy, students and reports."
    )


# ============================================================
# STUDENTS
# ============================================================

def students_page():

    st.title(
        "🎓 Students"
    )

    students = load_students()

    if st.session_state.role == "School Admin":

        with st.expander(
            "➕ Add Student"
        ):

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID"
                )

                student_name = st.text_input(
                    "Student Name"
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

                student_name = (
                    student_name.strip()
                )

                if not student_id:

                    st.error(
                        "Enter Student ID."
                    )

                elif not student_name:

                    st.error(
                        "Enter student name."
                    )

                else:

                    try:

                        db.table(
                            "students"
                        ).insert(
                            {
                                "school_id":
                                    st.session_state.school_id,

                                "student_id":
                                    student_id,

                                "name":
                                    student_name,

                                "class_name":
                                    class_name.strip(),

                                "roll_no":
                                    roll_no.strip(),

                                "status":
                                    "Active",
                            }
                        ).execute()

                        st.success(
                            "Student added."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            "Could not add student."
                        )

                        st.code(
                            str(error)
                        )

    students = load_students()

    if students.empty:

        st.info(
            "No students added yet."
        )

    else:

        visible_columns = [
            column
            for column in [
                "student_id",
                "name",
                "class_name",
                "roll_no",
                "status",
            ]
            if column in students.columns
        ]

        st.dataframe(
            students[
                visible_columns
            ],
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # DELETE STUDENT
    # --------------------------------------------------------

    if (
        st.session_state.role
        ==
        "School Admin"
        and
        not students.empty
    ):

        st.divider()

        st.subheader(
            "🗑 Remove Student"
        )

        options = {}

        for _, student in students.iterrows():

            label = (
                f"{student.get('student_id', '')}"
                f" — "
                f"{student.get('name', '')}"
            )

            options[label] = (
                student.get(
                    "student_id"
                )
            )

        selected = st.selectbox(
            "Select Student",
            list(options.keys())
        )

        if st.button(
            "Remove Student"
        ):

            student_id = (
                options[selected]
            )

            try:

                db.table(
                    "students"
                ).delete().eq(
                    "school_id",
                    st.session_state.school_id
                ).eq(
                    "student_id",
                    student_id
                ).execute()

                st.success(
                    "Student removed."
                )

                st.rerun()

            except Exception as error:

                st.error(
                    str(error)
                )


# ============================================================
# TEACHERS
# ============================================================

def teachers_page():

    st.title(
        "👨‍🏫 Teacher Management"
    )

    try:

        response = (
            db.table("teachers")
            .select("*")
            .eq(
                "school_id",
                st.session_state.school_id
            )
            .order(
                "teacher_name"
            )
            .execute()
        )

        teachers = response.data or []

    except Exception as error:

        st.error(
            str(error)
        )

        teachers = []

    with st.expander(
        "➕ Add Teacher"
    ):

        teacher_id = st.text_input(
            "Teacher ID"
        )

        teacher_name = st.text_input(
            "Teacher Name"
        )

        password = st.text_input(
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
                    "Enter teacher name."
                )

            elif len(password) < 6:

                st.error(
                    "Password must contain "
                    "at least 6 characters."
                )

            else:

                try:

                    db.table(
                        "teachers"
                    ).insert(
                        {
                            "school_id":
                                st.session_state.school_id,

                            "teacher_id":
                                teacher_id,

                            "teacher_name":
                                teacher_name,

                            "password_hash":
                                hash_password(
                                    password
                                ),

                            "enabled":
                                True,
                        }
                    ).execute()

                    st.success(
                        "Teacher account created "
                        "and saved permanently."
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        "Could not create teacher."
                    )

                    st.code(
                        str(error)
                    )

    if not teachers:

        st.info(
            "No teacher accounts yet."
        )

        return

    rows = []

    for teacher in teachers:

        rows.append(
            {
                "Teacher ID":
                    teacher.get(
                        "teacher_id",
                        ""
                    ),

                "Name":
                    teacher.get(
                        "teacher_name",
                        ""
                    ),

                "Status":
                    (
                        "Enabled"
                        if teacher.get(
                            "enabled",
                            True
                        )
                        else
                        "Disabled"
                    ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    teacher_options = {}

    for teacher in teachers:

        label = (
            f"{teacher.get('teacher_id')} "
            f"— "
            f"{teacher.get('teacher_name')}"
        )

        teacher_options[
            label
        ] = teacher

    selected_label = st.selectbox(
        "Manage Teacher",
        list(
            teacher_options.keys()
        )
    )

    selected_teacher = (
        teacher_options[
            selected_label
        ]
    )

    c1, c2 = st.columns(2)

    with c1:

        enabled = selected_teacher.get(
            "enabled",
            True
        )

        button_text = (
            "Disable Teacher"
            if enabled
            else
            "Enable Teacher"
        )

        if st.button(
            button_text
        ):

            db.table(
                "teachers"
            ).update(
                {
                    "enabled":
                        not enabled
                }
            ).eq(
                "school_id",
                st.session_state.school_id
            ).eq(
                "teacher_id",
                selected_teacher[
                    "teacher_id"
                ]
            ).execute()

            st.rerun()

    with c2:

        if st.button(
            "🗑 Delete Teacher"
        ):

            db.table(
                "teachers"
            ).delete().eq(
                "school_id",
                st.session_state.school_id
            ).eq(
                "teacher_id",
                selected_teacher[
                    "teacher_id"
                ]
            ).execute()

            st.rerun()


# ============================================================
# ATTENDANCE
# ============================================================

def attendance_page():

    st.title(
        "📷 Smart Attendance"
    )

    st.write(
        "Use AI face recognition or manually "
        "record attendance."
    )

    students = load_students()

    camera_tab, manual_tab, history_tab = (
        st.tabs(
            [
                "🤖 AI Camera",
                "✋ Manual",
                "📋 History",
            ]
        )
    )

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    with camera_tab:

        st.info(
            "AI camera module"
        )

        try:

            from smart_attendance import render_page

            render_page()

        except Exception as error:

            st.error(
                "AI Attendance could not start."
            )

            st.code(
                str(error)
            )

    # --------------------------------------------------------
    # MANUAL
    # --------------------------------------------------------

    with manual_tab:

        if students.empty:

            st.warning(
                "Add a student first."
            )

        else:

            options = {}

            for _, student in students.iterrows():

                label = (
                    f"{student.get('student_id', '')}"
                    f" — "
                    f"{student.get('name', '')}"
                )

                options[label] = student

            selected = st.selectbox(
                "Student",
                list(options.keys())
            )

            status = st.selectbox(
                "Status",
                [
                    "Present",
                    "Late",
                    "Absent",
                ]
            )

            if st.button(
                "✅ Save Attendance"
            ):

                student = options[
                    selected
                ]

                now = datetime.now()

                attendance_date = (
                    now.strftime(
                        "%Y-%m-%d"
                    )
                )

                attendance_time = (
                    now.strftime(
                        "%H:%M:%S"
                    )
                )

                record = {
                    "school_id":
                        st.session_state.school_id,

                    "student_id":
                        student.get(
                            "student_id",
                            ""
                        ),

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

                    "attendance_date":
                        attendance_date,

                    "attendance_time":
                        attendance_time,

                    "status":
                        status,
                }

                try:

                    existing = (
                        db.table(
                            "attendance"
                        )
                        .select("id")
                        .eq(
                            "school_id",
                            st.session_state.school_id
                        )
                        .eq(
                            "student_id",
                            record[
                                "student_id"
                            ]
                        )
                        .eq(
                            "attendance_date",
                            attendance_date
                        )
                        .execute()
                    )

                    if existing.data:

                        db.table(
                            "attendance"
                        ).update(
                            {
                                "name":
                                    record["name"],

                                "class_name":
                                    record[
                                        "class_name"
                                    ],

                                "attendance_time":
                                    attendance_time,

                                "status":
                                    status,
                            }
                        ).eq(
                            "id",
                            existing.data[0][
                                "id"
                            ]
                        ).execute()

                    else:

                        db.table(
                            "attendance"
                        ).insert(
                            record
                        ).execute()

                    st.success(
                        f"{record['name']} marked "
                        f"{status}."
                    )

                except Exception as error:

                    st.error(
                        "Could not save attendance."
                    )

                    st.code(
                        str(error)
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

            columns = [
                column
                for column in [
                    "student_id",
                    "name",
                    "class_name",
                    "attendance_date",
                    "attendance_time",
                    "status",
                ]
                if column
                in attendance.columns
            ]

            st.dataframe(
                attendance[columns],
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# SMART OCCUPANCY
# ============================================================

def occupancy_page():

    st.title(
        "👥 Smart Occupancy"
    )

    st.write(
        "AI-powered classroom person detection."
    )

    try:

        from smart_occupancy import render_page

        render_page()

    except Exception as error:

        st.error(
            "Smart Occupancy could not start."
        )

        st.code(
            str(error)
        )


# ============================================================
# REPORTS
# ============================================================

def reports_page():

    st.title(
        "📊 Reports"
    )

    students = load_students()
    attendance = load_attendance()

    total_records = len(
        attendance
    )

    present = 0

    if (
        not attendance.empty
        and
        "status"
        in attendance.columns
    ):

        present = len(
            attendance[
                attendance["status"]
                ==
                "Present"
            ]
        )

    if total_records:

        percentage = round(
            (
                present
                /
                total_records
            )
            *
            100,
            1
        )

    else:

        percentage = 0

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Students",
        len(students)
    )

    c2.metric(
        "Attendance Records",
        total_records
    )

    c3.metric(
        "Present %",
        f"{percentage}%"
    )

    st.divider()

    if attendance.empty:

        st.info(
            "No attendance records yet."
        )

    else:

        display_columns = [
            column
            for column in [
                "student_id",
                "name",
                "class_name",
                "attendance_date",
                "attendance_time",
                "status",
            ]
            if column
            in attendance.columns
        ]

        st.dataframe(
            attendance[
                display_columns
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# SETTINGS
# ============================================================

def settings_page():

    st.title(
        "⚙️ Settings"
    )

    st.subheader(
        "Account"
    )

    st.write(
        "School:",
        st.session_state.school_name
    )

    st.write(
        "School ID:",
        st.session_state.school_id
    )

    st.write(
        "Role:",
        st.session_state.role
    )

    st.write(
        "User:",
        st.session_state.user_name
        or
        st.session_state.user_id
    )

    st.divider()

    st.success(
        "☁️ School accounts, teachers, students "
        "and attendance are connected to the "
        "EduVision cloud database."
    )


# ============================================================
# SCHOOL APPLICATION
# ============================================================

def school_application():

    with st.sidebar:

        st.title(
            "🎓 EduVision"
        )

        st.caption(
            st.session_state.school_name
        )

        st.write(
            f"👤 {st.session_state.role}"
        )

        st.divider()

        if (
            st.session_state.role
            ==
            "School Admin"
        ):

            pages = [
                "🏠 Dashboard",
                "🎓 Students",
                "👨‍🏫 Teachers",
                "📷 Smart Attendance",
                "👥 Smart Occupancy",
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

            clear_login()

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    if page == "🏠 Dashboard":

        dashboard_page()

    elif page == "🎓 Students":

        students_page()

    elif page == "👨‍🏫 Teachers":

        if (
            st.session_state.role
            ==
            "School Admin"
        ):

            teachers_page()

        else:

            st.error(
                "School Admin access required."
            )

    elif page == "📷 Smart Attendance":

        attendance_page()

    elif page == "👥 Smart Occupancy":

        occupancy_page()

    elif page == "📊 Reports":

        reports_page()

    elif page == "⚙️ Settings":

        settings_page()


# ============================================================
# ROUTER
# ============================================================

screen = st.session_state.screen


if screen == "home":

    home_page()


elif screen == "school_portal":

    school_portal()


elif screen == "platform_admin_login":

    platform_admin_login()


elif (
    screen == "platform_admin"
    and
    st.session_state.logged_in
    and
    st.session_state.role
    ==
    "EduVision Admin"
):

    platform_admin_page()


elif screen == "school_login":

    school_login()


elif (
    screen == "school_app"
    and
    st.session_state.logged_in
):

    school_application()


else:

    go_home()

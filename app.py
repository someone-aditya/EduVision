import os
import sys
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None


# ============================================================
# APP DIRECTORY
# ============================================================

APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EduVision — Smart Classroom Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURATION
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

try:
    if not SUPABASE_URL and "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = str(st.secrets["SUPABASE_URL"])

    if not SUPABASE_KEY and "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = str(st.secrets["SUPABASE_KEY"])
except Exception:
    pass


EDUVISION_ADMIN_ID = os.getenv(
    "EDUVISION_ADMIN_ID",
    "12126"
)

EDUVISION_ADMIN_PASSWORD = os.getenv(
    "EDUVISION_ADMIN_PASSWORD",
    "12126"
)

try:
    if (
        not os.getenv("EDUVISION_ADMIN_ID")
        and "EDUVISION_ADMIN_ID" in st.secrets
    ):
        EDUVISION_ADMIN_ID = str(
            st.secrets["EDUVISION_ADMIN_ID"]
        )

    if (
        not os.getenv("EDUVISION_ADMIN_PASSWORD")
        and "EDUVISION_ADMIN_PASSWORD" in st.secrets
    ):
        EDUVISION_ADMIN_PASSWORD = str(
            st.secrets["EDUVISION_ADMIN_PASSWORD"]
        )
except Exception:
    pass


# ============================================================
# SUPABASE
# ============================================================

def clean_supabase_url(url):
    if not url:
        return ""

    url = str(url).strip().strip("'\"")

    if url.endswith("/rest/v1"):
        url = url[:-8]

    return url.rstrip("/")


def clean_supabase_key(key):
    if not key:
        return ""

    return str(key).strip().strip("'\"")


@st.cache_resource
def get_database():

    if create_client is None:
        raise RuntimeError(
            "The supabase library is not installed."
        )

    url = clean_supabase_url(SUPABASE_URL)
    key = clean_supabase_key(SUPABASE_KEY)

    if not url:
        raise RuntimeError("SUPABASE_URL is missing.")

    if not key:
        raise RuntimeError("SUPABASE_KEY is missing.")

    return create_client(url, key)


db = None
db_error_message = None

try:
    db = get_database()
except Exception as error:
    db_error_message = str(error)


# ============================================================
# SIMPLE WHITE UI
# ============================================================

st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #f7f7f5 !important;
    color: #111111 !important;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

h1, h2, h3 {
    color: #111111 !important;
}

p {
    color: #374151;
}

label {
    color: #374151 !important;
}

div.stButton > button {
    width: 100%;
    min-height: 42px;
    background: #111111 !important;
    color: white !important;
    border: 1px solid #111111 !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}

div.stButton > button:hover {
    background: #333333 !important;
    color: white !important;
    border-color: #333333 !important;
}

div[data-baseweb="input"] {
    background: white !important;
    border-radius: 6px !important;
}

div[data-baseweb="input"] input {
    background: white !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

div[data-baseweb="select"] > div {
    background: white !important;
    color: #111111 !important;
}

[data-testid="stMetric"] {
    background: white !important;
    border: 1px solid #dedede !important;
    border-radius: 8px !important;
    padding: 16px !important;
}

[data-testid="stSidebar"] {
    background: white !important;
    border-right: 1px solid #dedede !important;
}

[data-testid="stSidebar"] * {
    color: #111111;
}

[data-testid="stExpander"] {
    background: white !important;
    border: 1px solid #dedede !important;
    border-radius: 8px !important;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SECURITY
# ============================================================

def hash_password(password):
    return hashlib.sha256(
        str(password).encode("utf-8")
    ).hexdigest()


def generate_school_id():
    return "SCH-" + secrets.token_hex(3).upper()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_SESSION = {
    "screen": "welcome",
    "logged_in": False,
    "role": None,
    "school_id": None,
    "school_name": None,
    "user_id": None,
    "user_name": None,
    "nav_page": "Dashboard",
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
    st.session_state.nav_page = "Dashboard"

    if "sidebar_nav_radio" in st.session_state:
        del st.session_state["sidebar_nav_radio"]


def go_portal():
    clear_login()
    st.session_state.screen = "portal"
    st.rerun()


def go_welcome():
    clear_login()
    st.session_state.screen = "welcome"
    st.rerun()


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_school(school_id):

    if not db or not school_id:
        return None

    try:
        response = (
            db.table("schools")
            .select("*")
            .eq("school_id", str(school_id).strip())
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print("get_school:", error)

    return None


def get_school_by_admin(school_id, admin_id):

    if not db:
        return None

    try:
        response = (
            db.table("schools")
            .select("*")
            .eq("school_id", str(school_id).strip())
            .eq("admin_id", str(admin_id).strip())
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print("get_school_by_admin:", error)

    return None


def get_teacher(school_id, teacher_id):

    if not db:
        return None

    try:
        response = (
            db.table("teachers")
            .select("*")
            .eq("school_id", str(school_id).strip())
            .eq("teacher_id", str(teacher_id).strip())
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print("get_teacher:", error)

    return None


def load_students():

    if not db or not st.session_state.school_id:
        return pd.DataFrame()

    try:
        response = (
            db.table("students")
            .select("*")
            .eq(
                "school_id",
                st.session_state.school_id
            )
            .execute()
        )

        if response.data:
            return pd.DataFrame(response.data)

    except Exception as error:
        st.error(
            f"Could not load students: {error}"
        )

    return pd.DataFrame()


def load_attendance():

    if not db or not st.session_state.school_id:
        return pd.DataFrame()

    try:
        response = (
            db.table("attendance")
            .select("*")
            .eq(
                "school_id",
                st.session_state.school_id
            )
            .execute()
        )

        if response.data:
            df = pd.DataFrame(response.data)

            if "attendance_date" in df.columns:
                df = df.sort_values(
                    "attendance_date",
                    ascending=False
                )

            return df

    except Exception as error:
        st.error(
            f"Could not load attendance: {error}"
        )

    return pd.DataFrame()


# ============================================================
# WELCOME
# ============================================================

def welcome_screen():

    st.write("")
    st.write("")

    _, center, _ = st.columns([1, 2, 1])

    with center:

        st.caption("AI • SMART CLASSROOM")

        st.title("EduVision")

        st.write(
            "Smarter classrooms through fast attendance, "
            "classroom monitoring and simple management."
        )

        st.write("")

        if st.button(
            "Enter EduVision →",
            key="enter_eduvision_btn",
            use_container_width=True
        ):
            st.session_state.screen = "portal"
            st.rerun()

        st.success("System Online")


# ============================================================
# PORTAL
# ============================================================

def portal_screen():

    title_col, back_col = st.columns([4, 1])

    with title_col:
        st.title("EduVision")

    with back_col:
        if st.button(
            "← Back",
            key="portal_back_welcome"
        ):
            go_welcome()

    st.header("Choose your workspace")
    st.caption(
        "Select how you want to access EduVision."
    )

    st.write("")

    school_col, admin_col = st.columns(
        2,
        gap="large"
    )

    with school_col:

        with st.container(border=True):

            st.subheader("School Portal")

            st.write(
                "Access your school workspace for "
                "attendance, students and classroom management."
            )

        if st.button(
            "Open School Portal →",
            key="open_school_portal_btn"
        ):
            st.session_state.screen = "school_portal"
            st.rerun()

    with admin_col:

        with st.container(border=True):

            st.subheader("EduVision Admin")

            st.write(
                "Review and manage school registration requests."
            )

        if st.button(
            "Open Admin →",
            key="open_admin_portal_btn"
        ):
            st.session_state.screen = "platform_admin_login"
            st.rerun()


# ============================================================
# SCHOOL PORTAL
# ============================================================

def school_portal():

    c1, c2 = st.columns([4, 1])

    with c1:
        st.title("School Portal")
        st.caption(
            "Register a school or access an approved school."
        )

    with c2:
        if st.button(
            "← Back",
            key="school_portal_back"
        ):
            go_portal()

    st.divider()

    register_tab, open_tab = st.tabs(
        ["Register School", "Open School"]
    )

    # REGISTER SCHOOL
    with register_tab:

        st.subheader("Create a school workspace")

        st.caption(
            "Registration must be approved before "
            "the school can be accessed."
        )

        c1, c2 = st.columns(2)

        with c1:
            school_name = st.text_input(
                "School Name",
                placeholder="Enter school name"
            )

            admin_id = st.text_input(
                "School Admin ID",
                placeholder="Create admin ID"
            )

        with c2:
            admin_password = st.text_input(
                "Admin Password",
                type="password",
                placeholder="Minimum 6 characters"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Repeat password"
            )

        if st.button(
            "Submit Registration",
            key="submit_school_registration"
        ):

            school_name = school_name.strip()
            admin_id = admin_id.strip()

            if not school_name:
                st.error("Enter the school name.")

            elif not admin_id:
                st.error("Enter an Admin ID.")

            elif len(admin_password) < 6:
                st.error(
                    "Password must contain at least 6 characters."
                )

            elif admin_password != confirm_password:
                st.error("Passwords do not match.")

            elif not db:
                st.error("Database unavailable.")

            else:

                school_id = generate_school_id()

                try:
                    db.table("schools").insert({
                        "school_id": school_id,
                        "school_name": school_name,
                        "admin_id": admin_id,
                        "admin_password_hash":
                            hash_password(admin_password),
                        "approval_status": "pending",
                    }).execute()

                    st.success(
                        "School registration submitted."
                    )

                    with st.container(border=True):
                        st.caption("SAVE THESE DETAILS")
                        st.subheader(
                            f"School ID: {school_id}"
                        )
                        st.write(
                            f"Admin ID: **{admin_id}**"
                        )

                except Exception as error:
                    st.error(
                        f"Registration failed: {error}"
                    )

    # OPEN SCHOOL
    with open_tab:

        st.subheader("Open your school")

        st.caption(
            "Select an approved school to continue."
        )

        approved_schools = []

        if db:
            try:
                response = (
                    db.table("schools")
                    .select(
                        "school_id,school_name"
                    )
                    .eq(
                        "approval_status",
                        "approved"
                    )
                    .execute()
                )

                approved_schools = (
                    response.data or []
                )

            except Exception as error:
                st.error(
                    f"Could not load schools: {error}"
                )

        if not approved_schools:
            st.info(
                "No approved schools are currently available."
            )

        else:

            school_map = {
                school["school_name"]:
                    school["school_id"]
                for school in approved_schools
            }

            selected_name = st.selectbox(
                "School",
                sorted(school_map.keys())
            )

            if st.button(
                "Continue →",
                key="continue_school"
            ):

                school_id = school_map[selected_name]

                school = get_school(school_id)

                if school:

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

                else:
                    st.error(
                        "School could not be found."
                    )


# ============================================================
# SCHOOL LOGIN
# ============================================================

def school_login():

    school_id = st.session_state.school_id
    school = get_school(school_id)

    if not school:

        st.error("School workspace not found.")

        if st.button("Return to School Portal"):
            st.session_state.screen = "school_portal"
            st.rerun()

        return

    c1, c2 = st.columns([4, 1])

    with c1:
        st.title(school["school_name"])
        st.caption(
            f"School ID: {school_id}"
        )

    with c2:
        if st.button(
            "← Change School",
            key="change_school"
        ):
            clear_login()
            st.session_state.screen = "school_portal"
            st.rerun()

    st.divider()

    admin_tab, teacher_tab = st.tabs(
        ["School Admin", "Teacher"]
    )

    # ADMIN LOGIN
    with admin_tab:

        _, center, _ = st.columns([1, 2, 1])

        with center:

            st.subheader("Admin Login")

            st.caption(
                "Sign in to manage your school."
            )

            admin_id = st.text_input(
                "Admin ID",
                key="school_admin_login_id"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="school_admin_login_password"
            )

            if st.button(
                "Login",
                key="school_admin_login"
            ):

                admin_id = admin_id.strip()

                account = get_school_by_admin(
                    school_id,
                    admin_id
                )

                if (
                    account
                    and hash_password(password)
                    == account.get(
                        "admin_password_hash"
                    )
                ):

                    st.session_state.logged_in = True
                    st.session_state.role = "School Admin"
                    st.session_state.user_id = admin_id
                    st.session_state.user_name = (
                        f"{school['school_name']} Admin"
                    )
                    st.session_state.nav_page = "Dashboard"
                    st.session_state.screen = "school_app"

                    if "sidebar_nav_radio" in st.session_state:
                        del st.session_state[
                            "sidebar_nav_radio"
                        ]

                    st.rerun()

                else:
                    st.error(
                        "Incorrect Admin ID or password."
                    )

    # TEACHER LOGIN
    with teacher_tab:

        _, center, _ = st.columns([1, 2, 1])

        with center:

            st.subheader("Teacher Login")

            st.caption(
                "Sign in to access your classroom."
            )

            teacher_id = st.text_input(
                "Teacher ID",
                key="teacher_login_id"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="teacher_login_password"
            )

            if st.button(
                "Login",
                key="teacher_login"
            ):

                teacher_id = teacher_id.strip()

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
                        "This teacher account is disabled."
                    )

                elif (
                    hash_password(password)
                    != teacher.get("password_hash")
                ):
                    st.error(
                        "Incorrect password."
                    )

                else:

                    st.session_state.logged_in = True
                    st.session_state.role = "Teacher"
                    st.session_state.user_id = teacher_id

                    st.session_state.user_name = (
                        teacher.get("teacher_name")
                        or teacher.get("name")
                        or teacher_id
                    )

                    st.session_state.nav_page = "Dashboard"
                    st.session_state.screen = "school_app"

                    if "sidebar_nav_radio" in st.session_state:
                        del st.session_state[
                            "sidebar_nav_radio"
                        ]

                    st.rerun()


# ============================================================
# EDUVISION ADMIN LOGIN
# ============================================================

def platform_admin_login():

    c1, c2 = st.columns([4, 1])

    with c1:
        st.title("EduVision Admin")
        st.caption(
            "Manage school registrations."
        )

    with c2:
        if st.button(
            "← Back",
            key="platform_admin_back"
        ):
            go_portal()

    st.divider()

    _, center, _ = st.columns([1, 2, 1])

    with center:

        st.subheader("Admin Login")

        admin_id = st.text_input(
            "Admin ID",
            key="platform_admin_id"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="platform_admin_password"
        )

        if st.button(
            "Login",
            key="platform_admin_login_button"
        ):

            if (
                admin_id.strip() == EDUVISION_ADMIN_ID
                and password == EDUVISION_ADMIN_PASSWORD
            ):

                st.session_state.logged_in = True
                st.session_state.role = "EduVision Admin"
                st.session_state.user_id = admin_id.strip()
                st.session_state.screen = "platform_admin"

                st.rerun()

            else:
                st.error(
                    "Incorrect Admin ID or password."
                )


# ============================================================
# EDUVISION ADMIN PAGE
# ============================================================

def platform_admin_page():

    c1, c2 = st.columns([4, 1])

    with c1:
        st.title("EduVision Admin")
        st.caption(
            "Review and manage school registration requests."
        )

    with c2:
        if st.button(
            "Log Out",
            key="platform_logout"
        ):
            go_portal()

    st.divider()

    schools = []

    if db:
        try:
            response = (
                db.table("schools")
                .select("*")
                .execute()
            )

            schools = response.data or []

        except Exception as error:
            st.error(
                f"Could not load schools: {error}"
            )

    pending = [
        s for s in schools
        if str(
            s.get("approval_status", "")
        ).lower() == "pending"
    ]

    approved = [
        s for s in schools
        if str(
            s.get("approval_status", "")
        ).lower() == "approved"
    ]

    rejected = [
        s for s in schools
        if str(
            s.get("approval_status", "")
        ).lower() == "rejected"
    ]

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            "Pending Requests",
            len(pending)
        )

    with m2:
        st.metric(
            "Approved Schools",
            len(approved)
        )

    with m3:
        st.metric(
            "Rejected Requests",
            len(rejected)
        )

    tab1, tab2, tab3 = st.tabs([
        f"Pending ({len(pending)})",
        f"Approved ({len(approved)})",
        f"Rejected ({len(rejected)})",
    ])

    # PENDING
    with tab1:

        st.subheader("Pending Registrations")

        if not pending:
            st.info(
                "No school registrations are waiting for approval."
            )

        for school in pending:

            sid = school.get("school_id", "")
            name = school.get(
                "school_name",
                "Unnamed School"
            )
            aid = school.get("admin_id", "")

            with st.container(border=True):

                st.subheader(name)
                st.write(
                    f"**School ID:** {sid}"
                )
                st.write(
                    f"**Admin ID:** {aid}"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "Approve",
                        key=f"approve_{sid}"
                    ):

                        try:

                            try:
                                db.table(
                                    "schools"
                                ).update({
                                    "approval_status":
                                        "approved",
                                    "approved_by":
                                        st.session_state.user_id,
                                    "approved_at":
                                        datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                }).eq(
                                    "school_id",
                                    sid
                                ).execute()

                            except Exception:
                                db.table(
                                    "schools"
                                ).update({
                                    "approval_status":
                                        "approved"
                                }).eq(
                                    "school_id",
                                    sid
                                ).execute()

                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"Approval failed: {error}"
                            )

                with c2:

                    if st.button(
                        "Reject",
                        key=f"reject_{sid}"
                    ):

                        try:
                            db.table(
                                "schools"
                            ).update({
                                "approval_status":
                                    "rejected"
                            }).eq(
                                "school_id",
                                sid
                            ).execute()

                            st.rerun()

                        except Exception as error:
                            st.error(str(error))

    # APPROVED
    with tab2:

        st.subheader("Approved Schools")

        if not approved:
            st.info(
                "No schools have been approved yet."
            )

        else:

            rows = []

            for school in approved:
                rows.append({
                    "School Name":
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
                })

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )

    # REJECTED
    with tab3:

        st.subheader("Rejected Schools")

        if not rejected:
            st.info(
                "No rejected school registrations."
            )

        for school in rejected:

            sid = school.get("school_id", "")
            name = school.get(
                "school_name",
                ""
            )

            with st.container(border=True):

                st.subheader(name)
                st.write(
                    f"**School ID:** {sid}"
                )

                if st.button(
                    "Restore to Pending",
                    key=f"restore_{sid}"
                ):

                    try:
                        db.table(
                            "schools"
                        ).update({
                            "approval_status":
                                "pending"
                        }).eq(
                            "school_id",
                            sid
                        ).execute()

                        st.rerun()

                    except Exception as error:
                        st.error(str(error))


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():

    students = load_students()
    attendance = load_attendance()

    # Count only approved/active students
    if (
        not students.empty
        and "status" in students.columns
    ):
        student_status = (
            students["status"]
            .fillna("Active")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        active_students = students[
            ~student_status.isin(
                ["pending", "declined"]
            )
        ]

    else:
        active_students = students

    total_students = len(active_students)

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    present = 0
    late = 0
    absent = 0

    if (
        not attendance.empty
        and "attendance_date"
        in attendance.columns
    ):

        today_rows = attendance[
            attendance["attendance_date"]
            .astype(str) == today
        ]

        if "status" in today_rows.columns:

            statuses = (
                today_rows["status"]
                .astype(str)
                .str.lower()
            )

            present = (
                statuses == "present"
            ).sum()

            late = (
                statuses == "late"
            ).sum()

            absent = (
                statuses == "absent"
            ).sum()

    percentage = (
        round(
            (present / total_students) * 100,
            1
        )
        if total_students
        else 0.0
    )

    hour = datetime.now().hour

    if hour < 12:
        greeting = "Good Morning"
    elif hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    user = (
        st.session_state.user_name
        or st.session_state.user_id
        or "Educator"
    )

    st.title(
        f"{greeting}, {user}"
    )

    st.caption(
        st.session_state.school_name
    )

    st.subheader("Today's Overview")

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            "Students",
            total_students
        )

    with m2:
        st.metric(
            "Present",
            int(present)
        )

    with m3:
        st.metric(
            "Absent",
            int(absent)
        )

    with m4:
        st.metric(
            "Attendance",
            f"{percentage}%"
        )

    with st.container(border=True):

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Present",
                int(present)
            )

        with c2:
            st.metric(
                "Late",
                int(late)
            )

        with c3:
            st.metric(
                "Absent",
                int(absent)
            )

    st.subheader("Quick Actions")

    c1, c2 = st.columns(2)

    with c1:

        with st.container(border=True):
            st.subheader(
                "Smart Attendance"
            )
            st.write(
                "Take and review classroom attendance."
            )

        if st.button(
            "Open Attendance →",
            key="dashboard_attendance"
        ):
            st.session_state.nav_page = (
                "Smart Attendance"
            )

            if "sidebar_nav_radio" in st.session_state:
                del st.session_state[
                    "sidebar_nav_radio"
                ]

            st.rerun()

    with c2:

        with st.container(border=True):
            st.subheader(
                "Smart Occupancy"
            )
            st.write(
                "Monitor classroom occupancy "
                "and room status."
            )

        if st.button(
            "Open Occupancy →",
            key="dashboard_occupancy"
        ):
            st.session_state.nav_page = (
                "Smart Occupancy"
            )

            if "sidebar_nav_radio" in st.session_state:
                del st.session_state[
                    "sidebar_nav_radio"
                ]

            st.rerun()


# ============================================================
# STUDENTS
# ============================================================

def students_page():

    is_admin = (
        st.session_state.role
        == "School Admin"
    )

    is_teacher = (
        st.session_state.role
        == "Teacher"
    )

    st.title("Students")

    st.caption(
        "View and manage student registrations."
    )

    students = load_students()

    if students.empty:

        pending_students = pd.DataFrame()
        active_students = pd.DataFrame()
        declined_students = pd.DataFrame()

    elif "status" not in students.columns:

        pending_students = pd.DataFrame()
        declined_students = pd.DataFrame()
        active_students = students.copy()

    else:

        status = (
            students["status"]
            .fillna("Active")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        pending_students = students[
            status == "pending"
        ].copy()

        declined_students = students[
            status == "declined"
        ].copy()

        active_students = students[
            ~status.isin(
                ["pending", "declined"]
            )
        ].copy()

    m1, m2 = st.columns(2)

    with m1:
        st.metric(
            "Active Students",
            len(active_students)
        )

    with m2:
        st.metric(
            "Pending Approval",
            len(pending_students)
        )

    # TEACHER REGISTRATION
    if is_teacher:

        with st.expander(
            "Register New Student"
        ):

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID",
                    key="new_student_id"
                )

                student_name = st.text_input(
                    "Full Name",
                    key="new_student_name"
                )

            with c2:

                class_name = st.text_input(
                    "Class / Grade",
                    key="new_student_class"
                )

                roll_no = st.text_input(
                    "Roll Number",
                    key="new_student_roll"
                )

            if st.button(
                "Submit for Approval",
                key="submit_new_student"
            ):

                student_id = student_id.strip()
                student_name = student_name.strip()
                class_name = class_name.strip()
                roll_no = roll_no.strip()

                if not student_id:
                    st.error(
                        "Enter a Student ID."
                    )

                elif not student_name:
                    st.error(
                        "Enter the student's name."
                    )

                elif not class_name:
                    st.error(
                        "Enter the class."
                    )

                elif not db:
                    st.error(
                        "Database unavailable."
                    )

                else:

                    try:
                        db.table(
                            "students"
                        ).insert({
                            "school_id":
                                st.session_state.school_id,
                            "student_id":
                                student_id,
                            "name":
                                student_name,
                            "class_name":
                                class_name,
                            "roll_no":
                                roll_no,
                            "status":
                                "Pending",
                        }).execute()

                        st.success(
                            "Student submitted for approval."
                        )

                        st.rerun()

                    except Exception as error:
                        st.error(
                            f"Could not register student: {error}"
                        )

    # ADMIN APPROVAL
    if is_admin:

        st.subheader(
            "Pending Registrations"
        )

        if pending_students.empty:

            st.info(
                "No student registrations "
                "are waiting for approval."
            )

        else:

            columns = [
                c for c in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status",
                ]
                if c in pending_students.columns
            ]

            st.dataframe(
                pending_students[columns],
                use_container_width=True,
                hide_index=True
            )

            options = {}

            for _, row in pending_students.iterrows():

                sid = row.get(
                    "student_id",
                    ""
                )

                name = row.get(
                    "name",
                    ""
                )

                options[
                    f"{sid} — {name}"
                ] = sid

            selected = st.selectbox(
                "Select Student",
                list(options.keys()),
                key="pending_student_select"
            )

            sid = options[selected]

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "Approve",
                    key="approve_student"
                ):

                    try:
                        db.table(
                            "students"
                        ).update({
                            "status": "Active"
                        }).eq(
                            "school_id",
                            st.session_state.school_id
                        ).eq(
                            "student_id",
                            sid
                        ).execute()

                        st.rerun()

                    except Exception as error:
                        st.error(str(error))

            with c2:

                if st.button(
                    "Decline",
                    key="decline_student"
                ):

                    try:
                        db.table(
                            "students"
                        ).update({
                            "status": "Declined"
                        }).eq(
                            "school_id",
                            st.session_state.school_id
                        ).eq(
                            "student_id",
                            sid
                        ).execute()

                        st.rerun()

                    except Exception as error:
                        st.error(str(error))

    # ACTIVE STUDENTS
    st.subheader("Active Students")

    if active_students.empty:

        st.info(
            "No approved students are currently registered."
        )

    else:

        columns = [
            c for c in [
                "student_id",
                "name",
                "class_name",
                "roll_no",
                "status",
            ]
            if c in active_students.columns
        ]

        st.dataframe(
            active_students[columns],
            use_container_width=True,
            hide_index=True
        )

    # TEACHER PENDING
    if (
        is_teacher
        and not pending_students.empty
    ):

        with st.expander(
            f"Pending Registrations "
            f"({len(pending_students)})"
        ):

            columns = [
                c for c in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status",
                ]
                if c in pending_students.columns
            ]

            st.dataframe(
                pending_students[columns],
                use_container_width=True,
                hide_index=True
            )

    # ADMIN REMOVE
    if is_admin and not students.empty:

        st.divider()

        with st.expander(
            "Remove Student"
        ):

            student_map = {}

            for _, row in students.iterrows():

                sid = row.get(
                    "student_id",
                    ""
                )

                name = row.get(
                    "name",
                    ""
                )

                student_map[
                    f"{sid} — {name}"
                ] = sid

            selected = st.selectbox(
                "Student",
                list(student_map.keys()),
                key="remove_student_select"
            )

            if st.button(
                "Remove Student",
                key="remove_student_button"
            ):

                sid = student_map[selected]

                try:
                    db.table(
                        "students"
                    ).delete().eq(
                        "school_id",
                        st.session_state.school_id
                    ).eq(
                        "student_id",
                        sid
                    ).execute()

                    st.rerun()

                except Exception as error:
                    st.error(str(error))


# ============================================================
# TEACHERS
# ============================================================

def teachers_page():

    if st.session_state.role != "School Admin":

        st.error(
            "School Admin access required."
        )
        return

    st.title("Teachers")

    st.caption(
        "Create and manage teacher accounts."
    )

    teachers = []

    if db:

        try:
            response = (
                db.table("teachers")
                .select("*")
                .eq(
                    "school_id",
                    st.session_state.school_id
                )
                .execute()
            )

            teachers = response.data or []

        except Exception as error:
            st.error(
                f"Could not load teachers: {error}"
            )

    active = [
        teacher
        for teacher in teachers
        if teacher.get("enabled", True)
    ]

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Total Teachers",
            len(teachers)
        )

    with c2:
        st.metric(
            "Active Accounts",
            len(active)
        )

    with st.expander(
        "Create Teacher Account"
    ):

        c1, c2 = st.columns(2)

        with c1:

            teacher_id = st.text_input(
                "Teacher ID",
                key="create_teacher_id"
            )

            teacher_name = st.text_input(
                "Teacher Name",
                key="create_teacher_name"
            )

        with c2:

            teacher_password = st.text_input(
                "Temporary Password",
                type="password",
                key="create_teacher_password"
            )

        if st.button(
            "Create Teacher",
            key="create_teacher_button"
        ):

            teacher_id = teacher_id.strip()
            teacher_name = teacher_name.strip()

            if not teacher_id:
                st.error(
                    "Enter a Teacher ID."
                )

            elif not teacher_name:
                st.error(
                    "Enter the teacher's name."
                )

            elif len(teacher_password) < 6:
                st.error(
                    "Password must contain at least 6 characters."
                )

            else:

                try:
                    db.table(
                        "teachers"
                    ).insert({
                        "school_id":
                            st.session_state.school_id,
                        "teacher_id":
                            teacher_id,
                        "teacher_name":
                            teacher_name,
                        "password_hash":
                            hash_password(
                                teacher_password
                            ),
                        "enabled":
                            True,
                    }).execute()

                    st.success(
                        "Teacher account created."
                    )

                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Could not create teacher: {error}"
                    )

    st.subheader("Teacher Accounts")

    if not teachers:

        st.info(
            "No teacher accounts have been created yet."
        )
        return

    rows = []

    for teacher in teachers:

        name = (
            teacher.get("teacher_name")
            or teacher.get("name")
            or teacher.get("teacher_id", "")
        )

        rows.append({
            "Teacher ID":
                teacher.get(
                    "teacher_id",
                    ""
                ),
            "Name":
                name,
            "Status":
                "Enabled"
                if teacher.get(
                    "enabled",
                    True
                )
                else "Disabled",
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True
    )

    with st.expander("Manage Teacher"):

        teacher_map = {}

        for teacher in teachers:

            tid = teacher.get(
                "teacher_id",
                ""
            )

            name = (
                teacher.get("teacher_name")
                or teacher.get("name")
                or tid
            )

            teacher_map[
                f"{tid} — {name}"
            ] = teacher

        selected = st.selectbox(
            "Teacher",
            list(teacher_map.keys()),
            key="manage_teacher_select"
        )

        teacher = teacher_map[selected]

        enabled = teacher.get(
            "enabled",
            True
        )

        c1, c2 = st.columns(2)

        with c1:

            label = (
                "Disable Teacher"
                if enabled
                else "Enable Teacher"
            )

            if st.button(
                label,
                key="toggle_teacher"
            ):

                try:
                    db.table(
                        "teachers"
                    ).update({
                        "enabled":
                            not enabled
                    }).eq(
                        "school_id",
                        st.session_state.school_id
                    ).eq(
                        "teacher_id",
                        teacher["teacher_id"]
                    ).execute()

                    st.rerun()

                except Exception as error:
                    st.error(str(error))

        with c2:

            if st.button(
                "Delete Teacher",
                key="delete_teacher"
            ):

                try:
                    db.table(
                        "teachers"
                    ).delete().eq(
                        "school_id",
                        st.session_state.school_id
                    ).eq(
                        "teacher_id",
                        teacher["teacher_id"]
                    ).execute()

                    st.rerun()

                except Exception as error:
                    st.error(str(error))


# ============================================================
# SMART ATTENDANCE
# ============================================================

def attendance_page():

    st.title("Smart Attendance")

    st.caption(
        "Take attendance and review attendance records."
    )

    students = load_students()

    # Only active students
    if (
        not students.empty
        and "status" in students.columns
    ):

        status = (
            students["status"]
            .fillna("Active")
            .astype(str)
            .str.lower()
        )

        students = students[
            ~status.isin(
                ["pending", "declined"]
            )
        ].copy()

    camera_tab, manual_tab, records_tab = st.tabs(
        ["Camera", "Manual", "Records"]
    )

    # CAMERA
    with camera_tab:

        st.subheader("Camera Attendance")

        st.caption(
            "Start the camera to recognize registered "
            "students and record attendance."
        )

        try:
            from smart_attendance import (
                render_page as render_smart_attendance
            )

            render_smart_attendance()

        except Exception as error:

            st.error(
                "Smart Attendance could not be started."
            )

            st.code(str(error))

    # MANUAL
    with manual_tab:

        st.subheader("Manual Attendance")

        if students.empty:

            st.info(
                "No approved students are registered."
            )

        else:

            student_map = {}

            for _, row in students.iterrows():

                sid = row.get(
                    "student_id",
                    ""
                )

                name = row.get(
                    "name",
                    ""
                )

                student_map[
                    f"{sid} — {name}"
                ] = row

            c1, c2 = st.columns(2)

            with c1:
                selected = st.selectbox(
                    "Student",
                    list(student_map.keys()),
                    key="manual_student"
                )

            with c2:
                status_choice = st.selectbox(
                    "Status",
                    [
                        "Present",
                        "Late",
                        "Absent"
                    ],
                    key="manual_status"
                )

            if st.button(
                "Save Attendance",
                key="save_manual_attendance"
            ):

                student = student_map[selected]

                now = datetime.now()

                date_value = now.strftime(
                    "%Y-%m-%d"
                )

                time_value = now.strftime(
                    "%H:%M:%S"
                )

                student_id = str(
                    student.get(
                        "student_id",
                        ""
                    )
                )

                record = {
                    "school_id":
                        st.session_state.school_id,
                    "student_id":
                        student_id,
                    "name":
                        student.get("name", ""),
                    "class_name":
                        student.get(
                            "class_name",
                            ""
                        ),
                    "attendance_date":
                        date_value,
                    "attendance_time":
                        time_value,
                    "status":
                        status_choice,
                }

                try:

                    existing = (
                        db.table("attendance")
                        .select("id")
                        .eq(
                            "school_id",
                            st.session_state.school_id
                        )
                        .eq(
                            "student_id",
                            student_id
                        )
                        .eq(
                            "attendance_date",
                            date_value
                        )
                        .execute()
                    )

                    if existing.data:

                        db.table(
                            "attendance"
                        ).update({
                            "name":
                                record["name"],
                            "class_name":
                                record["class_name"],
                            "attendance_time":
                                time_value,
                            "status":
                                status_choice,
                        }).eq(
                            "id",
                            existing.data[0]["id"]
                        ).execute()

                    else:

                        db.table(
                            "attendance"
                        ).insert(
                            record
                        ).execute()

                    st.success(
                        f"{record['name']} marked "
                        f"{status_choice}."
                    )

                except Exception as error:
                    st.error(
                        f"Could not save attendance: {error}"
                    )

    # RECORDS
    with records_tab:

        st.subheader(
            "Attendance Records"
        )

        attendance = load_attendance()

        if attendance.empty:

            st.info(
                "No attendance records yet."
            )

        else:

            columns = [
                c for c in [
                    "student_id",
                    "name",
                    "class_name",
                    "attendance_date",
                    "attendance_time",
                    "status",
                ]
                if c in attendance.columns
            ]

            st.dataframe(
                attendance[columns],
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# SMART OCCUPANCY
# ============================================================

def occupancy_page():

    st.title("Smart Occupancy")

    st.caption(
        "Monitor classroom occupancy in real time."
    )

    with st.container(border=True):

        st.subheader(
            "Live Classroom View"
        )

        st.write(
            "Start the camera to monitor "
            "the number of people present."
        )

    try:
        from smart_occupancy import (
            render_page as render_smart_occupancy
        )

        render_smart_occupancy()

    except Exception as error:

        st.error(
            "Smart Occupancy could not be started."
        )

        st.code(str(error))


# ============================================================
# REPORTS
# ============================================================

def reports_page():

    st.title("Reports")

    st.caption(
        "View attendance statistics and records."
    )

    students = load_students()
    attendance = load_attendance()

    if (
        not students.empty
        and "status" in students.columns
    ):

        status = (
            students["status"]
            .fillna("Active")
            .astype(str)
            .str.lower()
        )

        students = students[
            ~status.isin(
                ["pending", "declined"]
            )
        ]

    total_records = len(attendance)

    present_count = 0

    if (
        not attendance.empty
        and "status" in attendance.columns
    ):

        present_count = int(
            (
                attendance["status"]
                .astype(str)
                .str.lower()
                == "present"
            ).sum()
        )

    overall = (
        round(
            (
                present_count
                / total_records
            ) * 100,
            1
        )
        if total_records
        else 0.0
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Total Students",
            len(students)
        )

    with c2:
        st.metric(
            "Attendance Records",
            total_records
        )

    with c3:
        st.metric(
            "Present",
            present_count
        )

    with st.container(border=True):
        st.metric(
            "Overall Attendance Rate",
            f"{overall}%"
        )

    st.subheader(
        "Attendance Records"
    )

    if attendance.empty:

        st.info(
            "No attendance records yet."
        )

    else:

        columns = [
            c for c in [
                "student_id",
                "name",
                "class_name",
                "attendance_date",
                "attendance_time",
                "status",
            ]
            if c in attendance.columns
        ]

        st.dataframe(
            attendance[columns],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SETTINGS
# ============================================================

def settings_page():

    st.title("Settings")

    st.caption(
        "View your school and account information."
    )

    st.subheader(
        "School Information"
    )

    with st.container(border=True):

        st.write(
            f"**School:** "
            f"{st.session_state.school_name}"
        )

        st.write(
            f"**School ID:** "
            f"{st.session_state.school_id}"
        )

        st.write(
            f"**Role:** "
            f"{st.session_state.role}"
        )

        account = (
            st.session_state.user_name
            or st.session_state.user_id
        )

        st.write(
            f"**Account:** {account}"
        )

    st.subheader("Connection")

    with st.container(border=True):

        if db:
            st.success(
                "Database Connected"
            )
        else:
            st.error(
                "Database connection unavailable."
            )

            if db_error_message:
                st.caption(
                    db_error_message
                )


# ============================================================
# SCHOOL APPLICATION
# ============================================================

def school_application():

    if not st.session_state.logged_in:
        st.session_state.screen = "school_login"
        st.rerun()

    with st.sidebar:

        st.title("EduVision")

        st.caption("SCHOOL")

        st.write(
            f"**{st.session_state.school_name}**"
        )

        st.caption("ACCOUNT")

        st.write(
            st.session_state.user_name
            or st.session_state.user_id
        )

        st.caption(
            st.session_state.role
        )

        st.divider()

        if st.session_state.role == "School Admin":

            pages = [
                "Dashboard",
                "Students",
                "Teachers",
                "Smart Attendance",
                "Smart Occupancy",
                "Reports",
                "Settings",
            ]

        else:

            pages = [
                "Dashboard",
                "Students",
                "Smart Attendance",
                "Smart Occupancy",
                "Reports",
            ]

        current = st.session_state.get(
            "nav_page",
            "Dashboard"
        )

        if current not in pages:
            current = "Dashboard"

        # Important: do not manually overwrite a widget
        # after it has already been created.
        if "sidebar_nav_radio" not in st.session_state:
            st.session_state[
                "sidebar_nav_radio"
            ] = current

        elif (
            st.session_state[
                "sidebar_nav_radio"
            ] not in pages
        ):
            del st.session_state[
                "sidebar_nav_radio"
            ]

            st.session_state[
                "sidebar_nav_radio"
            ] = current

        page = st.radio(
            "Navigation",
            pages,
            key="sidebar_nav_radio"
        )

        st.session_state.nav_page = page

        st.divider()

        if st.button(
            "Log Out",
            key="school_logout"
        ):

            clear_login()
            st.session_state.screen = "school_portal"
            st.rerun()

    # ROUTING

    if page == "Dashboard":
        dashboard_page()

    elif page == "Students":
        students_page()

    elif page == "Teachers":
        teachers_page()

    elif page == "Smart Attendance":
        attendance_page()

    elif page == "Smart Occupancy":
        occupancy_page()

    elif page == "Reports":
        reports_page()

    elif page == "Settings":
        settings_page()


# ============================================================
# MASTER ROUTER
# ============================================================

current_screen = st.session_state.get(
    "screen",
    "welcome"
)

if current_screen == "welcome":

    welcome_screen()

elif current_screen == "portal":

    portal_screen()

elif current_screen == "school_portal":

    school_portal()

elif current_screen == "platform_admin_login":

    platform_admin_login()

elif (
    current_screen == "platform_admin"
    and st.session_state.logged_in
    and st.session_state.role == "EduVision Admin"
):

    platform_admin_page()

elif current_screen == "school_login":

    school_login()

elif (
    current_screen == "school_app"
    and st.session_state.logged_in
):

    school_application()

else:

    st.session_state.screen = "welcome"
    st.rerun()

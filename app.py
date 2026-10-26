import os
import sys
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

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
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="EduVision — Smart Classroom Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# ENVIRONMENT / CONFIG
# ============================================================

def get_config(name, default=""):
    value = os.getenv(name, "")

    if value:
        return str(value).strip()

    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass

    return default


SUPABASE_URL = get_config("SUPABASE_URL")
SUPABASE_KEY = get_config("SUPABASE_KEY")

EDUVISION_ADMIN_ID = get_config(
    "EDUVISION_ADMIN_ID",
    "12126"
)

EDUVISION_ADMIN_PASSWORD = get_config(
    "EDUVISION_ADMIN_PASSWORD",
    "12126"
)


# ============================================================
# SUPABASE CLEANUP
# ============================================================

def clean_supabase_url(value):
    """
    Accepts common Supabase URL formats and returns only:

        https://PROJECT.supabase.co

    This protects against accidental values such as:
        "https://project.supabase.co/"
        https://project.supabase.co/rest/v1
        https://project.supabase.co/rest/v1/
        https://project.supabase.co?something
    """

    if not value:
        return ""

    url = str(value).strip()

    # Remove accidental quotes
    url = url.strip("'\"` ")

    # Remove whitespace/newlines
    url = "".join(url.split())

    # Add protocol if user omitted it
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlsplit(url)

        host = parsed.netloc.strip()

        # Handles malformed duplicated protocol cases
        if not host:
            return ""

        # Only keep scheme + hostname
        scheme = parsed.scheme or "https"

        return f"{scheme}://{host}".rstrip("/")

    except Exception:
        return ""


def clean_supabase_key(value):
    if not value:
        return ""

    key = str(value).strip()
    key = key.strip("'\"` ")

    return key


@st.cache_resource
def get_database():

    if create_client is None:
        raise RuntimeError(
            "Supabase library is not installed. "
            "Add 'supabase' to requirements.txt."
        )

    url = clean_supabase_url(SUPABASE_URL)
    key = clean_supabase_key(SUPABASE_KEY)

    if not url:
        raise RuntimeError(
            "SUPABASE_URL is missing or invalid."
        )

    if not key:
        raise RuntimeError(
            "SUPABASE_KEY is missing."
        )

    if "supabase.co" not in url.lower():
        raise RuntimeError(
            "SUPABASE_URL must look like "
            "https://your-project.supabase.co"
        )

    return create_client(url, key)


db = None
db_error_message = None

try:
    db = get_database()
except Exception as error:
    db_error_message = str(error)


# ============================================================
# UI
# ============================================================

st.markdown(
    """
<style>

/* ---------- APP ---------- */

html,
body,
.stApp,
[data-testid="stAppViewContainer"] {
    background: #f4f6f8 !important;
    color: #111827 !important;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}


/* ---------- TEXT ---------- */

h1, h2, h3, h4 {
    color: #111827 !important;
    font-weight: 800 !important;
}

p {
    color: #374151 !important;
}

label {
    color: #111827 !important;
    font-weight: 700 !important;
}


/* ---------- CARDS ---------- */

[data-testid="stVerticalBlockBorderWrapper"] {
    background: #e8f0f7 !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 10px !important;
    padding: 8px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] h1,
[data-testid="stVerticalBlockBorderWrapper"] h2,
[data-testid="stVerticalBlockBorderWrapper"] h3,
[data-testid="stVerticalBlockBorderWrapper"] h4 {
    color: #111827 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] p {
    color: #374151 !important;
}


/* ---------- BUTTONS ---------- */

div.stButton > button {
    width: 100% !important;
    min-height: 45px !important;

    background: #111827 !important;
    color: #ffffff !important;

    border: 2px solid #111827 !important;
    border-radius: 7px !important;

    font-size: 0.95rem !important;
    font-weight: 800 !important;

    box-shadow: none !important;
}

div.stButton > button p,
div.stButton > button span,
div.stButton > button div {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 800 !important;
    opacity: 1 !important;
}

div.stButton > button:hover {
    background: #334155 !important;
    border-color: #334155 !important;
}

div.stButton > button:hover p,
div.stButton > button:hover span,
div.stButton > button:hover div {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}


/* ---------- INPUTS ---------- */

div[data-baseweb="input"] {
    background: #ffffff !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 7px !important;
}

div[data-baseweb="input"] input {
    background: #ffffff !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}

input::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}


/* ---------- SELECT ---------- */

div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 7px !important;
}

div[data-baseweb="select"] span {
    color: #111827 !important;
}


/* ---------- METRICS ---------- */

[data-testid="stMetric"] {
    background: #e8f0f7 !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 10px !important;
    padding: 18px !important;
    box-shadow: 0 2px 7px rgba(0,0,0,0.04) !important;
}

[data-testid="stMetricLabel"] {
    color: #475569 !important;
    font-weight: 700 !important;
}

[data-testid="stMetricValue"] {
    color: #111827 !important;
    font-weight: 900 !important;
}


/* ---------- EXPANDERS ---------- */

[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 9px !important;
}


/* ---------- SIDEBAR ---------- */

[data-testid="stSidebar"] {
    background: #e8f0f7 !important;
    border-right: 1.5px solid #94a3b8 !important;
}

[data-testid="stSidebar"] * {
    color: #111827;
}

[data-testid="stSidebar"] div.stButton > button {
    background: #111827 !important;
}

[data-testid="stSidebar"] div.stButton > button p,
[data-testid="stSidebar"] div.stButton > button span {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}


/* ---------- TABLE ---------- */

[data-testid="stDataFrame"] {
    background: #ffffff !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 9px !important;
    overflow: hidden !important;
}


/* ---------- TABS ---------- */

button[data-baseweb="tab"] {
    color: #475569 !important;
    font-weight: 750 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #111827 !important;
    font-weight: 850 !important;
}


/* ---------- ALERTS ---------- */

[data-testid="stAlert"] {
    border-radius: 9px !important;
    border: 1px solid #94a3b8 !important;
}


/* ---------- CLEAN ---------- */

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
# UI HELPERS
# ============================================================

def page_box(title, description=None):
    """
    Consistent large information card used above pages.
    """

    with st.container(border=True):
        st.header(title)

        if description:
            st.write(description)


def small_box(title, description=None):

    with st.container(border=True):
        st.subheader(title)

        if description:
            st.write(description)


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
# SESSION
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


def navigate(page):

    st.session_state.nav_page = page

    if "sidebar_nav_radio" in st.session_state:
        del st.session_state["sidebar_nav_radio"]

    st.rerun()


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_school(school_id):

    if db is None or not school_id:
        return None

    try:

        response = (
            db.table("schools")
            .select("*")
            .eq(
                "school_id",
                str(school_id).strip()
            )
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print("get_school:", error)

    return None


def get_school_by_admin(
    school_id,
    admin_id
):

    if db is None:
        return None

    try:

        response = (
            db.table("schools")
            .select("*")
            .eq(
                "school_id",
                str(school_id).strip()
            )
            .eq(
                "admin_id",
                str(admin_id).strip()
            )
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print(
            "get_school_by_admin:",
            error
        )

    return None


def get_teacher(
    school_id,
    teacher_id
):

    if db is None:
        return None

    try:

        response = (
            db.table("teachers")
            .select("*")
            .eq(
                "school_id",
                str(school_id).strip()
            )
            .eq(
                "teacher_id",
                str(teacher_id).strip()
            )
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print(
            "get_teacher:",
            error
        )

    return None


def load_students():

    if (
        db is None
        or not st.session_state.school_id
    ):
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
            return pd.DataFrame(
                response.data
            )

    except Exception as error:
        st.error(
            f"Could not load students: {error}"
        )

    return pd.DataFrame()


def active_students_only(df):

    if df.empty:
        return df

    if "status" not in df.columns:
        return df

    status = (
        df["status"]
        .fillna("Active")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return df[
        ~status.isin([
            "pending",
            "declined",
            "rejected",
        ])
    ].copy()


def load_attendance():

    if (
        db is None
        or not st.session_state.school_id
    ):
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

            df = pd.DataFrame(
                response.data
            )

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

    _, center, _ = st.columns(
        [1, 2, 1]
    )

    with center:

        with st.container(border=True):

            st.caption(
                "AI • SMART CLASSROOM"
            )

            st.title("EduVision")

            st.write(
                "Smarter classrooms through fast "
                "attendance, classroom monitoring "
                "and simple management."
            )

            st.write("")

            st.success(
                "System Online"
            )

        if st.button(
            "Enter EduVision →",
            key="enter_eduvision_btn",
            use_container_width=True
        ):

            st.session_state.screen = (
                "portal"
            )

            st.rerun()


# ============================================================
# PORTAL
# ============================================================

def portal_screen():

    c1, c2 = st.columns(
        [4, 1]
    )

    with c1:

        page_box(
            "EduVision",
            "Choose the workspace you want to access."
        )

    with c2:

        if st.button(
            "← Back",
            key="portal_back"
        ):
            go_welcome()

    st.write("")

    school_col, admin_col = st.columns(
        2,
        gap="large"
    )

    with school_col:

        small_box(
            "School Portal",
            "Access your school workspace for "
            "attendance, students and classroom "
            "management."
        )

        if st.button(
            "Open School Portal →",
            key="open_school_portal"
        ):

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    with admin_col:

        small_box(
            "EduVision Admin",
            "Review school registrations and "
            "manage access to the EduVision platform."
        )

        if st.button(
            "Open Admin →",
            key="open_platform_admin"
        ):

            st.session_state.screen = (
                "platform_admin_login"
            )

            st.rerun()


# ============================================================
# SCHOOL PORTAL
# ============================================================

def school_portal():

    c1, c2 = st.columns(
        [4, 1]
    )

    with c1:

        page_box(
            "School Portal",
            "Register a new school or open an "
            "approved EduVision school workspace."
        )

    with c2:

        if st.button(
            "← Back",
            key="school_portal_back"
        ):
            go_portal()

    register_tab, open_tab = st.tabs([
        "Register School",
        "Open School"
    ])

    # --------------------------------------------------------
    # REGISTER
    # --------------------------------------------------------

    with register_tab:

        small_box(
            "Create a School Workspace",
            "Enter your school information below. "
            "EduVision Admin must approve the "
            "registration before the school can log in."
        )

        c1, c2 = st.columns(2)

        with c1:

            school_name = st.text_input(
                "School Name",
                placeholder="Enter school name"
            )

            admin_id = st.text_input(
                "School Admin ID",
                placeholder="Create an Admin ID"
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

            school_name = (
                school_name.strip()
            )

            admin_id = (
                admin_id.strip()
            )

            if not school_name:

                st.error(
                    "Enter the school name."
                )

            elif not admin_id:

                st.error(
                    "Enter an Admin ID."
                )

            elif len(admin_password) < 6:

                st.error(
                    "Password must contain "
                    "at least 6 characters."
                )

            elif (
                admin_password
                != confirm_password
            ):

                st.error(
                    "Passwords do not match."
                )

            elif db is None:

                st.error(
                    "Database unavailable."
                )

                if db_error_message:
                    st.caption(
                        db_error_message
                    )

            else:

                school_id = (
                    generate_school_id()
                )

                try:

                    db.table(
                        "schools"
                    ).insert({
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
                    }).execute()

                    st.success(
                        "School registration submitted."
                    )

                    with st.container(
                        border=True
                    ):

                        st.subheader(
                            "Save Your School Details"
                        )

                        st.write(
                            f"**School:** "
                            f"{school_name}"
                        )

                        st.write(
                            f"**School ID:** "
                            f"{school_id}"
                        )

                        st.write(
                            f"**Admin ID:** "
                            f"{admin_id}"
                        )

                        st.info(
                            "Your school must be "
                            "approved before you can log in."
                        )

                except Exception as error:

                    st.error(
                        f"Registration failed: {error}"
                    )

    # --------------------------------------------------------
    # OPEN SCHOOL
    # --------------------------------------------------------

    with open_tab:

        small_box(
            "Open Your School",
            "Select an approved school below "
            "to continue to the School Admin "
            "or Teacher login."
        )

        approved_schools = []

        if db is None:

            st.error(
                "EduVision cannot connect to "
                "the database."
            )

            if db_error_message:
                st.caption(
                    db_error_message
                )

        else:

            try:

                response = (
                    db.table("schools")
                    .select(
                        "school_id,school_name,"
                        "approval_status"
                    )
                    .execute()
                )

                all_schools = (
                    response.data or []
                )

                approved_schools = [
                    school
                    for school in all_schools
                    if str(
                        school.get(
                            "approval_status",
                            ""
                        )
                    ).strip().lower()
                    == "approved"
                ]

            except Exception as error:

                st.error(
                    "Could not load schools: "
                    f"{error}"
                )

        if not approved_schools:

            st.info(
                "No approved schools are "
                "currently available."
            )

        else:

            school_map = {}

            for school in approved_schools:

                name = str(
                    school.get(
                        "school_name",
                        "School"
                    )
                )

                sid = str(
                    school.get(
                        "school_id",
                        ""
                    )
                )

                label = (
                    f"{name} — {sid}"
                )

                school_map[label] = sid

            selected_school = st.selectbox(
                "Approved School",
                list(
                    school_map.keys()
                )
            )

            if st.button(
                "Continue →",
                key="continue_school"
            ):

                school_id = (
                    school_map[
                        selected_school
                    ]
                )

                school = (
                    get_school(
                        school_id
                    )
                )

                if school:

                    st.session_state.school_id = (
                        school.get(
                            "school_id"
                        )
                    )

                    st.session_state.school_name = (
                        school.get(
                            "school_name"
                        )
                    )

                    st.session_state.screen = (
                        "school_login"
                    )

                    st.rerun()

                else:

                    st.error(
                        "School could not be loaded."
                    )


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
            "School workspace could not be loaded."
        )

        if st.button(
            "Return to School Portal"
        ):

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

        return

    c1, c2 = st.columns(
        [4, 1]
    )

    with c1:

        page_box(
            school.get(
                "school_name",
                "School"
            ),
            f"School ID: {school_id} • "
            "Choose School Admin or Teacher "
            "to continue."
        )

    with c2:

        if st.button(
            "← Change School",
            key="change_school"
        ):

            clear_login()

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    admin_tab, teacher_tab = st.tabs([
        "School Admin",
        "Teacher"
    ])

    # --------------------------------------------------------
    # ADMIN LOGIN
    # --------------------------------------------------------

    with admin_tab:

        _, center, _ = st.columns(
            [1, 2, 1]
        )

        with center:

            small_box(
                "School Admin Login",
                "Manage students, teachers, "
                "attendance, occupancy and "
                "school settings."
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
                "Login as School Admin →",
                key="school_admin_login"
            ):

                admin_id = (
                    admin_id.strip()
                )

                account = (
                    get_school_by_admin(
                        school_id,
                        admin_id
                    )
                )

                if (
                    account
                    and hash_password(
                        password
                    )
                    == account.get(
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
                        f"{school.get('school_name', 'School')} Admin"
                    )
                    st.session_state.nav_page = (
                        "Dashboard"
                    )
                    st.session_state.screen = (
                        "school_app"
                    )

                    if (
                        "sidebar_nav_radio"
                        in st.session_state
                    ):
                        del st.session_state[
                            "sidebar_nav_radio"
                        ]

                    st.rerun()

                else:

                    st.error(
                        "Incorrect Admin ID "
                        "or password."
                    )

    # --------------------------------------------------------
    # TEACHER LOGIN
    # --------------------------------------------------------

    with teacher_tab:

        _, center, _ = st.columns(
            [1, 2, 1]
        )

        with center:

            small_box(
                "Teacher Login",
                "Access students, Smart Attendance, "
                "Smart Occupancy and classroom reports."
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
                "Login as Teacher →",
                key="teacher_login"
            ):

                teacher_id = (
                    teacher_id.strip()
                )

                teacher = (
                    get_teacher(
                        school_id,
                        teacher_id
                    )
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
                    != teacher.get(
                        "password_hash"
                    )
                ):

                    st.error(
                        "Incorrect password."
                    )

                else:

                    st.session_state.logged_in = True
                    st.session_state.role = (
                        "Teacher"
                    )
                    st.session_state.user_id = (
                        teacher_id
                    )

                    st.session_state.user_name = (
                        teacher.get(
                            "teacher_name"
                        )
                        or teacher.get(
                            "name"
                        )
                        or teacher_id
                    )

                    st.session_state.nav_page = (
                        "Dashboard"
                    )

                    st.session_state.screen = (
                        "school_app"
                    )

                    if (
                        "sidebar_nav_radio"
                        in st.session_state
                    ):
                        del st.session_state[
                            "sidebar_nav_radio"
                        ]

                    st.rerun()


# ============================================================
# EDUVISION ADMIN LOGIN
# ============================================================

def platform_admin_login():

    c1, c2 = st.columns(
        [4, 1]
    )

    with c1:

        page_box(
            "EduVision Admin",
            "Platform administration for reviewing "
            "and approving school registrations."
        )

    with c2:

        if st.button(
            "← Back",
            key="platform_admin_back"
        ):
            go_portal()

    _, center, _ = st.columns(
        [1, 2, 1]
    )

    with center:

        small_box(
            "Admin Login",
            "Enter the EduVision administrator "
            "credentials to continue."
        )

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
            "Login to EduVision Admin →",
            key="platform_admin_login_button"
        ):

            if (
                admin_id.strip()
                == EDUVISION_ADMIN_ID
                and password
                == EDUVISION_ADMIN_PASSWORD
            ):

                st.session_state.logged_in = True
                st.session_state.role = (
                    "EduVision Admin"
                )
                st.session_state.user_id = (
                    admin_id.strip()
                )
                st.session_state.screen = (
                    "platform_admin"
                )

                st.rerun()

            else:

                st.error(
                    "Incorrect Admin ID "
                    "or password."
                )


# ============================================================
# EDUVISION ADMIN
# ============================================================

def platform_admin_page():

    c1, c2 = st.columns(
        [4, 1]
    )

    with c1:

        page_box(
            "EduVision Admin Dashboard",
            "Review new school requests and "
            "manage approved schools."
        )

    with c2:

        if st.button(
            "Log Out",
            key="platform_logout"
        ):
            go_portal()

    schools = []

    if db is None:

        st.error(
            "Database unavailable."
        )

        if db_error_message:
            st.caption(
                db_error_message
            )

    else:

        try:

            response = (
                db.table("schools")
                .select("*")
                .execute()
            )

            schools = (
                response.data or []
            )

        except Exception as error:

            st.error(
                f"Could not load schools: {error}"
            )

    pending = [
        s for s in schools
        if str(
            s.get(
                "approval_status",
                ""
            )
        ).strip().lower()
        == "pending"
    ]

    approved = [
        s for s in schools
        if str(
            s.get(
                "approval_status",
                ""
            )
        ).strip().lower()
        == "approved"
    ]

    rejected = [
        s for s in schools
        if str(
            s.get(
                "approval_status",
                ""
            )
        ).strip().lower()
        in ["rejected", "declined"]
    ]

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Pending Requests",
        len(pending)
    )

    m2.metric(
        "Approved Schools",
        len(approved)
    )

    m3.metric(
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

        small_box(
            "Pending Registrations",
            "Approve valid school registrations "
            "or reject requests that should not "
            "receive access."
        )

        if not pending:

            st.info(
                "No registrations are "
                "waiting for approval."
            )

        for school in pending:

            sid = school.get(
                "school_id",
                ""
            )

            name = school.get(
                "school_name",
                "Unnamed School"
            )

            aid = school.get(
                "admin_id",
                ""
            )

            with st.container(
                border=True
            ):

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

                            st.error(
                                str(error)
                            )

    # APPROVED
    with tab2:

        small_box(
            "Approved Schools",
            "Schools currently allowed to "
            "use EduVision."
        )

        if not approved:

            st.info(
                "No approved schools yet."
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

        small_box(
            "Rejected Registrations",
            "Rejected requests can be restored "
            "to pending if they need to be "
            "reviewed again."
        )

        if not rejected:

            st.info(
                "No rejected registrations."
            )

        for school in rejected:

            sid = school.get(
                "school_id",
                ""
            )

            name = school.get(
                "school_name",
                "School"
            )

            with st.container(
                border=True
            ):

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

                        st.error(
                            str(error)
                        )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():

    students = active_students_only(
        load_students()
    )

    attendance = load_attendance()

    total_students = len(
        students
    )

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
            attendance[
                "attendance_date"
            ].astype(str)
            == today
        ]

        if "status" in today_rows.columns:

            statuses = (
                today_rows["status"]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            present = int(
                (
                    statuses
                    == "present"
                ).sum()
            )

            late = int(
                (
                    statuses
                    == "late"
                ).sum()
            )

            absent = int(
                (
                    statuses
                    == "absent"
                ).sum()
            )

    attended = (
        present + late
    )

    percentage = (
        round(
            attended
            / total_students
            * 100,
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

    page_box(
        f"{greeting}, {user}",
        f"{st.session_state.school_name} • "
        "Here is today's classroom overview."
    )

    st.subheader(
        "Today's Overview"
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Students",
        total_students
    )

    m2.metric(
        "Present",
        present
    )

    m3.metric(
        "Absent",
        absent
    )

    m4.metric(
        "Attendance",
        f"{percentage}%"
    )

    with st.container(
        border=True
    ):

        st.subheader(
            "Attendance Summary"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Present",
            present
        )

        c2.metric(
            "Late",
            late
        )

        c3.metric(
            "Absent",
            absent
        )

    st.subheader(
        "Quick Actions"
    )

    c1, c2 = st.columns(2)

    with c1:

        small_box(
            "Smart Attendance",
            "Open the attendance workspace "
            "to take or review attendance."
        )

        if st.button(
            "Open Attendance →",
            key="dashboard_attendance"
        ):

            navigate(
                "Smart Attendance"
            )

    with c2:

        small_box(
            "Smart Occupancy",
            "Open the classroom monitor to "
            "view live room occupancy."
        )

        if st.button(
            "Open Occupancy →",
            key="dashboard_occupancy"
        ):

            navigate(
                "Smart Occupancy"
            )


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

    page_box(
        "Students",
        "View approved students, register "
        "new students and manage student access."
    )

    students = load_students()

    if students.empty:

        pending_students = (
            pd.DataFrame()
        )

        active_students = (
            pd.DataFrame()
        )

    elif "status" not in students.columns:

        pending_students = (
            pd.DataFrame()
        )

        active_students = (
            students.copy()
        )

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

        active_students = students[
            ~status.isin([
                "pending",
                "declined",
                "rejected",
            ])
        ].copy()

    m1, m2 = st.columns(2)

    m1.metric(
        "Active Students",
        len(active_students)
    )

    m2.metric(
        "Pending Approval",
        len(pending_students)
    )

    # TEACHER REGISTRATION
    if is_teacher:

        with st.expander(
            "Register New Student"
        ):

            st.write(
                "New student registrations "
                "must be approved by the "
                "School Admin."
            )

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

                student_id = (
                    student_id.strip()
                )

                student_name = (
                    student_name.strip()
                )

                class_name = (
                    class_name.strip()
                )

                roll_no = (
                    roll_no.strip()
                )

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

                elif db is None:

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
                            "Student submitted "
                            "for approval."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            "Could not register "
                            f"student: {error}"
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
                if c
                in pending_students.columns
            ]

            st.dataframe(
                pending_students[
                    columns
                ],
                use_container_width=True,
                hide_index=True
            )

            options = {}

            for _, row in (
                pending_students.iterrows()
            ):

                sid = str(
                    row.get(
                        "student_id",
                        ""
                    )
                )

                name = str(
                    row.get(
                        "name",
                        ""
                    )
                )

                options[
                    f"{sid} — {name}"
                ] = sid

            selected = st.selectbox(
                "Select Student",
                list(options.keys()),
                key="pending_student_select"
            )

            sid = options[
                selected
            ]

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "Approve Student",
                    key="approve_student"
                ):

                    try:

                        db.table(
                            "students"
                        ).update({
                            "status":
                                "Active"
                        }).eq(
                            "school_id",
                            st.session_state.school_id
                        ).eq(
                            "student_id",
                            sid
                        ).execute()

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

            with c2:

                if st.button(
                    "Decline Student",
                    key="decline_student"
                ):

                    try:

                        db.table(
                            "students"
                        ).update({
                            "status":
                                "Declined"
                        }).eq(
                            "school_id",
                            st.session_state.school_id
                        ).eq(
                            "student_id",
                            sid
                        ).execute()

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

    # ACTIVE
    st.subheader(
        "Active Students"
    )

    if active_students.empty:

        st.info(
            "No approved students "
            "are currently registered."
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
            if c
            in active_students.columns
        ]

        st.dataframe(
            active_students[
                columns
            ],
            use_container_width=True,
            hide_index=True
        )

    # TEACHER PENDING VIEW
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
                if c
                in pending_students.columns
            ]

            st.dataframe(
                pending_students[
                    columns
                ],
                use_container_width=True,
                hide_index=True
            )

    # REMOVE
    if (
        is_admin
        and not students.empty
    ):

        with st.expander(
            "Remove Student"
        ):

            student_map = {}

            for _, row in (
                students.iterrows()
            ):

                sid = str(
                    row.get(
                        "student_id",
                        ""
                    )
                )

                name = str(
                    row.get(
                        "name",
                        ""
                    )
                )

                if sid:

                    student_map[
                        f"{sid} — {name}"
                    ] = sid

            if student_map:

                selected = st.selectbox(
                    "Student",
                    list(
                        student_map.keys()
                    ),
                    key="remove_student_select"
                )

                if st.button(
                    "Remove Student",
                    key="remove_student_button"
                ):

                    sid = (
                        student_map[
                            selected
                        ]
                    )

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

                        st.error(
                            str(error)
                        )


# ============================================================
# TEACHERS
# ============================================================

def teachers_page():

    if (
        st.session_state.role
        != "School Admin"
    ):

        st.error(
            "School Admin access required."
        )

        return

    page_box(
        "Teachers",
        "Create teacher accounts, enable or "
        "disable access and manage your "
        "school's teaching staff."
    )

    teachers = []

    if db is not None:

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

            teachers = (
                response.data or []
            )

        except Exception as error:

            st.error(
                f"Could not load teachers: {error}"
            )

    active = [
        teacher
        for teacher in teachers
        if teacher.get(
            "enabled",
            True
        )
    ]

    c1, c2 = st.columns(2)

    c1.metric(
        "Total Teachers",
        len(teachers)
    )

    c2.metric(
        "Active Accounts",
        len(active)
    )

    with st.expander(
        "Create Teacher Account"
    ):

        st.write(
            "Create login details for "
            "a teacher at this school."
        )

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

            teacher_id = (
                teacher_id.strip()
            )

            teacher_name = (
                teacher_name.strip()
            )

            if not teacher_id:

                st.error(
                    "Enter a Teacher ID."
                )

            elif not teacher_name:

                st.error(
                    "Enter the teacher's name."
                )

            elif (
                len(teacher_password)
                < 6
            ):

                st.error(
                    "Password must contain "
                    "at least 6 characters."
                )

            elif db is None:

                st.error(
                    "Database unavailable."
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
                        "Could not create "
                        f"teacher: {error}"
                    )

    st.subheader(
        "Teacher Accounts"
    )

    if not teachers:

        st.info(
            "No teacher accounts "
            "have been created yet."
        )

        return

    rows = []

    for teacher in teachers:

        name = (
            teacher.get(
                "teacher_name"
            )
            or teacher.get(
                "name"
            )
            or teacher.get(
                "teacher_id",
                ""
            )
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

    with st.expander(
        "Manage Teacher"
    ):

        teacher_map = {}

        for teacher in teachers:

            tid = str(
                teacher.get(
                    "teacher_id",
                    ""
                )
            )

            name = (
                teacher.get(
                    "teacher_name"
                )
                or teacher.get(
                    "name"
                )
                or tid
            )

            if tid:

                teacher_map[
                    f"{tid} — {name}"
                ] = teacher

        if teacher_map:

            selected = st.selectbox(
                "Teacher",
                list(
                    teacher_map.keys()
                ),
                key="manage_teacher_select"
            )

            teacher = (
                teacher_map[
                    selected
                ]
            )

            enabled = bool(
                teacher.get(
                    "enabled",
                    True
                )
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
                            teacher[
                                "teacher_id"
                            ]
                        ).execute()

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

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
                            teacher[
                                "teacher_id"
                            ]
                        ).execute()

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )


# ============================================================
# ATTENDANCE
# ============================================================

def attendance_page():

    page_box(
        "Smart Attendance",
        "Record classroom attendance using "
        "the camera or mark students manually."
    )

    students = active_students_only(
        load_students()
    )

    camera_tab, manual_tab, records_tab = (
        st.tabs([
            "Camera",
            "Manual",
            "Records"
        ])
    )

    # CAMERA
    with camera_tab:

        small_box(
            "Camera Attendance",
            "Use the classroom camera to "
            "recognize registered students."
        )

        try:

            from smart_attendance import (
                render_page
                as render_smart_attendance
            )

            render_smart_attendance()

        except Exception as error:

            st.error(
                "Smart Attendance "
                "could not be started."
            )

            with st.expander(
                "Technical Details"
            ):
                st.code(
                    str(error)
                )

    # MANUAL
    with manual_tab:

        small_box(
            "Manual Attendance",
            "Select a student and attendance "
            "status to update today's record."
        )

        if students.empty:

            st.info(
                "No approved students "
                "are registered."
            )

        else:

            student_map = {}

            for _, row in (
                students.iterrows()
            ):

                sid = str(
                    row.get(
                        "student_id",
                        ""
                    )
                )

                name = str(
                    row.get(
                        "name",
                        ""
                    )
                )

                if sid:

                    student_map[
                        f"{sid} — {name}"
                    ] = row

            if student_map:

                c1, c2 = st.columns(2)

                with c1:

                    selected = st.selectbox(
                        "Student",
                        list(
                            student_map.keys()
                        ),
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

                    if db is None:

                        st.error(
                            "Database unavailable."
                        )

                    else:

                        student = (
                            student_map[
                                selected
                            ]
                        )

                        now = datetime.now()

                        date_value = (
                            now.strftime(
                                "%Y-%m-%d"
                            )
                        )

                        time_value = (
                            now.strftime(
                                "%H:%M:%S"
                            )
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
                                date_value,
                            "attendance_time":
                                time_value,
                            "status":
                                status_choice,
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
                                        record[
                                            "name"
                                        ],
                                    "class_name":
                                        record[
                                            "class_name"
                                        ],
                                    "attendance_time":
                                        time_value,
                                    "status":
                                        status_choice,
                                }).eq(
                                    "id",
                                    existing.data[
                                        0
                                    ]["id"]
                                ).execute()

                            else:

                                db.table(
                                    "attendance"
                                ).insert(
                                    record
                                ).execute()

                            st.success(
                                f"{record['name']} "
                                f"marked {status_choice}."
                            )

                        except Exception as error:

                            st.error(
                                "Could not save "
                                f"attendance: {error}"
                            )

    # RECORDS
    with records_tab:

        small_box(
            "Attendance Records",
            "Review previously saved "
            "attendance information."
        )

        attendance = (
            load_attendance()
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
                if c
                in attendance.columns
            ]

            st.dataframe(
                attendance[
                    columns
                ],
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# OCCUPANCY
# ============================================================

def occupancy_page():

    page_box(
        "Smart Occupancy",
        "Monitor classroom occupancy and "
        "see how many people are currently "
        "inside the classroom."
    )

    small_box(
        "Live Classroom View",
        "Start the camera below to begin "
        "classroom occupancy monitoring."
    )

    try:

        from smart_occupancy import (
            render_page
            as render_smart_occupancy
        )

        render_smart_occupancy()

    except Exception as error:

        st.error(
            "Smart Occupancy "
            "could not be started."
        )

        with st.expander(
            "Technical Details"
        ):

            st.code(
                str(error)
            )


# ============================================================
# REPORTS
# ============================================================

def reports_page():

    page_box(
        "Reports",
        "View school attendance statistics "
        "and previously saved attendance records."
    )

    students = active_students_only(
        load_students()
    )

    attendance = (
        load_attendance()
    )

    total_records = len(
        attendance
    )

    present_count = 0
    late_count = 0

    if (
        not attendance.empty
        and "status"
        in attendance.columns
    ):

        statuses = (
            attendance["status"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        present_count = int(
            (
                statuses
                == "present"
            ).sum()
        )

        late_count = int(
            (
                statuses
                == "late"
            ).sum()
        )

    attended_count = (
        present_count
        + late_count
    )

    overall = (
        round(
            attended_count
            / total_records
            * 100,
            1
        )
        if total_records
        else 0.0
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Students",
        len(students)
    )

    c2.metric(
        "Attendance Records",
        total_records
    )

    c3.metric(
        "Present / Late",
        attended_count
    )

    with st.container(
        border=True
    ):

        st.subheader(
            "Overall Attendance"
        )

        st.metric(
            "Attendance Rate",
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
            if c
            in attendance.columns
        ]

        st.dataframe(
            attendance[
                columns
            ],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SETTINGS
# ============================================================

def settings_page():

    page_box(
        "Settings",
        "View your EduVision school "
        "and account information."
    )

    small_box(
        "School Information",
        "Information for the currently "
        "signed-in school workspace."
    )

    with st.container(
        border=True
    ):

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

    st.subheader(
        "System Connection"
    )

    with st.container(
        border=True
    ):

        if db is not None:

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
# SCHOOL APP
# ============================================================

def school_application():

    if not st.session_state.logged_in:

        st.session_state.screen = (
            "school_login"
        )

        st.rerun()

    with st.sidebar:

        st.title(
            "EduVision"
        )

        st.caption(
            "SCHOOL"
        )

        st.write(
            f"**{st.session_state.school_name}**"
        )

        st.caption(
            "ACCOUNT"
        )

        st.write(
            st.session_state.user_name
            or st.session_state.user_id
        )

        st.caption(
            st.session_state.role
        )

        st.divider()

        if (
            st.session_state.role
            == "School Admin"
        ):

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

        current = (
            st.session_state.get(
                "nav_page",
                "Dashboard"
            )
        )

        if current not in pages:
            current = "Dashboard"

        if (
            "sidebar_nav_radio"
            not in st.session_state
        ):

            st.session_state[
                "sidebar_nav_radio"
            ] = current

        elif (
            st.session_state[
                "sidebar_nav_radio"
            ]
            not in pages
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

        st.session_state.nav_page = (
            page
        )

        st.divider()

        if st.button(
            "Log Out",
            key="school_logout"
        ):

            clear_login()

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

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

current_screen = (
    st.session_state.get(
        "screen",
        "welcome"
    )
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
    current_screen
    == "platform_admin"
    and st.session_state.logged_in
    and st.session_state.role
    == "EduVision Admin"
):

    platform_admin_page()

elif current_screen == "school_login":

    school_login()

elif (
    current_screen
    == "school_app"
    and st.session_state.logged_in
):

    school_application()

else:

    clear_login()

    st.session_state.screen = (
        "welcome"
    )

    st.rerun()

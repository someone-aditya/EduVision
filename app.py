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
    page_title="EduVision — Smart Classroom",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIG
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
# SUPABASE
# ============================================================

def clean_supabase_url(value):
    if not value:
        return ""

    url = str(value).strip().strip("'\"` ")
    url = "".join(url.split())

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlsplit(url)

        if not parsed.netloc:
            return ""

        scheme = parsed.scheme or "https"
        host = parsed.netloc.strip()

        return f"{scheme}://{host}".rstrip("/")

    except Exception:
        return ""


def clean_supabase_key(value):
    if not value:
        return ""

    return str(value).strip().strip("'\"` ")


@st.cache_resource
def get_database():

    if create_client is None:
        raise RuntimeError(
            "Supabase library is not installed."
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
# DARK EDUVISION UI
# ============================================================

st.markdown(
    """
<style>

/* =========================================================
   APP
========================================================= */

html, body, .stApp,
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 10% 0%, rgba(37,99,235,0.13), transparent 32%),
        radial-gradient(circle at 90% 5%, rgba(124,58,237,0.10), transparent 30%),
        #080d18 !important;

    color: #f8fafc !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}


/* =========================================================
   TEXT
========================================================= */

h1 {
    color: #ffffff !important;
    font-weight: 900 !important;
    letter-spacing: -1px !important;
}

h2, h3, h4 {
    color: #f8fafc !important;
    font-weight: 800 !important;
}

p {
    color: #cbd5e1 !important;
}

label {
    color: #e2e8f0 !important;
    font-weight: 700 !important;
}

[data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
}


/* =========================================================
   CARDS / BOXES
========================================================= */

[data-testid="stVerticalBlockBorderWrapper"] {
    background:
        linear-gradient(
            145deg,
            rgba(17,24,39,0.96),
            rgba(15,23,42,0.92)
        ) !important;

    border: 1px solid #334155 !important;
    border-radius: 16px !important;

    padding: 8px !important;

    box-shadow:
        0 12px 35px rgba(0,0,0,0.20),
        inset 0 1px 0 rgba(255,255,255,0.035) !important;

    transition:
        transform 0.15s ease,
        border-color 0.15s ease !important;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #475569 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] p {
    color: #cbd5e1 !important;
}


/* =========================================================
   BUTTONS
========================================================= */

div.stButton > button {
    width: 100% !important;
    min-height: 46px !important;

    background:
        linear-gradient(
            100deg,
            #2563eb,
            #4f46e5
        ) !important;

    color: #ffffff !important;

    border: 1px solid rgba(255,255,255,0.13) !important;
    border-radius: 10px !important;

    font-size: 0.95rem !important;
    font-weight: 800 !important;

    box-shadow:
        0 8px 22px rgba(37,99,235,0.18) !important;

    transition:
        transform 0.15s ease,
        box-shadow 0.15s ease !important;
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
    transform: translateY(-1px) !important;

    background:
        linear-gradient(
            100deg,
            #3b82f6,
            #6366f1
        ) !important;

    border-color: #60a5fa !important;

    box-shadow:
        0 10px 28px rgba(37,99,235,0.28) !important;
}

div.stButton > button:active {
    transform: translateY(0px) !important;
}


/* =========================================================
   INPUTS
========================================================= */

div[data-baseweb="input"] {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #3b82f6 !important;
}

div[data-baseweb="input"] input {
    background: transparent !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

input::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}


/* =========================================================
   SELECT
========================================================= */

div[data-baseweb="select"] > div {
    background: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}

div[data-baseweb="select"] span {
    color: #ffffff !important;
}


/* =========================================================
   METRICS
========================================================= */

[data-testid="stMetric"] {
    background:
        linear-gradient(
            145deg,
            #111827,
            #0f172a
        ) !important;

    border: 1px solid #334155 !important;
    border-radius: 14px !important;

    padding: 20px !important;

    box-shadow:
        0 10px 30px rgba(0,0,0,0.17) !important;
}

[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-weight: 700 !important;
}

[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-weight: 900 !important;
}


/* =========================================================
   TABS
========================================================= */

button[data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-weight: 750 !important;
}

button[data-baseweb="tab"] p {
    color: inherit !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #60a5fa !important;
}

div[data-baseweb="tab-highlight"] {
    background-color: #3b82f6 !important;
}


/* =========================================================
   EXPANDERS
========================================================= */

[data-testid="stExpander"] {
    background: #111827 !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}

[data-testid="stExpander"] summary {
    color: #ffffff !important;
}


/* =========================================================
   ALERTS
========================================================= */

[data-testid="stAlert"] {
    border-radius: 11px !important;
    border: 1px solid #334155 !important;
}


/* =========================================================
   DATAFRAME
========================================================= */

[data-testid="stDataFrame"] {
    background: #111827 !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}


/* =========================================================
   SIDEBAR
========================================================= */

[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #0b1220 0%,
            #0f172a 100%
        ) !important;

    border-right: 1px solid #1e293b !important;
}

[data-testid="stSidebar"] h1 {
    color: #ffffff !important;
}

[data-testid="stSidebar"] p {
    color: #cbd5e1 !important;
}

[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 5px 4px !important;
}


/* =========================================================
   DIVIDER
========================================================= */

hr {
    border-color: #1e293b !important;
}


/* =========================================================
   SCROLLBAR
========================================================= */

::-webkit-scrollbar {
    width: 9px;
}

::-webkit-scrollbar-track {
    background: #080d18;
}

::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 10px;
}


/* =========================================================
   CLEAN STREAMLIT
========================================================= */

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

def hero(title, subtitle=None, label=None):

    with st.container(border=True):

        if label:
            st.caption(label)

        st.title(title)

        if subtitle:
            st.write(subtitle)


def feature_card(title, text=None):

    with st.container(border=True):

        st.subheader(title)

        if text:
            st.write(text)


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
        print("get_school_by_admin:", error)

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
        print("get_teacher:", error)

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
            return pd.DataFrame(response.data)

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
        ~status.isin(
            [
                "pending",
                "declined",
                "rejected",
            ]
        )
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

    _, center, _ = st.columns(
        [0.7, 2, 0.7]
    )

    with center:

        with st.container(border=True):

            st.caption(
                "AI • SMART CLASSROOM"
            )

            st.title("EduVision")

            st.write(
                "Smarter classrooms through fast attendance, "
                "classroom monitoring and simple management."
            )

            st.success(
                "● System Online"
            )

        st.write("")

        if st.button(
            "Enter EduVision  →",
            key="enter_eduvision",
            use_container_width=True
        ):

            st.session_state.screen = "portal"

            st.rerun()


# ============================================================
# PORTAL
# ============================================================

def portal_screen():

    c1, c2 = st.columns(
        [5, 1]
    )

    with c1:

        hero(
            "EduVision",
            "Choose your workspace.",
            "SMART CLASSROOM PLATFORM"
        )

    with c2:

        if st.button(
            "← Back",
            key="portal_back"
        ):
            go_welcome()

    st.write("")

    c1, c2 = st.columns(
        2,
        gap="large"
    )

    with c1:

        feature_card(
            "School Portal",
            "Attendance, students and classroom management."
        )

        if st.button(
            "Open School Portal  →",
            key="school_portal_button"
        ):

            st.session_state.screen = "school_portal"

            st.rerun()

    with c2:

        feature_card(
            "EduVision Admin",
            "School registration and platform access."
        )

        if st.button(
            "Open Admin  →",
            key="admin_portal_button"
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
        [5, 1]
    )

    with c1:

        hero(
            "School Portal",
            "Register or open your school.",
            "EDUVISION"
        )

    with c2:

        if st.button(
            "← Back",
            key="school_portal_back"
        ):
            go_portal()

    register_tab, open_tab = st.tabs(
        [
            "Register School",
            "Open School"
        ]
    )

    # --------------------------------------------------------
    # REGISTER
    # --------------------------------------------------------

    with register_tab:

        st.write("")

        feature_card(
            "Register School",
            "Create your EduVision school workspace."
        )

        c1, c2 = st.columns(2)

        with c1:

            school_name = st.text_input(
                "School Name",
                placeholder="School name"
            )

            admin_id = st.text_input(
                "Admin ID",
                placeholder="Create Admin ID"
            )

        with c2:

            admin_password = st.text_input(
                "Password",
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
            key="register_school"
        ):

            school_name = school_name.strip()
            admin_id = admin_id.strip()

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
                    "Password must contain at least 6 characters."
                )

            elif admin_password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            elif db is None:

                st.error(
                    "Database unavailable."
                )

                if db_error_message:
                    st.caption(db_error_message)

            else:

                school_id = generate_school_id()

                try:

                    db.table(
                        "schools"
                    ).insert(
                        {
                            "school_id": school_id,
                            "school_name": school_name,
                            "admin_id": admin_id,
                            "admin_password_hash":
                                hash_password(
                                    admin_password
                                ),
                            "approval_status":
                                "pending",
                        }
                    ).execute()

                    st.success(
                        "Registration submitted."
                    )

                    with st.container(
                        border=True
                    ):

                        st.subheader(
                            "School Created"
                        )

                        st.write(
                            f"**School ID:** {school_id}"
                        )

                        st.write(
                            f"**Admin ID:** {admin_id}"
                        )

                        st.info(
                            "Waiting for EduVision Admin approval."
                        )

                except Exception as error:

                    st.error(
                        f"Registration failed: {error}"
                    )

    # --------------------------------------------------------
    # OPEN
    # --------------------------------------------------------

    with open_tab:

        st.write("")

        feature_card(
            "Open School",
            "Continue to an approved school."
        )

        approved_schools = []

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
                    .select(
                        "school_id,"
                        "school_name,"
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
                    f"Could not load schools: {error}"
                )

        if not approved_schools:

            st.info(
                "No approved schools available."
            )

        else:

            school_map = {}

            for school in approved_schools:

                school_name = str(
                    school.get(
                        "school_name",
                        "School"
                    )
                )

                school_id = str(
                    school.get(
                        "school_id",
                        ""
                    )
                )

                school_map[
                    f"{school_name} • {school_id}"
                ] = school_id

            selected = st.selectbox(
                "School",
                list(school_map.keys())
            )

            if st.button(
                "Continue  →",
                key="continue_school"
            ):

                school_id = school_map[
                    selected
                ]

                school = get_school(
                    school_id
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
                        "Could not open this school."
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
            "School could not be loaded."
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
        [5, 1]
    )

    with c1:

        hero(
            school.get(
                "school_name",
                "EduVision School"
            ),
            f"School ID • {school_id}",
            "SCHOOL WORKSPACE"
        )

    with c2:

        if st.button(
            "← Change",
            key="change_school"
        ):

            clear_login()

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    admin_tab, teacher_tab = st.tabs(
        [
            "School Admin",
            "Teacher"
        ]
    )

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    with admin_tab:

        st.write("")

        _, center, _ = st.columns(
            [1, 2, 1]
        )

        with center:

            feature_card(
                "School Admin",
                "School management access."
            )

            admin_id = st.text_input(
                "Admin ID",
                key="school_admin_id"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="school_admin_password"
            )

            if st.button(
                "Login  →",
                key="school_admin_login"
            ):

                admin_id = admin_id.strip()

                account = get_school_by_admin(
                    school_id,
                    admin_id
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
                        "Incorrect Admin ID or password."
                    )

    # --------------------------------------------------------
    # TEACHER
    # --------------------------------------------------------

    with teacher_tab:

        st.write("")

        _, center, _ = st.columns(
            [1, 2, 1]
        )

        with center:

            feature_card(
                "Teacher",
                "Classroom access."
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
                "Login  →",
                key="teacher_login"
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
                        "Teacher account is disabled."
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
        [5, 1]
    )

    with c1:

        hero(
            "EduVision Admin",
            "Platform management.",
            "ADMINISTRATION"
        )

    with c2:

        if st.button(
            "← Back",
            key="admin_back"
        ):
            go_portal()

    st.write("")

    _, center, _ = st.columns(
        [1, 2, 1]
    )

    with center:

        feature_card(
            "Admin Login",
            "Authorized access only."
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
            "Login  →",
            key="platform_admin_login"
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
                    "Incorrect Admin ID or password."
                )


# ============================================================
# EDUVISION ADMIN PAGE
# ============================================================

def platform_admin_page():

    c1, c2 = st.columns(
        [5, 1]
    )

    with c1:

        hero(
            "Admin Dashboard",
            "School registrations.",
            "EDUVISION"
        )

    with c2:

        if st.button(
            "Log Out",
            key="admin_logout"
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
        school
        for school in schools
        if str(
            school.get(
                "approval_status",
                ""
            )
        ).strip().lower()
        == "pending"
    ]

    approved = [
        school
        for school in schools
        if str(
            school.get(
                "approval_status",
                ""
            )
        ).strip().lower()
        == "approved"
    ]

    rejected = [
        school
        for school in schools
        if str(
            school.get(
                "approval_status",
                ""
            )
        ).strip().lower()
        in [
            "rejected",
            "declined"
        ]
    ]

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Pending",
        len(pending)
    )

    m2.metric(
        "Approved",
        len(approved)
    )

    m3.metric(
        "Rejected",
        len(rejected)
    )

    tab1, tab2, tab3 = st.tabs(
        [
            f"Pending ({len(pending)})",
            f"Approved ({len(approved)})",
            f"Rejected ({len(rejected)})"
        ]
    )

    # --------------------------------------------------------
    # PENDING
    # --------------------------------------------------------

    with tab1:

        if not pending:

            st.info(
                "No pending registrations."
            )

        for school in pending:

            sid = school.get(
                "school_id",
                ""
            )

            name = school.get(
                "school_name",
                "School"
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
                    f"School ID • **{sid}**"
                )

                st.write(
                    f"Admin ID • **{aid}**"
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
                                ).update(
                                    {
                                        "approval_status":
                                            "approved",
                                        "approved_by":
                                            st.session_state.user_id,
                                        "approved_at":
                                            datetime.now(
                                                timezone.utc
                                            ).isoformat(),
                                    }
                                ).eq(
                                    "school_id",
                                    sid
                                ).execute()

                            except Exception:

                                db.table(
                                    "schools"
                                ).update(
                                    {
                                        "approval_status":
                                            "approved"
                                    }
                                ).eq(
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
                            ).update(
                                {
                                    "approval_status":
                                        "rejected"
                                }
                            ).eq(
                                "school_id",
                                sid
                            ).execute()

                            st.rerun()

                        except Exception as error:

                            st.error(
                                str(error)
                            )

    # --------------------------------------------------------
    # APPROVED
    # --------------------------------------------------------

    with tab2:

        if not approved:

            st.info(
                "No approved schools."
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
                hide_index=True
            )

    # --------------------------------------------------------
    # REJECTED
    # --------------------------------------------------------

    with tab3:

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
                    f"School ID • **{sid}**"
                )

                if st.button(
                    "Restore",
                    key=f"restore_{sid}"
                ):

                    try:

                        db.table(
                            "schools"
                        ).update(
                            {
                                "approval_status":
                                    "pending"
                            }
                        ).eq(
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

    attendance_percentage = (
        round(
            (
                present + late
            )
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

    hero(
        f"{greeting}, {user}",
        st.session_state.school_name,
        "CLASSROOM DASHBOARD"
    )

    st.write("")

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
        f"{attendance_percentage}%"
    )

    st.write("")

    st.subheader(
        "Quick Actions"
    )

    c1, c2 = st.columns(
        2,
        gap="large"
    )

    with c1:

        feature_card(
            "Smart Attendance",
            "Fast classroom attendance."
        )

        if st.button(
            "Open Attendance  →",
            key="dashboard_attendance"
        ):

            navigate(
                "Smart Attendance"
            )

    with c2:

        feature_card(
            "Smart Occupancy",
            "Live classroom occupancy."
        )

        if st.button(
            "Open Occupancy  →",
            key="dashboard_occupancy"
        ):

            navigate(
                "Smart Occupancy"
            )

    st.write("")

    with st.container(
        border=True
    ):

        st.subheader(
            "Today"
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

    hero(
        "Students",
        "Student management.",
        "SCHOOL"
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
            ~status.isin(
                [
                    "pending",
                    "declined",
                    "rejected"
                ]
            )
        ].copy()

    m1, m2 = st.columns(2)

    m1.metric(
        "Active",
        len(active_students)
    )

    m2.metric(
        "Pending",
        len(pending_students)
    )

    # --------------------------------------------------------
    # TEACHER REGISTER STUDENT
    # --------------------------------------------------------

    if is_teacher:

        with st.expander(
            "Register Student"
        ):

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID",
                    key="new_student_id"
                )

                student_name = st.text_input(
                    "Name",
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
                "Submit for Approval",
                key="submit_student"
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
                        "Enter Student ID."
                    )

                elif not student_name:

                    st.error(
                        "Enter student name."
                    )

                elif not class_name:

                    st.error(
                        "Enter class."
                    )

                elif db is None:

                    st.error(
                        "Database unavailable."
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
                                    class_name,
                                "roll_no":
                                    roll_no,
                                "status":
                                    "Pending",
                            }
                        ).execute()

                        st.success(
                            "Student submitted."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Could not register student: {error}"
                        )

    # --------------------------------------------------------
    # ADMIN APPROVAL
    # --------------------------------------------------------

    if is_admin:

        st.subheader(
            "Pending Registrations"
        )

        if pending_students.empty:

            st.info(
                "No pending students."
            )

        else:

            columns = [
                column
                for column in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status"
                ]
                if column
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

                if sid:

                    options[
                        f"{sid} • {name}"
                    ] = sid

            if options:

                selected = st.selectbox(
                    "Student",
                    list(
                        options.keys()
                    ),
                    key="pending_student"
                )

                sid = options[
                    selected
                ]

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "Approve",
                        key="approve_student"
                    ):

                        try:

                            db.table(
                                "students"
                            ).update(
                                {
                                    "status":
                                        "Active"
                                }
                            ).eq(
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
                        "Decline",
                        key="decline_student"
                    ):

                        try:

                            db.table(
                                "students"
                            ).update(
                                {
                                    "status":
                                        "Declined"
                                }
                            ).eq(
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

    # --------------------------------------------------------
    # ACTIVE STUDENTS
    # --------------------------------------------------------

    st.subheader(
        "Active Students"
    )

    if active_students.empty:

        st.info(
            "No active students."
        )

    else:

        columns = [
            column
            for column in [
                "student_id",
                "name",
                "class_name",
                "roll_no",
                "status"
            ]
            if column
            in active_students.columns
        ]

        st.dataframe(
            active_students[
                columns
            ],
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # TEACHER PENDING
    # --------------------------------------------------------

    if (
        is_teacher
        and not pending_students.empty
    ):

        with st.expander(
            f"Pending ({len(pending_students)})"
        ):

            columns = [
                column
                for column in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status"
                ]
                if column
                in pending_students.columns
            ]

            st.dataframe(
                pending_students[
                    columns
                ],
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------------------------
    # REMOVE
    # --------------------------------------------------------

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
                        f"{sid} • {name}"
                    ] = sid

            if student_map:

                selected = st.selectbox(
                    "Student",
                    list(
                        student_map.keys()
                    ),
                    key="remove_student"
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

    hero(
        "Teachers",
        "Teacher accounts.",
        "SCHOOL"
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
        "Teachers",
        len(teachers)
    )

    c2.metric(
        "Active",
        len(active)
    )

    with st.expander(
        "Create Teacher"
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
                "Password",
                type="password",
                key="create_teacher_password"
            )

        if st.button(
            "Create Teacher",
            key="create_teacher"
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

            elif len(
                teacher_password
            ) < 6:

                st.error(
                    "Password must be at least 6 characters."
                )

            elif db is None:

                st.error(
                    "Database unavailable."
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
                                    teacher_password
                                ),
                            "enabled":
                                True,
                        }
                    ).execute()

                    st.success(
                        "Teacher created."
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Could not create teacher: {error}"
                    )

    st.subheader(
        "Teacher Accounts"
    )

    if not teachers:

        st.info(
            "No teachers yet."
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

        rows.append(
            {
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
            }
        )

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
                    f"{tid} • {name}"
                ] = teacher

        if teacher_map:

            selected = st.selectbox(
                "Teacher",
                list(
                    teacher_map.keys()
                ),
                key="manage_teacher"
            )

            teacher = teacher_map[
                selected
            ]

            enabled = bool(
                teacher.get(
                    "enabled",
                    True
                )
            )

            c1, c2 = st.columns(2)

            with c1:

                label = (
                    "Disable"
                    if enabled
                    else "Enable"
                )

                if st.button(
                    label,
                    key="toggle_teacher"
                ):

                    try:

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
                    "Delete",
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
# SMART ATTENDANCE
# ============================================================

def attendance_page():

    hero(
        "Smart Attendance",
        "Fast classroom attendance.",
        "EDUVISION"
    )

    students = active_students_only(
        load_students()
    )

    camera_tab, manual_tab, records_tab = (
        st.tabs(
            [
                "Camera",
                "Manual",
                "Records"
            ]
        )
    )

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    with camera_tab:

        st.write("")

        feature_card(
            "Camera Attendance",
            "Recognize registered students."
        )

        try:

            from smart_attendance import (
                render_page
                as render_smart_attendance
            )

            render_smart_attendance()

        except Exception as error:

            st.error(
                "Smart Attendance could not start."
            )

            with st.expander(
                "Technical Details"
            ):

                st.code(
                    str(error)
                )

    # --------------------------------------------------------
    # MANUAL
    # --------------------------------------------------------

    with manual_tab:

        st.write("")

        feature_card(
            "Manual Attendance",
            "Update today's attendance."
        )

        if students.empty:

            st.info(
                "No active students."
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
                        f"{sid} • {name}"
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
                    key="save_attendance"
                ):

                    if db is None:

                        st.error(
                            "Database unavailable."
                        )

                    else:

                        student = student_map[
                            selected
                        ]

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
                                ).update(
                                    {
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
                                    }
                                ).eq(
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
                                f"{record['name']} • {status_choice}"
                            )

                        except Exception as error:

                            st.error(
                                f"Could not save attendance: {error}"
                            )

    # --------------------------------------------------------
    # RECORDS
    # --------------------------------------------------------

    with records_tab:

        st.write("")

        attendance = load_attendance()

        if attendance.empty:

            st.info(
                "No attendance records."
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
                    "status"
                ]
                if column
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
# SMART OCCUPANCY
# ============================================================

def occupancy_page():

    hero(
        "Smart Occupancy",
        "Live classroom monitoring.",
        "EDUVISION"
    )

    feature_card(
        "Live Classroom",
        "Start the camera to monitor occupancy."
    )

    try:

        from smart_occupancy import (
            render_page
            as render_smart_occupancy
        )

        render_smart_occupancy()

    except Exception as error:

        st.error(
            "Smart Occupancy could not start."
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

    hero(
        "Reports",
        "Attendance overview.",
        "EDUVISION"
    )

    students = active_students_only(
        load_students()
    )

    attendance = load_attendance()

    total_records = len(
        attendance
    )

    present = 0
    late = 0
    absent = 0

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

    overall = (
        round(
            (
                present + late
            )
            / total_records
            * 100,
            1
        )
        if total_records
        else 0.0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Students",
        len(students)
    )

    c2.metric(
        "Present",
        present
    )

    c3.metric(
        "Absent",
        absent
    )

    c4.metric(
        "Attendance",
        f"{overall}%"
    )

    st.write("")

    if attendance.empty:

        st.info(
            "No attendance records."
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
                "status"
            ]
            if column
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

    hero(
        "Settings",
        "School account.",
        "EDUVISION"
    )

    with st.container(
        border=True
    ):

        st.subheader(
            "School"
        )

        st.write(
            f"**{st.session_state.school_name}**"
        )

        st.write(
            f"School ID • "
            f"{st.session_state.school_id}"
        )

        st.write(
            f"Role • "
            f"{st.session_state.role}"
        )

        account = (
            st.session_state.user_name
            or st.session_state.user_id
        )

        st.write(
            f"Account • {account}"
        )

    st.write("")

    with st.container(
        border=True
    ):

        st.subheader(
            "System"
        )

        if db is not None:

            st.success(
                "● Database Connected"
            )

        else:

            st.error(
                "Database unavailable."
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

        st.session_state.screen = (
            "school_login"
        )

        st.rerun()

    with st.sidebar:

        st.title(
            "EduVision"
        )

        st.caption(
            "SMART CLASSROOM"
        )

        st.write("")

        with st.container(
            border=True
        ):

            st.caption(
                "SCHOOL"
            )

            st.write(
                f"**{st.session_state.school_name}**"
            )

            st.caption(
                st.session_state.role
            )

        st.write("")

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
    current_screen == "platform_admin"
    and st.session_state.logged_in
    and st.session_state.role
    == "EduVision Admin"
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

    clear_login()

    st.session_state.screen = (
        "welcome"
    )

    st.rerun()

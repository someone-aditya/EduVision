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
    if (
        not SUPABASE_URL
        and hasattr(st, "secrets")
        and "SUPABASE_URL" in st.secrets
    ):
        SUPABASE_URL = str(st.secrets["SUPABASE_URL"])

    if (
        not SUPABASE_KEY
        and hasattr(st, "secrets")
        and "SUPABASE_KEY" in st.secrets
    ):
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
        and hasattr(st, "secrets")
        and "EDUVISION_ADMIN_ID" in st.secrets
    ):
        EDUVISION_ADMIN_ID = str(
            st.secrets["EDUVISION_ADMIN_ID"]
        )

    if (
        not os.getenv("EDUVISION_ADMIN_PASSWORD")
        and hasattr(st, "secrets")
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

def clean_supabase_url(url: str) -> str:
    if not url:
        return ""

    u = str(url).strip().strip("'\"")

    changed = True

    while changed:
        changed = False

        if u.endswith("/"):
            u = u[:-1]
            changed = True

        if u.endswith("/rest/v1"):
            u = u[:-8]
            changed = True

    if u.startswith("https:///"):
        u = "https://" + u[9:]

    elif u.startswith("http:///"):
        u = "http://" + u[8:]

    return u


def clean_supabase_key(key: str) -> str:
    if not key:
        return ""

    return str(key).strip().strip("'\"")


@st.cache_resource
def get_database():

    if create_client is None:
        raise RuntimeError(
            "The supabase library is not installed."
        )

    clean_url = clean_supabase_url(SUPABASE_URL)
    clean_key = clean_supabase_key(SUPABASE_KEY)

    if not clean_url:
        raise RuntimeError(
            "SUPABASE_URL is missing."
        )

    if not clean_key:
        raise RuntimeError(
            "SUPABASE_KEY is missing."
        )

    return create_client(
        clean_url,
        clean_key
    )


db = None
db_error_message = None

try:
    db = get_database()

except Exception as error:
    db_error_message = str(error)


# ============================================================
# WHITE MINIMALIST UI
# ============================================================

st.markdown(
    """
    <style>

    :root {
        --bg: #f7f7f5;
        --card: #ffffff;
        --text: #111111;
        --muted: #6b7280;
        --border: #dedede;
    }

    html,
    body,
    [data-testid="stAppViewContainer"],
    .stApp {
        background: #f7f7f5 !important;
        color: #111111 !important;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            sans-serif !important;
    }

    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        color: #111111 !important;
    }

    p {
        color: #374151;
    }

    label {
        color: #374151 !important;
        font-weight: 650 !important;
    }

    div.stButton > button {
        width: 100%;
        min-height: 44px;

        background: #111111 !important;
        color: #ffffff !important;

        border: 1px solid #111111 !important;
        border-radius: 6px !important;

        font-weight: 700 !important;

        box-shadow: none !important;

        transition:
            background 0.15s ease,
            border-color 0.15s ease !important;
    }

    div.stButton > button:hover {
        background: #333333 !important;
        color: #ffffff !important;
        border-color: #333333 !important;

        transform: none !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"] {
        background: #ffffff !important;

        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;

        box-shadow: none !important;
    }

    div[data-baseweb="input"] input {
        background: #ffffff !important;

        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #111111 !important;
        box-shadow: none !important;
    }

    input::placeholder {
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }

    div[data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #111111 !important;

        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;

        box-shadow: none !important;
    }

    div[data-baseweb="select"] span {
        color: #111111 !important;
    }

    li[role="option"] {
        color: #111111 !important;
        background: #ffffff !important;
    }

    li[role="option"]:hover {
        background: #f3f4f6 !important;
    }

    [data-testid="stMetric"] {
        background: #ffffff !important;

        border: 1px solid #dedede !important;
        border-radius: 8px !important;

        padding: 18px 20px !important;

        box-shadow: none !important;
    }

    [data-testid="stMetricLabel"] {
        color: #6b7280 !important;
    }

    [data-testid="stMetricValue"] {
        color: #111111 !important;

        font-weight: 850 !important;
        font-size: 2rem !important;
    }

    button[data-baseweb="tab"] {
        color: #6b7280 !important;
        font-weight: 700 !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #111111 !important;
    }

    [data-testid="stExpander"] {
        background: #ffffff !important;

        border: 1px solid #dedede !important;
        border-radius: 8px !important;

        box-shadow: none !important;
    }

    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #dedede !important;
    }

    [data-testid="stSidebar"] * {
        color: #111111;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 9px 12px;
        margin-bottom: 4px;

        border-radius: 6px;

        border: 1px solid transparent;
        background: transparent;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: #f3f4f6;
        border-color: #e5e7eb;
    }

    [data-testid="stDataFrame"] {
        background: #ffffff !important;

        border: 1px solid #dedede !important;
        border-radius: 8px !important;

        overflow: hidden !important;

        box-shadow: none !important;
    }

    [data-testid="stAlert"] {
        border-radius: 6px !important;
        box-shadow: none !important;
    }

    hr {
        border-color: #e5e7eb !important;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    @media (max-width: 700px) {

        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }
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
            .eq(
                "school_id",
                str(school_id).strip()
            )
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as error:
        print(
            f"get_school error: {error}"
        )

    return None


def get_school_by_admin(
    school_id,
    admin_id
):

    if not db or not school_id or not admin_id:
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
            f"get_school_by_admin error: {error}"
        )

    return None


def get_teacher(
    school_id,
    teacher_id
):

    if not db or not school_id or not teacher_id:
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
            f"get_teacher error: {error}"
        )

    return None


def load_students():

    if (
        not db
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
            .order("name")
            .execute()
        )

        if response.data:
            return pd.DataFrame(
                response.data
            )

    except Exception:

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


def load_attendance():

    if (
        not db
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

    except Exception:

        try:

            response = (
                db.table("attendance")
                .select("*")
                .eq(
                    "school_id",
                    st.session_state.school_id
                )
                .order(
                    "attendance_date",
                    desc=True
                )
                .execute()
            )

            if response.data:
                return pd.DataFrame(
                    response.data
                )

        except Exception:

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
                    return pd.DataFrame(
                        response.data
                    )

            except Exception as error:

                st.error(
                    f"Could not load attendance: {error}"
                )

    return pd.DataFrame()


# ============================================================
# WELCOME
# ============================================================

def welcome_screen():

    st.markdown(
        """
        <div style="
            max-width:900px;
            margin:70px auto 35px;
            text-align:center;
            padding:20px;
        ">

            <div style="
                font-size:0.85rem;
                font-weight:800;
                letter-spacing:0.10em;
                color:#6b7280;
                margin-bottom:18px;
            ">
                AI • SMART CLASSROOM
            </div>

            <div style="
                font-size:clamp(3.5rem,9vw,6.5rem);
                font-weight:950;
                letter-spacing:-0.065em;
                line-height:0.95;
                color:#111111;
                margin-bottom:24px;
            ">
                EduVision
            </div>

            <div style="
                max-width:650px;
                margin:0 auto;
                color:#6b7280;
                font-size:1.05rem;
                line-height:1.7;
            ">
                Smarter classrooms through fast attendance,
                classroom monitoring and simple management.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    left, button_col, right = st.columns(
        [1.3, 1, 1.3]
    )

    with button_col:

        if st.button(
            "Enter EduVision →",
            key="enter_eduvision_btn",
            use_container_width=True
        ):

            st.session_state.screen = "portal"

            st.rerun()

    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:24px;
            color:#6b7280;
            font-size:0.82rem;
            font-weight:650;
        ">

            <span style="
                display:inline-block;
                width:7px;
                height:7px;
                border-radius:50%;
                background:#22c55e;
                margin-right:7px;
            "></span>

            System Online

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PORTAL
# ============================================================

def portal_screen():

    top1, top2 = st.columns(
        [4, 1]
    )

    with top1:

        st.markdown(
            """
            <div style="
                font-size:1.5rem;
                font-weight:900;
                color:#111111;
            ">
                EduVision
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top2:

        if st.button(
            "← Back",
            key="portal_back_welcome",
            use_container_width=True
        ):
            go_welcome()

    st.markdown(
        """
        <div style="
            margin:45px 0 35px;
        ">

            <div style="
                color:#111111;
                font-size:clamp(2.2rem,5vw,3.8rem);
                font-weight:900;
                letter-spacing:-0.055em;
            ">
                Choose your workspace
            </div>

            <div style="
                color:#6b7280;
                font-size:1rem;
                margin-top:10px;
            ">
                Select how you want to access EduVision.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    school_col, admin_col = st.columns(
        2,
        gap="large"
    )

    with school_col:

        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:32px;
                min-height:180px;
            ">

                <div style="
                    font-size:1.4rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:12px;
                ">
                    School Portal
                </div>

                <div style="
                    color:#6b7280;
                    line-height:1.6;
                ">
                    Access your school workspace for
                    attendance, students and classroom
                    management.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        if st.button(
            "Open School Portal →",
            key="open_school_portal_btn",
            use_container_width=True
        ):

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    with admin_col:

        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:32px;
                min-height:180px;
            ">

                <div style="
                    font-size:1.4rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:12px;
                ">
                    EduVision Admin
                </div>

                <div style="
                    color:#6b7280;
                    line-height:1.6;
                ">
                    Review and manage school
                    registration requests.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        if st.button(
            "Open Admin →",
            key="open_admin_portal_btn",
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

    c_title, c_back = st.columns(
        [4, 1]
    )

    with c_title:

        st.markdown(
            """
            <div style="margin-bottom:18px;">

                <div style="
                    font-size:2rem;
                    font-weight:900;
                    color:#111111;
                ">
                    School Portal
                </div>

                <div style="
                    color:#6b7280;
                    margin-top:5px;
                ">
                    Register a school or access
                    an approved school.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_back:

        if st.button(
            "← Back",
            key="portal_back_btn",
            use_container_width=True
        ):
            go_portal()

    st.divider()

    register_tab, open_tab = st.tabs(
        [
            "Register School",
            "Open School",
        ]
    )

    # ------------------------------------------------------------
    # REGISTER
    # ------------------------------------------------------------

    with register_tab:

        st.markdown(
            "### Create a school workspace"
        )

        st.caption(
            "Registration must be approved before the school can be accessed."
        )

        c1, c2 = st.columns(2)

        with c1:

            school_name = st.text_input(
                "School Name",
                placeholder="Enter school name",
                key="reg_school_name"
            )

            admin_id = st.text_input(
                "School Admin ID",
                placeholder="Create admin ID",
                key="reg_admin_id"
            )

        with c2:

            admin_password = st.text_input(
                "Admin Password",
                type="password",
                placeholder="Minimum 6 characters",
                key="reg_admin_pwd"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Repeat password",
                key="reg_admin_confirm"
            )

        st.write("")

        if st.button(
            "Submit Registration",
            key="submit_reg_btn",
            use_container_width=True
        ):

            school_name = (
                school_name.strip()
            )

            admin_id = (
                admin_id.strip()
            )

            if not school_name:

                st.error(
                    "Please enter your school name."
                )

            elif not admin_id:

                st.error(
                    "Please enter a School Admin ID."
                )

            elif len(admin_password) < 6:

                st.error(
                    "Password must be at least 6 characters long."
                )

            elif (
                admin_password
                != confirm_password
            ):

                st.error(
                    "Passwords do not match."
                )

            elif not db:

                st.error(
                    "Database connection is unavailable."
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
                        "School registration submitted successfully."
                    )

                    st.markdown(
                        f"""
                        <div style="
                            background:#ffffff;
                            border:1px solid #dedede;
                            border-radius:8px;
                            padding:22px;
                            margin-top:18px;
                        ">

                            <div style="
                                color:#6b7280;
                                font-size:0.8rem;
                                font-weight:700;
                            ">
                                SAVE THESE DETAILS
                            </div>

                            <div style="
                                font-size:1.3rem;
                                font-weight:850;
                                margin-top:8px;
                            ">
                                School ID: {school_id}
                            </div>

                            <div style="
                                margin-top:5px;
                            ">
                                Admin ID:
                                <strong>
                                    {admin_id}
                                </strong>
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                except Exception as error:

                    st.error(
                        f"School registration failed: {error}"
                    )

    # ------------------------------------------------------------
    # OPEN SCHOOL
    # ------------------------------------------------------------

    with open_tab:

        st.markdown(
            "### Open your school"
        )

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
                    f"Could not load school list: {error}"
                )

        if not approved_schools:

            st.info(
                "No approved schools are currently available."
            )

        else:

            school_name_to_id = {
                school["school_name"]:
                    school["school_id"]

                for school
                in approved_schools
            }

            school_names = sorted(
                school_name_to_id.keys()
            )

            selected_name = st.selectbox(
                "School",
                school_names,
                key="open_school_name_select"
            )

            st.write("")

            if st.button(
                "Continue →",
                key="open_school_action_btn",
                use_container_width=True
            ):

                selected_id = (
                    school_name_to_id.get(
                        selected_name,
                        ""
                    )
                )

                school = get_school(
                    selected_id
                )

                if not school:

                    st.error(
                        "School record not found."
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
            "School workspace not found."
        )

        if st.button(
            "← Return to School Portal"
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

        st.markdown(
            f"""
            <div style="margin-bottom:18px;">

                <div style="
                    font-size:2rem;
                    font-weight:900;
                ">
                    {school['school_name']}
                </div>

                <div style="
                    color:#6b7280;
                    margin-top:5px;
                ">
                    School ID: {school_id}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        if st.button(
            "← Change School",
            key="change_school_btn",
            use_container_width=True
        ):

            clear_login()

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    st.divider()

    admin_tab, teacher_tab = st.tabs(
        [
            "School Admin",
            "Teacher",
        ]
    )

    # ------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------

    with admin_tab:

        _, center, _ = st.columns(
            [1, 2, 1]
        )

        with center:

            st.markdown(
                "### Admin Login"
            )

            st.caption(
                "Sign in to manage your school."
            )

            admin_id = st.text_input(
                "Admin ID",
                key="school_admin_id_input"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="school_admin_pwd_input"
            )

            if st.button(
                "Login",
                key="login_admin_action",
                use_container_width=True
            ):

                admin_id_clean = (
                    admin_id.strip()
                )

                school_account = (
                    get_school_by_admin(
                        school_id,
                        admin_id_clean
                    )
                )

                if (
                    school_account
                    and hash_password(password)
                    == school_account.get(
                        "admin_password_hash"
                    )
                ):

                    st.session_state.logged_in = True
                    st.session_state.role = (
                        "School Admin"
                    )
                    st.session_state.user_id = (
                        admin_id_clean
                    )
                    st.session_state.user_name = (
                        f"{school['school_name']} Admin"
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

    # ------------------------------------------------------------
    # TEACHER
    # ------------------------------------------------------------

    with teacher_tab:

        _, center, _ = st.columns(
            [1, 2, 1]
        )

        with center:

            st.markdown(
                "### Teacher Login"
            )

            st.caption(
                "Sign in to access your classroom."
            )

            teacher_id = st.text_input(
                "Teacher ID",
                key="teacher_id_input"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="teacher_pwd_input"
            )

            if st.button(
                "Login",
                key="login_teacher_action",
                use_container_width=True
            ):

                teacher_id_clean = (
                    teacher_id.strip()
                )

                teacher = get_teacher(
                    school_id,
                    teacher_id_clean
                )

                if not teacher:

                    st.error(
                        "Teacher account not found for this school."
                    )

                elif not teacher.get(
                    "enabled",
                    True
                ):

                    st.error(
                        "This teacher account has been disabled."
                    )

                elif (
                    hash_password(password)
                    != teacher.get(
                        "password_hash"
                    )
                ):

                    st.error(
                        "Incorrect teacher password."
                    )

                else:

                    st.session_state.logged_in = True
                    st.session_state.role = (
                        "Teacher"
                    )
                    st.session_state.user_id = (
                        teacher_id_clean
                    )

                    st.session_state.user_name = (
                        teacher.get(
                            "teacher_name"
                        )
                        or teacher.get("name")
                        or teacher_id_clean
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

        st.markdown(
            """
            <div style="margin-bottom:18px;">

                <div style="
                    font-size:2rem;
                    font-weight:900;
                ">
                    EduVision Admin
                </div>

                <div style="
                    color:#6b7280;
                    margin-top:5px;
                ">
                    Manage school registrations.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        if st.button(
            "← Back",
            key="admin_login_back",
            use_container_width=True
        ):
            go_portal()

    st.divider()

    _, center, _ = st.columns(
        [1, 2, 1]
    )

    with center:

        st.markdown(
            "### Admin Login"
        )

        admin_id = st.text_input(
            "Admin ID",
            key="plat_admin_id"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="plat_admin_pwd"
        )

        if st.button(
            "Login",
            key="plat_login_btn",
            use_container_width=True
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
        [4, 1]
    )

    with c1:

        st.markdown(
            """
            <div style="margin-bottom:18px;">

                <div style="
                    font-size:2rem;
                    font-weight:900;
                ">
                    EduVision Admin
                </div>

                <div style="
                    color:#6b7280;
                    margin-top:5px;
                ">
                    Review and manage school
                    registration requests.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        if st.button(
            "Log Out",
            key="master_logout_btn",
            use_container_width=True
        ):
            go_portal()

    st.divider()

    schools = []

    if db:

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

            schools = (
                response.data or []
            )

        except Exception:

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
                    f"Error loading schools: {error}"
                )

    pending = [
        s for s in schools
        if s.get(
            "approval_status"
        ) == "pending"
    ]

    approved = [
        s for s in schools
        if s.get(
            "approval_status"
        ) == "approved"
    ]

    rejected = [
        s for s in schools
        if s.get(
            "approval_status"
        ) == "rejected"
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

    tab1, tab2, tab3 = st.tabs(
        [
            f"Pending ({len(pending)})",
            f"Approved ({len(approved)})",
            f"Rejected ({len(rejected)})",
        ]
    )

    # ------------------------------------------------------------
    # PENDING
    # ------------------------------------------------------------

    with tab1:

        st.markdown(
            "### Pending Registrations"
        )

        if not pending:

            st.info(
                "No school registrations are waiting for approval."
            )

        for school in pending:

            school_id = school.get(
                "school_id",
                ""
            )

            school_name = school.get(
                "school_name",
                "Unnamed School"
            )

            admin_id = school.get(
                "admin_id",
                ""
            )

            st.markdown(
                f"""
                <div style="
                    background:#ffffff;
                    border:1px solid #dedede;
                    border-radius:8px;
                    padding:22px;
                    margin:16px 0 12px;
                ">

                    <div style="
                        font-size:1.2rem;
                        font-weight:850;
                    ">
                        {school_name}
                    </div>

                    <div style="
                        color:#6b7280;
                        margin-top:10px;
                    ">
                        School ID: {school_id}
                        <br>
                        Admin ID: {admin_id}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            approve_col, reject_col = (
                st.columns(2)
            )

            with approve_col:

                if st.button(
                    "Approve",
                    key=f"app_{school_id}",
                    use_container_width=True
                ):

                    try:

                        payload = {
                            "approval_status":
                                "approved",

                            "approved_by":
                                st.session_state.user_id,

                            "approved_at":
                                datetime.now(
                                    timezone.utc
                                ).isoformat(),
                        }

                        (
                            db.table("schools")
                            .update(payload)
                            .eq(
                                "school_id",
                                school_id
                            )
                            .execute()
                        )

                        st.rerun()

                    except Exception:

                        try:

                            (
                                db.table("schools")
                                .update({
                                    "approval_status":
                                        "approved"
                                })
                                .eq(
                                    "school_id",
                                    school_id
                                )
                                .execute()
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"Approval error: {error}"
                            )

            with reject_col:

                if st.button(
                    "Reject",
                    key=f"rej_{school_id}",
                    use_container_width=True
                ):

                    try:

                        (
                            db.table("schools")
                            .update({
                                "approval_status":
                                    "rejected"
                            })
                            .eq(
                                "school_id",
                                school_id
                            )
                            .execute()
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Rejection error: {error}"
                        )

    # ------------------------------------------------------------
    # APPROVED
    # ------------------------------------------------------------

    with tab2:

        st.markdown(
            "### Approved Schools"
        )

        if not approved:

            st.info(
                "No schools have been approved yet."
            )

        else:

            rows = []

            for school in approved:

                rows.append(
                    {
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
                    }
                )

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )

    # ------------------------------------------------------------
    # REJECTED
    # ------------------------------------------------------------

    with tab3:

        st.markdown(
            "### Rejected Schools"
        )

        if not rejected:

            st.info(
                "No rejected school registrations."
            )

        for school in rejected:

            school_id = school.get(
                "school_id",
                ""
            )

            school_name = school.get(
                "school_name",
                ""
            )

            st.markdown(
                f"""
                <div style="
                    background:#ffffff;
                    border:1px solid #dedede;
                    border-radius:8px;
                    padding:18px;
                    margin:14px 0;
                ">
                    <strong>
                        {school_name}
                    </strong>

                    <div style="
                        color:#6b7280;
                        margin-top:5px;
                    ">
                        School ID:
                        {school_id}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Restore to Pending",
                key=f"restore_{school_id}",
                use_container_width=True
            ):

                try:

                    (
                        db.table("schools")
                        .update({
                            "approval_status":
                                "pending"
                        })
                        .eq(
                            "school_id",
                            school_id
                        )
                        .execute()
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        str(error)
                    )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():

    students = load_students()
    attendance = load_attendance()

    today_str = (
        datetime.now()
        .strftime("%Y-%m-%d")
    )

    present_today = 0
    late_today = 0
    absent_today = 0

    if (
        not attendance.empty
        and "attendance_date"
        in attendance.columns
    ):

        today_rows = attendance[
            attendance[
                "attendance_date"
            ].astype(str) == today_str
        ]

        if "status" in today_rows.columns:

            present_today = len(
                today_rows[
                    today_rows["status"]
                    == "Present"
                ]
            )

            late_today = len(
                today_rows[
                    today_rows["status"]
                    == "Late"
                ]
            )

            absent_today = len(
                today_rows[
                    today_rows["status"]
                    == "Absent"
                ]
            )

    total_students = len(
        students
    )

    attendance_percentage = (
        round(
            (
                present_today
                / total_students
            ) * 100,
            1
        )
        if total_students > 0
        else 0.0
    )

    current_hour = (
        datetime.now().hour
    )

    if current_hour < 12:
        greeting = "Good Morning"

    elif current_hour < 17:
        greeting = "Good Afternoon"

    else:
        greeting = "Good Evening"

    user_display = (
        st.session_state.user_name
        or st.session_state.user_id
        or "Educator"
    )

    st.markdown(
        f"""
        <div style="margin-bottom:32px;">

            <div style="
                font-size:2.2rem;
                font-weight:900;
                color:#111111;
            ">
                {greeting}, {user_display}
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                {st.session_state.school_name}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### Today's Overview"
    )

    m1, m2, m3, m4 = (
        st.columns(4)
    )

    with m1:
        st.metric(
            "Students",
            total_students
        )

    with m2:
        st.metric(
            "Present",
            present_today
        )

    with m3:
        st.metric(
            "Absent",
            absent_today
        )

    with m4:
        st.metric(
            "Attendance",
            f"{attendance_percentage}%"
        )

    st.write("")

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:20px 24px;
            margin-bottom:32px;
        ">

            Present: <strong>
                {present_today}
            </strong>

            &nbsp;&nbsp;&nbsp;

            Late: <strong>
                {late_today}
            </strong>

            &nbsp;&nbsp;&nbsp;

            Absent: <strong>
                {absent_today}
            </strong>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### Quick Actions"
    )

    a1, a2 = st.columns(2)

    with a1:

        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:24px;
                min-height:125px;
            ">

                <div style="
                    font-size:1.2rem;
                    font-weight:850;
                ">
                    Smart Attendance
                </div>

                <div style="
                    color:#6b7280;
                    margin-top:8px;
                ">
                    Take and review classroom
                    attendance.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        if st.button(
            "Open Attendance →",
            key="dash_goto_attendance",
            use_container_width=True
        ):

            st.session_state.nav_page = (
                "Smart Attendance"
            )

            st.session_state[
                "sidebar_nav_radio"
            ] = "Smart Attendance"

            st.rerun()

    with a2:

        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:24px;
                min-height:125px;
            ">

                <div style="
                    font-size:1.2rem;
                    font-weight:850;
                ">
                    Smart Occupancy
                </div>

                <div style="
                    color:#6b7280;
                    margin-top:8px;
                ">
                    Monitor classroom occupancy
                    and room status.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        if st.button(
            "Open Occupancy →",
            key="dash_goto_occupancy",
            use_container_width=True
        ):

            st.session_state.nav_page = (
                "Smart Occupancy"
            )

            st.session_state[
                "sidebar_nav_radio"
            ] = "Smart Occupancy"

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

    st.markdown(
        """
        <div style="margin-bottom:28px;">

            <div style="
                font-size:2rem;
                font-weight:900;
            ">
                Students
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                View and manage student registrations.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    students = load_students()

    if (
        students.empty
        or "status"
        not in students.columns
    ):

        pending_students = (
            pd.DataFrame()
        )

        active_students = (
            students.copy()
        )

        declined_students = (
            pd.DataFrame()
        )

    else:

        status = (
            students["status"]
            .fillna("Active")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        pending_students = (
            students[
                status == "pending"
            ].copy()
        )

        declined_students = (
            students[
                status == "declined"
            ].copy()
        )

        active_students = (
            students[
                ~status.isin(
                    [
                        "pending",
                        "declined"
                    ]
                )
            ].copy()
        )

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

    # ------------------------------------------------------------
    # TEACHER REGISTER
    # ------------------------------------------------------------

    if is_teacher:

        with st.expander(
            "Register New Student"
        ):

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID",
                    key="teacher_reg_student_id"
                )

                student_name = st.text_input(
                    "Full Name",
                    key="teacher_reg_student_name"
                )

            with c2:

                class_name = st.text_input(
                    "Class / Grade",
                    key="teacher_reg_student_class"
                )

                roll_no = st.text_input(
                    "Roll Number",
                    key="teacher_reg_student_roll"
                )

            if st.button(
                "Submit for Approval",
                key="teacher_submit_student_btn",
                use_container_width=True
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
                        "Please enter a Student ID."
                    )

                elif not student_name:

                    st.error(
                        "Please enter the student's name."
                    )

                elif not class_name:

                    st.error(
                        "Please enter the student's class."
                    )

                elif not db:

                    st.error(
                        "Database connection unavailable."
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
                            "Student submitted for approval."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Could not submit student: {error}"
                        )

    # ------------------------------------------------------------
    # ADMIN APPROVAL
    # ------------------------------------------------------------

    if is_admin:

        st.markdown(
            "### Pending Registrations"
        )

        if pending_students.empty:

            st.info(
                "No student registrations are waiting for approval."
            )

        else:

            visible = [
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
                pending_students[visible],
                use_container_width=True,
                hide_index=True
            )

            pending_map = {
                f"{row.get('student_id')} — {row.get('name')}":
                    row.get("student_id")

                for _, row
                in pending_students.iterrows()
            }

            selected = st.selectbox(
                "Select Student",
                list(
                    pending_map.keys()
                ),
                key="pending_student_review_select"
            )

            selected_id = (
                pending_map[selected]
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "Approve",
                    key="approve_student_btn",
                    use_container_width=True
                ):

                    try:

                        (
                            db.table("students")
                            .update({
                                "status":
                                    "Active"
                            })
                            .eq(
                                "school_id",
                                st.session_state.school_id
                            )
                            .eq(
                                "student_id",
                                selected_id
                            )
                            .execute()
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

            with c2:

                if st.button(
                    "Decline",
                    key="decline_student_btn",
                    use_container_width=True
                ):

                    try:

                        (
                            db.table("students")
                            .update({
                                "status":
                                    "Declined"
                            })
                            .eq(
                                "school_id",
                                st.session_state.school_id
                            )
                            .eq(
                                "student_id",
                                selected_id
                            )
                            .execute()
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            str(error)
                        )

    # ------------------------------------------------------------
    # ACTIVE
    # ------------------------------------------------------------

    st.markdown(
        "### Active Students"
    )

    if active_students.empty:

        st.info(
            "No approved students are currently registered."
        )

    else:

        visible = [
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
            active_students[visible],
            use_container_width=True,
            hide_index=True
        )

    # ------------------------------------------------------------
    # PENDING FOR TEACHER
    # ------------------------------------------------------------

    if (
        is_teacher
        and not pending_students.empty
    ):

        with st.expander(
            f"Pending Registrations ({len(pending_students)})"
        ):

            visible = [
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
                pending_students[visible],
                use_container_width=True,
                hide_index=True
            )

    # ------------------------------------------------------------
    # REMOVE
    # ------------------------------------------------------------

    if (
        is_admin
        and not students.empty
    ):

        st.divider()

        with st.expander(
            "Remove Student"
        ):

            student_map = {
                f"{row.get('student_id')} — {row.get('name')}":
                    row.get("student_id")

                for _, row
                in students.iterrows()
            }

            selected = st.selectbox(
                "Student",
                list(
                    student_map.keys()
                ),
                key="del_student_select"
            )

            if st.button(
                "Remove Student",
                key="del_student_btn",
                use_container_width=True
            ):

                sid = (
                    student_map[selected]
                )

                try:

                    (
                        db.table("students")
                        .delete()
                        .eq(
                            "school_id",
                            st.session_state.school_id
                        )
                        .eq(
                            "student_id",
                            sid
                        )
                        .execute()
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

    if (
        st.session_state.role
        != "School Admin"
    ):

        st.error(
            "School Admin access required."
        )

        return

    st.markdown(
        """
        <div style="margin-bottom:28px;">

            <div style="
                font-size:2rem;
                font-weight:900;
            ">
                Teachers
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                Create and manage teacher accounts.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
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

            teachers = (
                response.data or []
            )

        except Exception as error:

            st.error(
                f"Error loading teachers: {error}"
            )

    active_teachers = [
        t for t in teachers
        if t.get(
            "enabled",
            True
        )
    ]

    m1, m2 = st.columns(2)

    with m1:

        st.metric(
            "Total Teachers",
            len(teachers)
        )

    with m2:

        st.metric(
            "Active Accounts",
            len(active_teachers)
        )

    with st.expander(
        "Create Teacher Account"
    ):

        c1, c2 = st.columns(2)

        with c1:

            t_id = st.text_input(
                "Teacher ID",
                key="add_t_id"
            )

            t_name = st.text_input(
                "Teacher Name",
                key="add_t_name"
            )

        with c2:

            t_pwd = st.text_input(
                "Temporary Password",
                type="password",
                key="add_t_pwd"
            )

        if st.button(
            "Create Teacher",
            key="submit_add_teacher_btn",
            use_container_width=True
        ):

            t_id = t_id.strip()
            t_name = t_name.strip()

            if not t_id:

                st.error(
                    "Please enter a Teacher ID."
                )

            elif not t_name:

                st.error(
                    "Please enter the teacher's name."
                )

            elif len(t_pwd) < 6:

                st.error(
                    "Password must be at least 6 characters."
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
                                t_id,

                            "teacher_name":
                                t_name,

                            "password_hash":
                                hash_password(
                                    t_pwd
                                ),

                            "enabled":
                                True,
                        }
                    ).execute()

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Could not create teacher: {error}"
                    )

    st.markdown(
        "### Teacher Accounts"
    )

    if not teachers:

        st.info(
            "No teacher accounts have been created yet."
        )

        return

    rows = []

    for teacher in teachers:

        name = (
            teacher.get(
                "teacher_name"
            )
            or teacher.get("name")
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
                    (
                        "Enabled"
                        if teacher.get(
                            "enabled",
                            True
                        )
                        else "Disabled"
                    ),
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

        options = {}

        for teacher in teachers:

            tid = teacher.get(
                "teacher_id",
                ""
            )

            name = (
                teacher.get(
                    "teacher_name"
                )
                or teacher.get("name")
                or tid
            )

            options[
                f"{tid} — {name}"
            ] = teacher

        selected = st.selectbox(
            "Teacher",
            list(options.keys()),
            key="manage_t_select"
        )

        target = (
            options[selected]
        )

        enabled = target.get(
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
                key="toggle_teacher_status",
                use_container_width=True
            ):

                try:

                    (
                        db.table("teachers")
                        .update({
                            "enabled":
                                not enabled
                        })
                        .eq(
                            "school_id",
                            st.session_state.school_id
                        )
                        .eq(
                            "teacher_id",
                            target[
                                "teacher_id"
                            ]
                        )
                        .execute()
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        str(error)
                    )

        with c2:

            if st.button(
                "Delete Teacher",
                key="delete_teacher_btn",
                use_container_width=True
            ):

                try:

                    (
                        db.table("teachers")
                        .delete()
                        .eq(
                            "school_id",
                            st.session_state.school_id
                        )
                        .eq(
                            "teacher_id",
                            target[
                                "teacher_id"
                            ]
                        )
                        .execute()
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        str(error)
                    )


# ============================================================
# SMART ATTENDANCE
# ============================================================

def attendance_page():

    st.markdown(
        """
        <div style="margin-bottom:28px;">

            <div style="
                font-size:2rem;
                font-weight:900;
            ">
                Smart Attendance
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                Take attendance and review attendance records.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    students = load_students()

    camera_tab, manual_tab, history_tab = (
        st.tabs(
            [
                "Camera",
                "Manual",
                "Records",
            ]
        )
    )

    # ------------------------------------------------------------
    # CAMERA
    # ------------------------------------------------------------

    with camera_tab:

        st.markdown(
            "### Camera Attendance"
        )

        st.caption(
            "Start the camera to recognize registered students and record attendance."
        )

        try:

            from smart_attendance import (
                render_page
                as render_smart_attendance
            )

            render_smart_attendance()

        except Exception as error:

            st.error(
                "Smart Attendance could not be started."
            )

            st.code(
                str(error)
            )

    # ------------------------------------------------------------
    # MANUAL
    # ------------------------------------------------------------

    with manual_tab:

        st.markdown(
            "### Manual Attendance"
        )

        if students.empty:

            st.info(
                "No students are currently registered."
            )

        else:

            student_opts = {
                f"{row.get('student_id')} — {row.get('name')}":
                    row

                for _, row
                in students.iterrows()
            }

            c1, c2 = st.columns(2)

            with c1:

                selected = st.selectbox(
                    "Student",
                    list(
                        student_opts.keys()
                    ),
                    key="man_student_select"
                )

            with c2:

                status_choice = (
                    st.selectbox(
                        "Status",
                        [
                            "Present",
                            "Late",
                            "Absent",
                        ],
                        key="man_status_select"
                    )
                )

            if st.button(
                "Save Attendance",
                key="save_manual_att_btn",
                use_container_width=True
            ):

                student = (
                    student_opts[selected]
                )

                now = datetime.now()

                date = now.strftime(
                    "%Y-%m-%d"
                )

                time = now.strftime(
                    "%H:%M:%S"
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
                        date,

                    "attendance_time":
                        time,

                    "status":
                        status_choice,
                }

                if not db:

                    st.error(
                        "Database unavailable."
                    )

                else:

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
                                date
                            )
                            .execute()
                        )

                        if existing.data:

                            (
                                db.table(
                                    "attendance"
                                )
                                .update({
                                    "name":
                                        record[
                                            "name"
                                        ],

                                    "class_name":
                                        record[
                                            "class_name"
                                        ],

                                    "attendance_time":
                                        time,

                                    "status":
                                        status_choice,
                                })
                                .eq(
                                    "id",
                                    existing.data[
                                        0
                                    ]["id"]
                                )
                                .execute()
                            )

                        else:

                            db.table(
                                "attendance"
                            ).insert(
                                record
                            ).execute()

                        st.success(
                            f"{record['name']} marked as {status_choice}."
                        )

                    except Exception as error:

                        st.error(
                            f"Could not save attendance: {error}"
                        )

    # ------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------

    with history_tab:

        st.markdown(
            "### Attendance Records"
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
                attendance[columns],
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# SMART OCCUPANCY
# ============================================================

def occupancy_page():

    st.markdown(
        """
        <div style="margin-bottom:28px;">

            <div style="
                font-size:2rem;
                font-weight:900;
            ">
                Smart Occupancy
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                Monitor classroom occupancy in real time.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:22px;
            margin-bottom:22px;
        ">

            <div style="
                font-size:1.2rem;
                font-weight:850;
            ">
                Live Classroom View
            </div>

            <div style="
                color:#6b7280;
                margin-top:6px;
            ">
                Start the camera to monitor
                the number of people present.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    try:

        from smart_occupancy import (
            render_page
            as render_smart_occupancy
        )

        render_smart_occupancy()

    except Exception as error:

        st.error(
            "Smart Occupancy could not be started."
        )

        st.code(
            str(error)
        )


# ============================================================
# REPORTS
# ============================================================

def reports_page():

    st.markdown(
        """
        <div style="margin-bottom:28px;">

            <div style="
                font-size:2rem;
                font-weight:900;
            ">
                Reports
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                View attendance statistics and records.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    students = load_students()
    attendance = load_attendance()

    total_records = len(
        attendance
    )

    present_count = 0

    if (
        not attendance.empty
        and "status"
        in attendance.columns
    ):

        present_count = len(
            attendance[
                attendance["status"]
                == "Present"
            ]
        )

    overall_pct = (
        round(
            (
                present_count
                / total_records
            ) * 100,
            1
        )
        if total_records > 0
        else 0.0
    )

    m1, m2, m3 = st.columns(3)

    with m1:

        st.metric(
            "Total Students",
            len(students)
        )

    with m2:

        st.metric(
            "Attendance Records",
            total_records
        )

    with m3:

        st.metric(
            "Present",
            present_count
        )

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:24px;
            margin:24px 0;
        ">

            <div style="
                color:#6b7280;
                font-size:0.8rem;
                font-weight:700;
            ">
                OVERALL ATTENDANCE RATE
            </div>

            <div style="
                font-size:2.4rem;
                font-weight:900;
                margin-top:5px;
            ">
                {overall_pct}%
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### Attendance Records"
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
            attendance[columns],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SETTINGS
# ============================================================

def settings_page():

    st.markdown(
        """
        <div style="margin-bottom:28px;">

            <div style="
                font-size:2rem;
                font-weight:900;
            ">
                Settings
            </div>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                View your school and account information.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### School Information"
    )

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:24px;
            margin-bottom:28px;
        ">

            <strong>School</strong>
            <br>
            {st.session_state.school_name}

            <br><br>

            <strong>School ID</strong>
            <br>
            {st.session_state.school_id}

            <br><br>

            <strong>Role</strong>
            <br>
            {st.session_state.role}

            <br><br>

            <strong>Account</strong>
            <br>
            {
                st.session_state.user_name
                or st.session_state.user_id
            }

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### Connection"
    )

    connection_status = (
        "Connected"
        if db
        else "Connection unavailable"
    )

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:22px;
        ">

            <strong>Database</strong>

            <div style="
                color:#6b7280;
                margin-top:5px;
            ">
                {connection_status}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SCHOOL APPLICATION
# ============================================================

def school_application():

    with st.sidebar:

        st.markdown(
            """
            <div style="
                padding:10px 0 18px;
                border-bottom:1px solid #dedede;
                margin-bottom:18px;
            ">

                <div style="
                    font-size:1.45rem;
                    font-weight:900;
                ">
                    EduVision
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="
                margin-bottom:18px;
            ">

                <div style="
                    color:#6b7280;
                    font-size:0.78rem;
                    font-weight:700;
                ">
                    SCHOOL
                </div>

                <div style="
                    margin-top:4px;
                    font-weight:750;
                ">
                    {st.session_state.school_name}
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.78rem;
                    font-weight:700;
                    margin-top:18px;
                ">
                    ACCOUNT
                </div>

                <div style="
                    margin-top:4px;
                    font-weight:650;
                ">
                    {
                        st.session_state.user_name
                        or st.session_state.user_id
                    }
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.82rem;
                    margin-top:3px;
                ">
                    {st.session_state.role}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
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

        old_nav_names = {
            "🏠 Dashboard":
                "Dashboard",

            "🎓 Students":
                "Students",

            "👨‍🏫 Teachers":
                "Teachers",

            "📷 Smart Attendance":
                "Smart Attendance",

            "👥 Smart Occupancy":
                "Smart Occupancy",

            "📊 Reports":
                "Reports",

            "⚙️ Settings":
                "Settings",
        }

        current_page = (
            st.session_state.get(
                "nav_page",
                "Dashboard"
            )
        )

        current_page = (
            old_nav_names.get(
                current_page,
                current_page
            )
        )

        if current_page not in pages:
            current_page = "Dashboard"

        # Keep widget state valid.
        if (
            "sidebar_nav_radio"
            in st.session_state
            and st.session_state[
                "sidebar_nav_radio"
            ] not in pages
        ):
            del st.session_state[
                "sidebar_nav_radio"
            ]

        if (
            "sidebar_nav_radio"
            not in st.session_state
        ):
            st.session_state[
                "sidebar_nav_radio"
            ] = current_page

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
            key="sidebar_logout_btn",
            use_container_width=True
        ):

            clear_login()

            st.session_state.screen = (
                "school_portal"
            )

            st.rerun()

    # ------------------------------------------------------------
    # ROUTING
    # ------------------------------------------------------------

    if page == "Dashboard":
        dashboard_page()

    elif page == "Students":
        students_page()

    elif page == "Teachers":

        if (
            st.session_state.role
            == "School Admin"
        ):
            teachers_page()

        else:
            st.error(
                "School Admin access required."
            )

    elif page == "Smart Attendance":
        attendance_page()

    elif page == "Smart Occupancy":
        occupancy_page()

    elif page == "Reports":
        reports_page()

    elif page == "Settings":

        if (
            st.session_state.role
            == "School Admin"
        ):
            settings_page()

        else:
            st.error(
                "School Admin access required."
            )


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

    st.session_state.screen = (
        "welcome"
    )

    st.rerun()

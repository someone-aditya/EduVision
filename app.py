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
# DESIGN — MAGIC UI INSPIRED
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --ev-bg: #020617;
        --ev-panel: rgba(10, 18, 38, .78);
        --ev-panel-2: rgba(15, 23, 42, .92);
        --ev-border: rgba(148, 163, 184, .16);
        --ev-purple: #8b5cf6;
        --ev-blue: #3b82f6;
        --ev-cyan: #22d3ee;
        --ev-text: #f8fafc;
        --ev-muted: #94a3b8;
    }

    html { scroll-behavior: smooth; }

    .stApp {
        color: var(--ev-text);
        background:
            radial-gradient(circle at 12% 12%, rgba(124,58,237,.20), transparent 28%),
            radial-gradient(circle at 88% 72%, rgba(6,182,212,.14), transparent 30%),
            linear-gradient(135deg, #020617, #071426 52%, #020617);
        background-attachment: fixed;
    }

    /* Animated grid */
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: .20;
        background-image:
            linear-gradient(rgba(148,163,184,.10) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148,163,184,.10) 1px, transparent 1px);
        background-size: 52px 52px;
        mask-image: linear-gradient(to bottom, black, transparent 88%);
        animation: evGrid 18s linear infinite;
    }

    @keyframes evGrid {
        from { background-position: 0 0, 0 0; }
        to { background-position: 52px 52px, 52px 52px; }
    }

    /* Aurora blobs */
    .stApp::after {
        content: "";
        position: fixed;
        width: 45vw;
        height: 45vw;
        left: 28vw;
        top: -28vw;
        border-radius: 50%;
        pointer-events: none;
        filter: blur(80px);
        opacity: .16;
        background: linear-gradient(90deg, #7c3aed, #2563eb, #06b6d4);
        animation: evAurora 10s ease-in-out infinite alternate;
    }

    @keyframes evAurora {
        from { transform: translateX(-7%) scale(.92); }
        to { transform: translateX(7%) scale(1.08); }
    }

    /* Scroll progress */
    .ev-scroll-progress {
        position: fixed;
        left: 0;
        top: 0;
        height: 3px;
        width: 100%;
        z-index: 999999;
        transform-origin: left;
        background: linear-gradient(90deg, #2563eb, #8b5cf6, #22d3ee);
        animation: evProgress linear;
        animation-timeline: scroll(root);
    }

    @keyframes evProgress {
        from { transform: scaleX(0); }
        to { transform: scaleX(1); }
    }

    .block-container {
        position: relative;
        z-index: 1;
        max-width: 1400px;
        padding-top: 1.7rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 { color: #f8fafc !important; }

    p, .stMarkdown { color: #cbd5e1; }

    /* Hero / Aurora text */
    .ev-hero {
        position: relative;
        overflow: hidden;
        padding: 56px 34px;
        margin: 4px 0 26px;
        text-align: center;
        border-radius: 28px;
        border: 1px solid rgba(139,92,246,.25);
        background: linear-gradient(145deg, rgba(15,23,42,.78), rgba(2,6,23,.72));
        box-shadow: 0 30px 80px rgba(0,0,0,.28);
        backdrop-filter: blur(18px);
    }

    .ev-kicker {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 12px;
        border-radius: 999px;
        border: 1px solid rgba(34,211,238,.25);
        background: rgba(8,145,178,.08);
        color: #a5f3fc;
        font-size: .82rem;
        font-weight: 800;
        letter-spacing: .08em;
    }

    .ev-title {
        margin: 16px 0 8px;
        font-size: clamp(3rem, 8vw, 6.2rem);
        line-height: .98;
        font-weight: 950;
        letter-spacing: -.06em;
        background: linear-gradient(90deg, #ffffff 5%, #93c5fd 30%, #c4b5fd 55%, #67e8f9 80%, #ffffff);
        background-size: 220% auto;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        animation: evAuroraText 6s linear infinite;
    }

    @keyframes evAuroraText {
        to { background-position: 220% center; }
    }

    .ev-subtitle {
        max-width: 760px;
        margin: 0 auto;
        color: #cbd5e1;
        font-size: clamp(1rem, 2vw, 1.22rem);
        line-height: 1.7;
    }

    .ev-status {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        margin-top: 18px;
        padding: 8px 13px;
        border-radius: 999px;
        background: rgba(16,185,129,.08);
        border: 1px solid rgba(52,211,153,.22);
        color: #a7f3d0;
        font-weight: 800;
        font-size: .84rem;
    }

    .ev-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #34d399;
        box-shadow: 0 0 0 0 rgba(52,211,153,.6);
        animation: evPulse 1.8s infinite;
    }

    @keyframes evPulse {
        0% { box-shadow: 0 0 0 0 rgba(52,211,153,.55); }
        70% { box-shadow: 0 0 0 10px rgba(52,211,153,0); }
        100% { box-shadow: 0 0 0 0 rgba(52,211,153,0); }
    }

    /* Magic cards */
    .ev-card, [data-testid="stMetric"] {
        position: relative;
        overflow: hidden;
        padding: 20px;
        border-radius: 22px;
        border: 1px solid var(--ev-border);
        background:
            radial-gradient(circle at 15% 0%, rgba(139,92,246,.11), transparent 35%),
            rgba(15,23,42,.76);
        box-shadow: 0 16px 45px rgba(0,0,0,.20);
        backdrop-filter: blur(16px);
        transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
    }

    .ev-card:hover, [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        border-color: rgba(96,165,250,.42);
        box-shadow: 0 22px 55px rgba(30,64,175,.15);
    }

    .ev-card h3 { margin-top: 8px; margin-bottom: 8px; }
    .ev-card p { margin-bottom: 0; color: #94a3b8; }

    .ev-icon {
        width: 44px;
        height: 44px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        font-size: 1.35rem;
        background: linear-gradient(135deg, rgba(37,99,235,.22), rgba(139,92,246,.22));
        border: 1px solid rgba(147,197,253,.16);
    }

    /* Border beam */
    .ev-beam {
        position: relative;
        overflow: hidden;
        border-radius: 24px;
        padding: 1px;
        background: rgba(148,163,184,.14);
    }

    .ev-beam::before {
        content: "";
        position: absolute;
        width: 180px;
        height: 180px;
        top: -70px;
        left: -70px;
        background: conic-gradient(from 90deg, transparent, #60a5fa, #a78bfa, #22d3ee, transparent);
        animation: evBeam 4.5s linear infinite;
        filter: blur(3px);
    }

    @keyframes evBeam {
        to { transform: rotate(360deg); }
    }

    .ev-beam-inner {
        position: relative;
        z-index: 1;
        border-radius: 23px;
        padding: 22px;
        background: rgba(2,6,23,.94);
    }

    .ev-section-title {
        margin-top: 12px;
        margin-bottom: 4px;
        font-size: 1.35rem;
        font-weight: 900;
        color: #f8fafc;
    }

    .ev-muted {
        color: #94a3b8;
        font-size: .92rem;
    }

    /* Shimmer Streamlit buttons */
    div.stButton > button {
        width: 100%;
        min-height: 46px;
        position: relative;
        overflow: hidden;
        color: white !important;
        font-weight: 850;
        border-radius: 14px;
        border: 1px solid rgba(96,165,250,.34);
        background: linear-gradient(100deg, #1d4ed8, #6d28d9 52%, #0891b2);
        box-shadow: 0 10px 28px rgba(37,99,235,.16);
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }

    div.stButton > button::before {
        content: "";
        position: absolute;
        inset: 0;
        transform: translateX(-130%);
        background: linear-gradient(105deg, transparent 35%, rgba(255,255,255,.28), transparent 65%);
        animation: evShimmer 3.4s infinite;
    }

    @keyframes evShimmer {
        0%, 55% { transform: translateX(-130%); }
        100% { transform: translateX(130%); }
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        border-color: rgba(255,255,255,.62);
        box-shadow: 0 14px 34px rgba(79,70,229,.26);
    }

    /* Inputs */
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

    div[data-baseweb="select"] span { color: black !important; }

    li[role="option"] {
        color: black !important;
        background: white !important;
    }

    /* Metrics / number ticker feel */
    [data-testid="stMetric"] {
        min-height: 130px;
    }

    [data-testid="stMetricValue"] {
        color: white;
        font-weight: 950;
        letter-spacing: -.04em;
        animation: evMetricIn .7s cubic-bezier(.2,.8,.2,1);
    }

    @keyframes evMetricIn {
        from { opacity: 0; transform: translateY(10px) scale(.96); filter: blur(4px); }
        to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        border-radius: 12px 12px 0 0;
        font-weight: 800;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background:
            radial-gradient(circle at 20% 0%, rgba(124,58,237,.16), transparent 25%),
            rgba(2,6,23,.97);
        border-right: 1px solid rgba(148,163,184,.10);
    }

    [data-testid="stSidebar"] * { color: white; }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 8px 10px;
        border-radius: 12px;
        transition: background .2s ease, transform .2s ease;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(99,102,241,.10);
        transform: translateX(3px);
    }

    label { color: white !important; }

    /* Tables */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(148,163,184,.14);
        border-radius: 18px;
        overflow: hidden;
    }

    /* Hide Streamlit chrome */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    @media (max-width: 700px) {
        .ev-hero { padding: 38px 18px; border-radius: 22px; }
        .ev-title { font-size: 3.25rem; }
    }
    </style>

    <div class="ev-scroll-progress"></div>
    """,
    unsafe_allow_html=True,
)


def hero(title="EduVision", subtitle="Smarter classrooms. Less administration. More teaching.", badge="AI • SMART CLASSROOM"):
    st.markdown(
        f"""
        <div class="ev-hero">
            <div class="ev-kicker">✦ {badge}</div>
            <div class="ev-title">{title}</div>
            <div class="ev-subtitle">{subtitle}</div>
            <div class="ev-status"><span class="ev-dot"></span> AI Systems Online • Cloud Connected</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def magic_card(icon, title, text):
    st.markdown(
        f"""
        <div class="ev-card">
            <div class="ev-icon">{icon}</div>
            <h3>{title}</h3>
            <p>{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def beam_card(icon, title, text, status="AI READY"):
    st.markdown(
        f"""
        <div class="ev-beam">
            <div class="ev-beam-inner">
                <div class="ev-icon">{icon}</div>
                <div class="ev-section-title">{title}</div>
                <div class="ev-muted">{text}</div>
                <div class="ev-status"><span class="ev-dot"></span> {status}</div>
            </div>
        </div>
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

    hero(
        "EduVision",
        "Smarter classrooms. Less administration. More teaching.",
        "AI • SMART CLASSROOM"
    )

    st.markdown(
        """
        <div style="text-align:center; max-width:760px; margin:-8px auto 28px; color:#94a3b8;">
            Attendance, classroom occupancy and school management in one intelligent platform.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1.25, 1])

    with col1:

        magic_card(
            "🏫",
            "School Portal",
            "Register a school or securely open an approved EduVision workspace."
        )

        st.write("")

        if st.button(
            "🏫 Open School Portal  →",
            use_container_width=True
        ):
            st.session_state.screen = "school_portal"
            st.rerun()

    with col2:

        magic_card(
            "👑",
            "EduVision Admin",
            "Review registration requests and control which schools can access the platform."
        )

        st.write("")

        if st.button(
            "👑 Admin Portal  →",
            use_container_width=True
        ):
            st.session_state.screen = "platform_admin_login"
            st.rerun()

    st.write("")
    st.write("")

    a, b, c = st.columns(3)

    with a:
        magic_card("📷", "Smart Attendance", "AI-assisted attendance with teacher review and attendance history.")

    with b:
        magic_card("👥", "Smart Occupancy", "Live classroom person detection powered by computer vision.")

    with c:
        magic_card("☁️", "Cloud Connected", "School, teacher, student and attendance records stay connected to Supabase.")


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

    today = datetime.now().strftime("%Y-%m-%d")
    present_today = 0
    late_today = 0

    if not attendance.empty and "attendance_date" in attendance.columns:

        today_rows = attendance[
            attendance["attendance_date"].astype(str) == today
        ]

        if "status" in today_rows.columns:
            present_today = len(today_rows[today_rows["status"] == "Present"])
            late_today = len(today_rows[today_rows["status"] == "Late"])

    hero(
        st.session_state.school_name or "EduVision",
        "Your intelligent classroom command center.",
        "SCHOOL DASHBOARD"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("🎓 Students", len(students))
    c2.metric("✅ Present Today", present_today)
    c3.metric("📋 Attendance Records", len(attendance))
    c4.metric("👤 Access", st.session_state.role)

    st.write("")
    st.markdown('<div class="ev-section-title">AI Tools</div>', unsafe_allow_html=True)
    st.markdown('<div class="ev-muted">Launch the two core EduVision classroom systems from the sidebar.</div>', unsafe_allow_html=True)
    st.write("")

    left, right = st.columns(2)

    with left:
        beam_card(
            "📷",
            "Smart Attendance",
            "Recognize registered students and reduce repetitive attendance work.",
            "FACE AI READY"
        )

    with right:
        beam_card(
            "👥",
            "Smart Occupancy",
            "Detect people in the classroom and monitor room usage in real time.",
            "VISION AI READY"
        )

    st.write("")
    st.write("")

    x, y = st.columns([1.35, 1])

    with x:
        magic_card(
            "⚡",
            "Quick Start",
            "Open Smart Attendance from the sidebar, start the camera, then review attendance history before class ends."
        )

    with y:
        magic_card(
            "🟢",
            "System Status",
            f"Cloud database connected • {present_today} present today • {late_today} late today."
        )


# ============================================================
# STUDENTS
# ============================================================

def students_page():

    hero("Students", "Manage the students registered to this school.", "🎓 SCHOOL DIRECTORY")

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

    hero("Teacher Management", "Create and manage permanent teacher accounts for this school.", "👨‍🏫 SCHOOL TEAM")

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

    hero(
        "Smart Attendance",
        "AI-assisted recognition, manual correction and attendance history in one place.",
        "📷 FACE RECOGNITION"
    )

    beam_card(
        "🤖",
        "Attendance AI",
        "Start the camera below. Registered students can be recognized while teachers keep final review control.",
        "AI CAMERA READY"
    )

    st.write("")

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

    hero(
        "Smart Occupancy",
        "Live classroom person detection for smarter room monitoring.",
        "👥 COMPUTER VISION"
    )

    beam_card(
        "👁️",
        "Live Occupancy AI",
        "Use the camera feed below to detect people and monitor whether the classroom is occupied.",
        "YOLO READY"
    )

    st.write("")

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

    hero("Reports", "A clear view of student and attendance activity.", "📊 INSIGHTS")

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

    hero("Settings", "School workspace and cloud connection information.", "⚙️ WORKSPACE")

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

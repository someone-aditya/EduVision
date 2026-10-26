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

# Ensure current application directory is in Python path for sub-modules
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EduVision — AI Smart Classroom Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURATION & CREDENTIALS
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Support Streamlit secrets as fallback if environment variables are not set
try:
    if not SUPABASE_URL and hasattr(st, "secrets") and "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = str(st.secrets["SUPABASE_URL"])
    if not SUPABASE_KEY and hasattr(st, "secrets") and "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = str(st.secrets["SUPABASE_KEY"])
except Exception:
    pass

# Main EduVision administrator credentials
EDUVISION_ADMIN_ID = os.getenv(
    "EDUVISION_ADMIN_ID",
    "12126"
)

EDUVISION_ADMIN_PASSWORD = os.getenv(
    "EDUVISION_ADMIN_PASSWORD",
    "12126"
)

# Support Streamlit secrets as fallback for admin credentials
try:
    if not os.getenv("EDUVISION_ADMIN_ID") and hasattr(st, "secrets") and "EDUVISION_ADMIN_ID" in st.secrets:
        EDUVISION_ADMIN_ID = str(st.secrets["EDUVISION_ADMIN_ID"])
    if not os.getenv("EDUVISION_ADMIN_PASSWORD") and hasattr(st, "secrets") and "EDUVISION_ADMIN_PASSWORD" in st.secrets:
        EDUVISION_ADMIN_PASSWORD = str(st.secrets["EDUVISION_ADMIN_PASSWORD"])
except Exception:
    pass


# ============================================================
# SUPABASE CLIENT SETUP (ROBUST & RESILIENT — FIXES PGRST125)
# ============================================================

def clean_supabase_url(url: str) -> str:
    """
    Sanitizes SUPABASE_URL to prevent PostgREST PGRST125 404 'Invalid path specified in request URL' errors.
    Strips trailing slashes, accidental /rest/v1 suffixes, quotes, and whitespace that occur when
    pasting URLs into deployment dashboards like Render.
    """
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
        raise RuntimeError("The 'supabase' library is not installed. Please run: pip install supabase")

    clean_url = clean_supabase_url(SUPABASE_URL)
    clean_key = clean_supabase_key(SUPABASE_KEY)

    if not clean_url:
        raise RuntimeError("SUPABASE_URL is missing from environment variables.")
    if not clean_key:
        raise RuntimeError("SUPABASE_KEY is missing from environment variables.")

    client = create_client(clean_url, clean_key)

    # Extra safety: fix any double slash in PostgREST REST URL (e.g., ...co//rest/v1)
    if hasattr(client, "rest_url") and client.rest_url:
        raw_rest = str(client.rest_url)
        clean_rest = raw_rest.replace("://", "___PROTO___").replace("//", "/").replace("___PROTO___", "://")
        while clean_rest.endswith("/"):
            clean_rest = clean_rest[:-1]
        client.rest_url = clean_rest

    return client


db = None
db_error_message = None

try:
    db = get_database()
except Exception as error:
    db_error_message = str(error)


# ============================================================
# DESIGN SYSTEM & STYLING (MAGIC UI INSPIRED)
# ============================================================

st.markdown(
    """
    <style>
    /* ------------------------------------------------------------
       DESIGN TOKENS & ROOT VARIABLES
    ------------------------------------------------------------ */
    :root {
        --ev-bg: #020617;
        --ev-bg-alt: #071426;
        --ev-panel: rgba(15, 23, 42, 0.76);
        --ev-panel-card: rgba(15, 23, 42, 0.88);
        --ev-panel-hover: rgba(30, 41, 59, 0.85);
        --ev-border: rgba(148, 163, 184, 0.16);
        --ev-border-bright: rgba(56, 189, 248, 0.42);
        --ev-blue: #3b82f6;
        --ev-purple: #8b5cf6;
        --ev-cyan: #22d3ee;
        --ev-emerald: #10b981;
        --ev-rose: #f43f5e;
        --ev-text: #f8fafc;
        --ev-muted: #94a3b8;
    }

    html {
        scroll-behavior: smooth;
    }

    /* Overall App Base */
    .stApp {
        color: var(--ev-text);
        background:
            radial-gradient(circle at 10% 12%, rgba(124, 58, 237, 0.18), transparent 30%),
            radial-gradient(circle at 90% 75%, rgba(6, 182, 212, 0.15), transparent 32%),
            radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.08), transparent 50%),
            linear-gradient(145deg, #020617 0%, #071426 50%, #030712 100%);
        background-attachment: fixed;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }

    /* ------------------------------------------------------------
       SCROLL PROGRESS BAR
    ------------------------------------------------------------ */
    .ev-scroll-progress {
        position: fixed;
        top: 0;
        left: 0;
        height: 3.5px;
        width: 0%;
        z-index: 999999;
        transform-origin: left;
        background: linear-gradient(90deg, #2563eb 0%, #8b5cf6 50%, #22d3ee 100%);
        box-shadow: 0 0 10px rgba(34, 211, 238, 0.5);
        transition: width 0.1s linear;
    }

    /* ------------------------------------------------------------
       FLICKERING GRID BACKGROUND
    ------------------------------------------------------------ */
    .ev-flicker-grid {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: 0.28;
        background-image:
            radial-gradient(circle at 50% 50%, rgba(34, 211, 238, 0.12) 1.5px, transparent 1.5px),
            linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
        background-size: 48px 48px, 48px 48px, 48px 48px;
        mask-image: radial-gradient(circle at 50% 40%, black 50%, transparent 95%);
        animation: evGridFlicker 9s ease-in-out infinite alternate;
    }

    @keyframes evGridFlicker {
        0% { opacity: 0.18; transform: scale(1); }
        35% { opacity: 0.28; }
        65% { opacity: 0.22; }
        100% { opacity: 0.32; transform: scale(1.01); }
    }

    /* ------------------------------------------------------------
       LIGHT RAYS EFFECT
    ------------------------------------------------------------ */
    .ev-light-rays {
        position: absolute;
        top: -250px;
        left: 50%;
        transform: translateX(-50%);
        width: 1000px;
        height: 600px;
        pointer-events: none;
        z-index: 0;
        background: conic-gradient(
            from 180deg at 50% 0%,
            transparent 0deg,
            rgba(37, 99, 235, 0.14) 40deg,
            transparent 85deg,
            rgba(124, 58, 237, 0.16) 130deg,
            transparent 175deg,
            rgba(6, 182, 212, 0.15) 220deg,
            transparent 270deg
        );
        filter: blur(55px);
        animation: evRayDrift 16s ease-in-out infinite alternate;
    }

    @keyframes evRayDrift {
        0% { transform: translateX(-50%) rotate(-6deg) scale(0.96); opacity: 0.7; }
        100% { transform: translateX(-50%) rotate(6deg) scale(1.06); opacity: 0.95; }
    }

    /* ------------------------------------------------------------
       METEORS (SUBTLE & REFINED)
    ------------------------------------------------------------ */
    .ev-meteor {
        position: absolute;
        width: 2px;
        height: 90px;
        background: linear-gradient(180deg, #38bdf8, rgba(139, 92, 246, 0.5), transparent);
        transform: rotate(45deg);
        pointer-events: none;
        opacity: 0;
        z-index: 1;
    }
    .ev-meteor-1 { top: 5%; left: 25%; animation: evMeteorAnim 7s ease-in-out infinite 0.5s; }
    .ev-meteor-2 { top: 12%; left: 70%; animation: evMeteorAnim 9s ease-in-out infinite 2.8s; }
    .ev-meteor-3 { top: 25%; left: 45%; animation: evMeteorAnim 8s ease-in-out infinite 5.2s; }
    .ev-meteor-4 { top: 8%; left: 88%; animation: evMeteorAnim 11s ease-in-out infinite 7.5s; }

    @keyframes evMeteorAnim {
        0% { transform: rotate(45deg) translate(0, 0); opacity: 0; }
        10% { opacity: 0.85; }
        25% { transform: rotate(45deg) translate(-280px, 280px); opacity: 0; }
        100% { transform: rotate(45deg) translate(-280px, 280px); opacity: 0; }
    }

    /* ------------------------------------------------------------
       FLOATING 3D PARTICLES / NODES
    ------------------------------------------------------------ */
    .ev-floating-node {
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
        z-index: 1;
        filter: blur(1px);
    }
    .ev-node-1 {
        width: 24px;
        height: 24px;
        top: 18%;
        left: 12%;
        background: radial-gradient(circle, rgba(56, 189, 248, 0.45) 0%, rgba(37, 99, 235, 0.1) 70%, transparent 100%);
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.35);
        animation: evFloat1 8s ease-in-out infinite alternate;
    }
    .ev-node-2 {
        width: 32px;
        height: 32px;
        top: 28%;
        right: 14%;
        background: radial-gradient(circle, rgba(168, 85, 247, 0.4) 0%, rgba(124, 58, 237, 0.1) 70%, transparent 100%);
        box-shadow: 0 0 26px rgba(168, 85, 247, 0.35);
        animation: evFloat2 10s ease-in-out infinite alternate 1.5s;
    }
    .ev-node-3 {
        width: 16px;
        height: 16px;
        top: 72%;
        left: 20%;
        background: radial-gradient(circle, rgba(34, 211, 238, 0.5) 0%, rgba(6, 182, 212, 0.1) 70%, transparent 100%);
        box-shadow: 0 0 16px rgba(34, 211, 238, 0.4);
        animation: evFloat1 9s ease-in-out infinite alternate 3s;
    }

    @keyframes evFloat1 {
        0% { transform: translateY(0px) scale(0.95); }
        100% { transform: translateY(-28px) scale(1.1); }
    }
    @keyframes evFloat2 {
        0% { transform: translateY(0px) scale(1.05); }
        100% { transform: translateY(-35px) scale(0.9); }
    }

    /* ------------------------------------------------------------
       AURORA GRADIENT TEXT
    ------------------------------------------------------------ */
    .ev-aurora-title {
    font-size: clamp(4.2rem, 10vw, 7.4rem);
    font-weight: 950;
    letter-spacing: -0.045em;
    line-height: 1;
    margin: 16px 0 14px;

    /* Solid fallback so EDUVISION can NEVER disappear */
    color: #e0f2fe !important;
    -webkit-text-fill-color: #e0f2fe !important;

    /* Strong premium glow */
    text-shadow:
        0 0 12px rgba(255,255,255,0.35),
        0 0 28px rgba(59,130,246,0.55),
        0 0 50px rgba(139,92,246,0.30);

    position: relative;
    z-index: 5;
}

    @keyframes evAuroraGrad {
        0% { background-position: 0% center; }
        100% { background-position: 260% center; }
    }

    /* Welcome EDUVISION: stronger visibility while keeping Magic UI */
    .ev-welcome-brand {
        font-size: clamp(4.4rem, 11vw, 7.8rem);
        color: #ffffff;
        -webkit-text-stroke: 1px rgba(255,255,255,0.16);
        text-shadow: 0 0 18px rgba(59,130,246,0.22);
    }

    @media (max-width: 700px) {
        .ev-welcome-brand {
            font-size: clamp(3.1rem, 16vw, 5rem);
            letter-spacing: -0.035em;
        }
    }

    /* ------------------------------------------------------------
       ANIMATED SHINY BADGE & TEXT
    ------------------------------------------------------------ */
    .ev-shiny-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 16px;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(56, 189, 248, 0.3);
        backdrop-filter: blur(14px);
        font-size: 0.82rem;
        font-weight: 850;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .ev-shiny-text {
        background: linear-gradient(110deg, #94a3b8 15%, #ffffff 45%, #38bdf8 55%, #94a3b8 85%);
        background-size: 220% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: evShineText 3.8s linear infinite;
    }

    @keyframes evShineText {
        0% { background-position: 220% 0; }
        100% { background-position: -220% 0; }
    }

    /* ------------------------------------------------------------
       KINETIC TEXT & BADGES
    ------------------------------------------------------------ */
    .ev-kinetic-sub {
        font-size: clamp(1.2rem, 2.6vw, 1.7rem);
        font-weight: 750;
        color: #f1f5f9;
        letter-spacing: -0.02em;
        margin: 14px 0 6px;
    }

    .ev-kinetic-word {
        background: linear-gradient(90deg, #38bdf8, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        position: relative;
        display: inline-block;
    }

    .ev-badge-chip {
        display: inline-block;
        padding: 4px 11px;
        margin: 0 4px;
        border-radius: 8px;
        font-size: 0.74rem;
        font-weight: 850;
        letter-spacing: 0.06em;
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #7dd3fc;
    }

    /* ------------------------------------------------------------
       WELCOME CONTAINER
    ------------------------------------------------------------ */
    .ev-welcome-hero {
        position: relative;
        overflow: hidden;
        padding: 72px 28px 56px;
        margin: 10px auto 30px;
        max-width: 980px;
        text-align: center;
        border-radius: 32px;
        border: 1px solid rgba(139, 92, 246, 0.28);
        background: linear-gradient(160deg, rgba(15, 23, 42, 0.82) 0%, rgba(2, 6, 23, 0.88) 100%);
        box-shadow: 0 35px 95px rgba(0, 0, 0, 0.45);
        backdrop-filter: blur(22px);
    }

    .ev-welcome-tagline {
        font-size: clamp(1rem, 1.8vw, 1.25rem);
        color: #cbd5e1;
        max-width: 680px;
        margin: 12px auto 26px;
        line-height: 1.65;
    }

    .ev-pulse-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #10b981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: evDotPulse 2s infinite;
        vertical-align: middle;
        margin-right: 6px;
    }

    @keyframes evDotPulse {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
        70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* ------------------------------------------------------------
       SHIMMER & INTERACTIVE BUTTONS
    ------------------------------------------------------------ */
    .ev-enter-btn-wrapper div.stButton > button {
        background: linear-gradient(135deg, #1d4ed8 0%, #6d28d9 48%, #0891b2 100%) !important;
        color: #ffffff !important;
        font-size: 1.2rem !important;
        font-weight: 850 !important;
        padding: 14px 34px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.35) !important;
        box-shadow: 0 12px 36px rgba(37, 99, 235, 0.35), 0 0 25px rgba(139, 92, 246, 0.28) !important;
        cursor: pointer !important;
        position: relative !important;
        overflow: hidden !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease !important;
    }

    .ev-enter-btn-wrapper div.stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        border-color: rgba(255, 255, 255, 0.75) !important;
        box-shadow: 0 18px 48px rgba(59, 130, 246, 0.5), 0 0 35px rgba(139, 92, 246, 0.45) !important;
    }

    .ev-enter-btn-wrapper div.stButton > button::before {
        content: "";
        position: absolute;
        top: 0;
        left: -120%;
        width: 60%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
        transform: skewX(-22deg);
        animation: evBtnShimmer 3.2s infinite;
    }

    @keyframes evBtnShimmer {
        0%, 45% { left: -120%; }
        100% { left: 220%; }
    }

    /* Standard App Buttons */
    div.stButton > button {
        width: 100%;
        min-height: 44px;
        position: relative;
        overflow: hidden;
        color: white !important;
        font-weight: 800;
        border-radius: 13px;
        border: 1px solid rgba(96, 165, 250, 0.35);
        background: linear-gradient(110deg, #1e40af 0%, #6b21a8 52%, #0e7490 100%);
        box-shadow: 0 8px 24px rgba(37, 99, 235, 0.16);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.65);
        box-shadow: 0 12px 30px rgba(99, 102, 241, 0.3);
    }

    /* ------------------------------------------------------------
       PORTAL ENTRANCE TRANSITION
    ------------------------------------------------------------ */
    .ev-portal-container {
        animation: evPortalSlideIn 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes evPortalSlideIn {
        0% { opacity: 0; transform: translateY(22px) scale(0.98); filter: blur(6px); }
        100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    }

    .ev-light-sweep-overlay {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 99999;
        background: linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.22) 45%, rgba(139, 92, 246, 0.3) 50%, rgba(34, 211, 238, 0.22) 55%, transparent 100%);
        animation: evLightSweep 0.8s ease-out forwards;
    }

    @keyframes evLightSweep {
        0% { transform: translateX(-100%); opacity: 0; }
        35% { opacity: 1; }
        100% { transform: translateX(100%); opacity: 0; }
    }

    /* ------------------------------------------------------------
       BENTO GRID CARDS
    ------------------------------------------------------------ */
    .ev-bento-grid {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 20px;
        margin: 28px 0;
    }

    .ev-bento-col-8 { grid-column: span 8; }
    .ev-bento-col-4 { grid-column: span 4; }
    .ev-bento-col-6 { grid-column: span 6; }
    .ev-bento-col-12 { grid-column: span 12; }

    @media (max-width: 900px) {
        .ev-bento-col-8, .ev-bento-col-4, .ev-bento-col-6 {
            grid-column: span 12;
        }
    }

    /* ------------------------------------------------------------
       MAGIC CARDS & HOVER SPOTLIGHT
    ------------------------------------------------------------ */
    .ev-magic-card {
        position: relative;
        border-radius: 22px;
        padding: 24px;
        background: radial-gradient(circle at 12% 10%, rgba(99, 102, 241, 0.1), transparent 42%), rgba(15, 23, 42, 0.75);
        border: 1px solid var(--ev-border);
        box-shadow: 0 16px 45px rgba(0, 0, 0, 0.26);
        backdrop-filter: blur(18px);
        transition: transform 0.26s ease, border-color 0.26s ease, box-shadow 0.26s ease;
        overflow: hidden;
        height: 100%;
    }

    .ev-magic-card:hover {
        transform: translateY(-4px);
        border-color: rgba(96, 165, 250, 0.45);
        box-shadow: 0 22px 55px rgba(37, 99, 235, 0.22);
    }

    .ev-card-icon {
        width: 48px;
        height: 48px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        font-size: 1.4rem;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(139, 92, 246, 0.25));
        border: 1px solid rgba(147, 197, 253, 0.2);
        margin-bottom: 14px;
    }

    .ev-card-title {
        font-size: 1.25rem;
        font-weight: 850;
        color: #f8fafc;
        margin-bottom: 8px;
    }

    .ev-card-desc {
        color: #94a3b8;
        font-size: 0.94rem;
        line-height: 1.6;
        margin: 0;
    }

    /* ------------------------------------------------------------
       BORDER BEAM EFFECT
    ------------------------------------------------------------ */
    .ev-border-beam-box {
        position: relative;
        border-radius: 24px;
        padding: 1.5px;
        overflow: hidden;
        background: rgba(148, 163, 184, 0.14);
    }

    .ev-border-beam-box::before {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        top: -60px;
        left: -60px;
        background: conic-gradient(from 0deg, transparent 0%, #38bdf8 25%, #818cf8 50%, #c084fc 75%, transparent 100%);
        animation: evBeamSpin 4.5s linear infinite;
        filter: blur(4px);
    }

    @keyframes evBeamSpin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .ev-border-beam-inner {
        position: relative;
        z-index: 1;
        border-radius: 22.5px;
        background: rgba(10, 18, 38, 0.94);
        backdrop-filter: blur(24px);
        padding: 24px;
    }

    /* ------------------------------------------------------------
       NEON GRADIENT CARDS (HERO AI SYSTEM CARDS)
    ------------------------------------------------------------ */
    .ev-neon-card-blue {
        position: relative;
        border-radius: 24px;
        padding: 26px;
        background: linear-gradient(150deg, rgba(15, 23, 42, 0.9) 0%, rgba(7, 20, 38, 0.85) 100%);
        border: 1px solid rgba(56, 189, 248, 0.45);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35), inset 0 0 25px rgba(56, 189, 248, 0.12), 0 0 28px rgba(56, 189, 248, 0.22);
        backdrop-filter: blur(20px);
        transition: all 0.28s ease;
    }

    .ev-neon-card-blue:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.4), inset 0 0 35px rgba(56, 189, 248, 0.2), 0 0 42px rgba(56, 189, 248, 0.36);
        border-color: rgba(56, 189, 248, 0.75);
    }

    .ev-neon-card-purple {
        position: relative;
        border-radius: 24px;
        padding: 26px;
        background: linear-gradient(150deg, rgba(15, 23, 42, 0.9) 0%, rgba(20, 12, 40, 0.85) 100%);
        border: 1px solid rgba(168, 85, 247, 0.45);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35), inset 0 0 25px rgba(168, 85, 247, 0.12), 0 0 28px rgba(168, 85, 247, 0.22);
        backdrop-filter: blur(20px);
        transition: all 0.28s ease;
    }

    .ev-neon-card-purple:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.4), inset 0 0 35px rgba(168, 85, 247, 0.2), 0 0 42px rgba(168, 85, 247, 0.36);
        border-color: rgba(168, 85, 247, 0.75);
    }

    /* ------------------------------------------------------------
       NUMBER TICKER / METRIC CARDS
    ------------------------------------------------------------ */
    .ev-metric-card {
        border-radius: 20px;
        padding: 22px;
        background: rgba(15, 23, 42, 0.78);
        border: 1px solid var(--ev-border);
        box-shadow: 0 14px 38px rgba(0, 0, 0, 0.22);
        backdrop-filter: blur(16px);
        transition: transform 0.22s ease, border-color 0.22s ease;
    }

    .ev-metric-card:hover {
        transform: translateY(-3px);
        border-color: var(--ev-border-bright);
    }

    .ev-number-ticker {
        animation: evTickerRoll 0.65s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes evTickerRoll {
        0% { opacity: 0; transform: translateY(12px) scale(0.94); filter: blur(4px); }
        100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    }

    [data-testid="stMetric"] {
        border-radius: 20px !important;
        padding: 18px 20px !important;
        background: rgba(15, 23, 42, 0.78) !important;
        border: 1px solid var(--ev-border) !important;
        box-shadow: 0 14px 38px rgba(0, 0, 0, 0.22) !important;
        backdrop-filter: blur(16px) !important;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 950 !important;
        font-size: 2rem !important;
        letter-spacing: -0.04em !important;
    }

    /* ------------------------------------------------------------
       CONFETTI CELEBRATION (LIGHTWEIGHT CSS)
    ------------------------------------------------------------ */
    .ev-confetti-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 999999;
        overflow: hidden;
    }

    .ev-confetti-piece {
        position: absolute;
        width: 9px;
        height: 14px;
        opacity: 0.9;
        animation: evConfettiFall 2.4s ease-out forwards;
    }

    @keyframes evConfettiFall {
        0% { transform: translateY(-40px) rotate(0deg); opacity: 1; }
        100% { transform: translateY(105vh) rotate(720deg); opacity: 0; }
    }

    /* ------------------------------------------------------------
       INPUT CONTROLS & READABILITY ENHANCEMENTS
    ------------------------------------------------------------ */
    div[data-baseweb="input"] {
        background: rgba(15, 23, 42, 0.88) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 12px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.3) !important;
    }

    div[data-baseweb="input"] input {
        color: #f8fafc !important;
        -webkit-text-fill-color: #f8fafc !important;
        background: transparent !important;
        font-size: 0.98rem !important;
        padding: 10px 14px !important;
    }

    input::placeholder {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
    }

    div[data-baseweb="select"] > div {
        background: rgba(15, 23, 42, 0.88) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="select"] span {
        color: #f8fafc !important;
    }

    li[role="option"] {
        color: #f8fafc !important;
        background: #0f172a !important;
    }

    li[role="option"]:hover {
        background: #1e293b !important;
    }

    label {
        color: #e2e8f0 !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }

    /* ------------------------------------------------------------
       TABS & EXPANDERS
    ------------------------------------------------------------ */
    button[data-baseweb="tab"] {
        border-radius: 12px 12px 0 0;
        font-weight: 800;
        color: #94a3b8 !important;
        transition: color 0.2s ease;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom-color: #38bdf8 !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid var(--ev-border) !important;
        border-radius: 16px !important;
        background: rgba(15, 23, 42, 0.72) !important;
        backdrop-filter: blur(14px) !important;
    }

    /* ------------------------------------------------------------
       SIDEBAR PILL NAVIGATION
    ------------------------------------------------------------ */
    [data-testid="stSidebar"] {
        background:
            radial-gradient(circle at 10% 0%, rgba(124, 58, 237, 0.16), transparent 28%),
            rgba(2, 6, 23, 0.96) !important;
        border-right: 1px solid rgba(148, 163, 184, 0.12) !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 10px 14px;
        margin-bottom: 5px;
        border-radius: 12px;
        background: transparent;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(56, 189, 248, 0.1);
        border-color: rgba(56, 189, 248, 0.2);
        transform: translateX(4px);
    }

    [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(37, 99, 235, 0.25), rgba(139, 92, 246, 0.2));
        border: 1px solid rgba(96, 165, 250, 0.4);
    }

    /* ------------------------------------------------------------
       DATAFRAME / TABLE STYLING
    ------------------------------------------------------------ */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(148, 163, 184, 0.18) !important;
        border-radius: 18px !important;
        overflow: hidden !important;
        background: rgba(15, 23, 42, 0.65) !important;
    }

    /* ------------------------------------------------------------
       CLEAN STREAMLIT CHROME
    ------------------------------------------------------------ */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }

    /* ------------------------------------------------------------
       ACCESSIBILITY (REDUCED MOTION)
    ------------------------------------------------------------ */
    @media (prefers-reduced-motion: reduce) {
        *, ::before, ::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>

    <div id="ev-scroll-bar" class="ev-scroll-progress"></div>
    <script>
    (function() {
        function updateScrollBar() {
            var bar = document.getElementById('ev-scroll-bar');
            if (!bar) return;
            var scrollTop = window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
            var docHeight = Math.max(
                document.body.scrollHeight, document.documentElement.scrollHeight,
                document.body.offsetHeight, document.documentElement.offsetHeight,
                document.body.clientHeight, document.documentElement.clientHeight
            ) - window.innerHeight;
            var pct = docHeight > 0 ? Math.min(100, (scrollTop / docHeight) * 100) : 0;
            bar.style.width = pct + '%';
        }
        window.addEventListener('scroll', updateScrollBar, { passive: true });
        updateScrollBar();
    })();
    </script>
    <div class="ev-flicker-grid"></div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# COMPONENT HELPERS (MAGIC UI VISUALS)
# ============================================================

def render_confetti():
    """Renders a short, subtle celebration confetti burst upon success."""
    st.markdown(
        """
        <div class="ev-confetti-container">
            <div class="ev-confetti-piece" style="left:12%; background:#38bdf8; animation-delay:0.1s;"></div>
            <div class="ev-confetti-piece" style="left:26%; background:#a855f7; animation-delay:0.3s;"></div>
            <div class="ev-confetti-piece" style="left:42%; background:#34d399; animation-delay:0.15s;"></div>
            <div class="ev-confetti-piece" style="left:58%; background:#f43f5e; animation-delay:0.4s;"></div>
            <div class="ev-confetti-piece" style="left:74%; background:#fbbf24; animation-delay:0.2s;"></div>
            <div class="ev-confetti-piece" style="left:88%; background:#22d3ee; animation-delay:0.35s;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_circular_progress(percentage, title="Attendance Today", size=180, stroke_width=12):
    """
    Renders an Animated Circular Progress Bar (Magic UI inspired)
    Calculated purely from real student data.
    """
    val = max(0.0, min(100.0, float(percentage)))
    radius = (size - stroke_width) / 2
    circumference = 2 * 3.14159265 * radius
    stroke_dashoffset = circumference - (val / 100.0) * circumference

    html = f"""
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:18px;">
        <div style="position:relative; width:{size}px; height:{size}px;">
            <svg width="{size}" height="{size}" style="transform: rotate(-90deg);">
                <defs>
                    <linearGradient id="evCircleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#3b82f6" />
                        <stop offset="50%" stop-color="#8b5cf6" />
                        <stop offset="100%" stop-color="#22d3ee" />
                    </linearGradient>
                    <filter id="evCircleGlow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3.5" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                </defs>
                <circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" stroke="rgba(148, 163, 184, 0.16)" stroke-width="{stroke_width}" />
                <circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" stroke="url(#evCircleGrad)" stroke-width="{stroke_width}"
                    stroke-dasharray="{circumference}" stroke-dashoffset="{stroke_dashoffset}"
                    stroke-linecap="round" filter="url(#evCircleGlow)"
                    style="transition: stroke-dashoffset 1.4s cubic-bezier(0.2, 0.8, 0.2, 1);" />
            </svg>
            <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; pointer-events:none;">
                <span style="font-size:2.2rem; font-weight:950; color:#f8fafc; letter-spacing:-0.04em; text-shadow:0 0 16px rgba(56,189,248,0.45);">{val:.1f}%</span>
                <span style="font-size:0.75rem; font-weight:800; color:#94a3b8; text-transform:uppercase; letter-spacing:0.08em; margin-top:2px;">Rate</span>
            </div>
        </div>
        <div style="margin-top:14px; font-weight:850; font-size:1.05rem; color:#f8fafc; text-align:center;">{title}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_metric_card(icon, label, value, subtext=None, is_number=True):
    """Renders a metric card with Number Ticker animation."""
    sub_html = f'<div style="font-size:0.8rem; color:#94a3b8; margin-top:5px;">{subtext}</div>' if subtext else ""
    anim_class = "ev-number-ticker" if is_number else ""
    html = f"""
    <div class="ev-metric-card">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
            <span style="font-size:0.82rem; font-weight:800; color:#94a3b8; text-transform:uppercase; letter-spacing:0.06em;">{label}</span>
            <span style="font-size:1.25rem;">{icon}</span>
        </div>
        <div class="{anim_class}" style="font-size:2.2rem; font-weight:950; color:#f8fafc; letter-spacing:-0.03em;">{value}</div>
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def hero(title="EduVision", subtitle="Smarter classrooms. Less administration. More teaching.", badge="AI • SMART CLASSROOM"):
    """Futuristic SaaS Hero Header."""
    st.markdown(
        f"""
        <div style="position:relative; overflow:hidden; padding:40px 24px 34px; margin:4px 0 24px; text-align:center; border-radius:26px; border:1px solid rgba(139,92,246,0.25); background:linear-gradient(155deg, rgba(15,23,42,0.85) 0%, rgba(2,6,23,0.88) 100%); box-shadow:0 24px 60px rgba(0,0,0,0.3); backdrop-filter:blur(18px);">
            <div class="ev-shiny-badge"><span class="ev-shiny-text">✦ {badge}</span></div>
            <div class="ev-aurora-title" style="font-size:clamp(2.4rem, 5.5vw, 4.2rem); margin:12px 0 6px;">{title}</div>
            <div style="max-width:720px; margin:0 auto; color:#cbd5e1; font-size:clamp(0.95rem, 1.8vw, 1.15rem); line-height:1.65;">{subtitle}</div>
            <div style="display:inline-flex; align-items:center; gap:8px; margin-top:16px; padding:6px 14px; border-radius:999px; background:rgba(16,185,129,0.08); border:1px solid rgba(52,211,153,0.24); color:#a7f3d0; font-weight:800; font-size:0.82rem;">
                <span class="ev-pulse-dot"></span> AI Systems Online • Cloud Connected
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def magic_card(icon, title, text):
    """Renders a Magic Card with hover elevation and spotlight."""
    st.markdown(
        f"""
        <div class="ev-magic-card">
            <div class="ev-card-icon">{icon}</div>
            <div class="ev-card-title">{title}</div>
            <p class="ev-card-desc">{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def beam_card(icon, title, text, status="AI READY"):
    """Renders a high-tech Border Beam Card."""
    st.markdown(
        f"""
        <div class="ev-border-beam-box">
            <div class="ev-border-beam-inner">
                <div class="ev-card-icon">{icon}</div>
                <div class="ev-card-title">{title}</div>
                <p class="ev-card-desc">{text}</p>
                <div style="display:inline-flex; align-items:center; gap:8px; margin-top:16px; padding:6px 12px; border-radius:999px; background:rgba(16,185,129,0.08); border:1px solid rgba(52,211,153,0.22); color:#a7f3d0; font-weight:800; font-size:0.8rem;">
                    <span class="ev-pulse-dot"></span> {status}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SECURITY & AUTHENTICATION UTILITIES
# ============================================================

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()


def generate_school_id():
    return "SCH-" + secrets.token_hex(3).upper()


# ============================================================
# SESSION STATE MANAGEMENT
# ============================================================

DEFAULT_SESSION = {
    "screen": "welcome",
    "logged_in": False,
    "role": None,
    "school_id": None,
    "school_name": None,
    "user_id": None,
    "user_name": None,
    "nav_page": "🏠 Dashboard",
    "transition_trigger": False,
    "school_reg_success": None,
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
    st.session_state.nav_page = "🏠 Dashboard"


def go_portal():
    clear_login()
    st.session_state.screen = "portal"
    st.rerun()


def go_welcome():
    clear_login()
    st.session_state.screen = "welcome"
    st.rerun()


# ============================================================
# DATABASE ACCESS HELPERS (PRESERVED SUPABASE LOGIC)
# ============================================================

def get_school(school_id):
    if not db or not school_id:
        return None
    try:
        response = (
            db.table("schools")
            .select("*")
            .eq("school_id", school_id.strip())
            .execute()
        )
        if response.data:
            return response.data[0]
    except Exception as error:
        print(f"get_school error for {school_id}: {error}")
    return None


def get_school_by_admin(school_id, admin_id):
    if not db or not school_id or not admin_id:
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
        print(f"get_school_by_admin error: {error}")
    return None


def get_teacher(school_id, teacher_id):
    if not db or not school_id or not teacher_id:
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
        print(f"get_teacher error: {error}")
    return None


def load_students():
    if not db or not st.session_state.school_id:
        return pd.DataFrame()
    try:
        response = (
            db.table("students")
            .select("*")
            .eq("school_id", st.session_state.school_id)
            .order("name")
            .execute()
        )
        if response.data:
            return pd.DataFrame(response.data)
    except Exception:
        try:
            response = (
                db.table("students")
                .select("*")
                .eq("school_id", st.session_state.school_id)
                .execute()
            )
            if response.data:
                return pd.DataFrame(response.data)
        except Exception as error:
            st.error(f"Could not load students: {error}")
    return pd.DataFrame()


def load_attendance():
    if not db or not st.session_state.school_id:
        return pd.DataFrame()
    try:
        response = (
            db.table("attendance")
            .select("*")
            .eq("school_id", st.session_state.school_id)
            .order("created_at", desc=True)
            .execute()
        )
        if response.data:
            return pd.DataFrame(response.data)
    except Exception:
        try:
            response = (
                db.table("attendance")
                .select("*")
                .eq("school_id", st.session_state.school_id)
                .order("attendance_date", desc=True)
                .execute()
            )
            if response.data:
                return pd.DataFrame(response.data)
        except Exception:
            try:
                response = (
                    db.table("attendance")
                    .select("*")
                    .eq("school_id", st.session_state.school_id)
                    .execute()
                )
                if response.data:
                    return pd.DataFrame(response.data)
            except Exception as error:
                st.error(f"Could not load attendance: {error}")
    return pd.DataFrame()


# ============================================================
# SCREEN 1 — NEW FIRST SCREEN: WELCOME TO EDUVISION
# ============================================================

def welcome_screen():
    _welcome_html = (
'<div class="ev-welcome-hero">'
'\n<!-- Light Rays -->'
'\n<div class="ev-light-rays"></div>'
'\n<!-- Meteors -->'
'\n<div class="ev-meteor ev-meteor-1"></div>'
'\n<div class="ev-meteor ev-meteor-2"></div>'
'\n<div class="ev-meteor ev-meteor-3"></div>'
'\n<div class="ev-meteor ev-meteor-4"></div>'
'\n<!-- Floating 3D Nodes -->'
'\n<div class="ev-floating-node ev-node-1"></div>'
'\n<div class="ev-floating-node ev-node-2"></div>'
'\n<div class="ev-floating-node ev-node-3"></div>'
'\n<div style="position:relative; z-index:2;">'
'\n<div class="ev-shiny-badge"><span class="ev-shiny-text">✦ AI-POWERED EDUCATION</span></div>'
'\n<div style="color:#94a3b8; font-weight:800; font-size:1.1rem; letter-spacing:0.04em; margin-top:20px;">Welcome to</div>'
'\n<h1 class="ev-aurora-title ev-welcome-brand">EDUVISION</h1>'
'\n<div class="ev-kinetic-sub">The Future of <span class="ev-kinetic-word">Smart Classrooms</span></div>'
'\n<p class="ev-welcome-tagline">Smarter classrooms. Less administration. More teaching.</p>'
'\n<div style="margin: 0 auto 30px;">'
'\n<span class="ev-badge-chip">SMARTER</span>'
'\n<span class="ev-badge-chip">FASTER</span>'
'\n<span class="ev-badge-chip">INTELLIGENT</span>'
'\n</div>'
'\n</div>'
'\n</div>'
    )
    st.markdown(_welcome_html, unsafe_allow_html=True)

    # Centered CTA Button with Shimmer & Interactive Hover
    col_l, col_btn, col_r = st.columns([1, 1.25, 1])
    with col_btn:
        st.markdown('<div class="ev-enter-btn-wrapper">', unsafe_allow_html=True)
        if st.button("Enter EduVision  →", key="enter_eduvision_btn", use_container_width=True):
            st.session_state.screen = "portal"
            st.session_state.transition_trigger = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Status Pill
    cloud_status_text = "Cloud Connected" if db else "Cloud: Ready for Deployment"
    _pill_html = (
        '<div style="text-align:center; margin-top:22px;">'
        '<div style="display:inline-flex; align-items:center; gap:8px; padding:7px 16px;'
        ' border-radius:999px; background:rgba(15,23,42,0.8);'
        ' border:1px solid rgba(52,211,153,0.25); color:#a7f3d0; font-size:0.82rem; font-weight:800;">'
        f'<span class="ev-pulse-dot"></span> AI Systems Online &bull; {cloud_status_text}'
        '</div></div>'
    )
    st.markdown(_pill_html, unsafe_allow_html=True)


# ============================================================
# SCREEN 2 — EDUVISION PORTAL (BENTO GRID & ACTIONS)
# ============================================================

def portal_screen():
    # Trigger smooth light sweep overlay on entrance if transitioning
    if st.session_state.get("transition_trigger"):
        st.markdown('<div class="ev-light-sweep-overlay"></div>', unsafe_allow_html=True)
        st.session_state.transition_trigger = False

    st.markdown('<div class="ev-portal-container">', unsafe_allow_html=True)

    # Top Brand Bar
    c_brand, c_nav = st.columns([2, 1])
    with c_brand:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-size:1.8rem;">🎓</span>
                <div>
                    <div style="font-size:1.4rem; font-weight:950; letter-spacing:-0.03em; color:#f8fafc;">EduVision</div>
                    <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">AI Classroom SaaS</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_nav:
        st.markdown('<div style="text-align:right;">', unsafe_allow_html=True)
        if st.button("✦ Back to Welcome", key="back_to_welcome_btn"):
            go_welcome()
        st.markdown('</div>', unsafe_allow_html=True)

    # Hero Headline
    hero(
        "AI-Powered Smart Classroom Management",
        "Attendance, classroom intelligence and school management — connected in one unified platform.",
        "EDUVISION PORTAL"
    )

    # Primary & Secondary Action Cards
    c_primary, c_secondary = st.columns([1.6, 1])

    with c_primary:
        st.markdown(
            """
            <div class="ev-neon-card-blue">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <div class="ev-shiny-badge"><span class="ev-shiny-text">★ PRIMARY PORTAL</span></div>
                    <span style="font-size:1.8rem;">🏫</span>
                </div>
                <div style="font-size:1.5rem; font-weight:900; color:#f8fafc; margin-bottom:6px;">School Portal</div>
                <p style="color:#94a3b8; font-size:0.95rem; line-height:1.6; margin-bottom:20px;">
                    Access your campus command center, register a new institution, or log in as an administrator or teacher.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("🏫 Open School Portal  →", key="open_school_portal_btn", use_container_width=True):
            st.session_state.screen = "school_portal"
            st.rerun()

    with c_secondary:
        st.markdown(
            """
            <div class="ev-magic-card">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <div style="font-size:0.75rem; font-weight:800; color:#cbd5e1; text-transform:uppercase; letter-spacing:0.06em;">ADMINISTRATION</div>
                    <span style="font-size:1.8rem;">👑</span>
                </div>
                <div style="font-size:1.35rem; font-weight:900; color:#f8fafc; margin-bottom:6px;">EduVision Admin</div>
                <p style="color:#94a3b8; font-size:0.9rem; line-height:1.6; margin-bottom:20px;">
                    Review campus registration requests, approve new schools, and govern platform permissions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("👑 EduVision Admin  →", key="open_admin_portal_btn", use_container_width=True):
            st.session_state.screen = "platform_admin_login"
            st.rerun()

    st.write("")
    st.write("")

    # ------------------------------------------------------------
    # BENTO GRID SECTION
    # ------------------------------------------------------------
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin:24px 0 16px;">
            <div class="ev-shiny-badge"><span class="ev-shiny-text">✦ PLATFORM CAPABILITIES</span></div>
            <div style="font-size:1.25rem; font-weight:900; color:#f8fafc;">Bento Architecture</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2 = st.columns([1.2, 1])

    with b1:
        beam_card(
            "📷",
            "Smart Attendance",
            "AI-assisted face recognition attendance powered by OpenCV LBPH. Recognize registered students, minimize roll-call overhead, and ensure auditable records.",
            "FACE AI ENGINE"
        )

    with b2:
        beam_card(
            "👥",
            "Smart Occupancy",
            "Real-time classroom person detection with YOLO11 computer vision. Monitor headcounts, occupancy limits, and room utilization in live video.",
            "YOLO11 VISION"
        )

    st.write("")

    b3, b4, b5 = st.columns(3)

    with b3:
        magic_card(
            "☁️",
            "Cloud Connected",
            "Institutional data, rosters, credentials, and daily attendance logs stay synchronized in real time with the Supabase cloud database."
        )

    with b4:
        magic_card(
            "🏫",
            "School Management",
            "Role-based access separating School Administrators and Teachers. Add students, govern staff accounts, and track classroom performance."
        )

    with b5:
        magic_card(
            "✨",
            "AI System Tools",
            "Low-latency WebRTC browser video processing with privacy-conscious client/server pipelines and instant facial recognition inference."
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# SCREEN 3 — SCHOOL PORTAL (REGISTER & OPEN EXISTING)
# ============================================================

def school_portal():
    c_title, c_back = st.columns([3, 1])
    with c_title:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <span style="font-size:2rem;">🏫</span>
                <div>
                    <h2 style="margin:0; font-weight:950; color:#f8fafc;">School Portal</h2>
                    <div style="font-size:0.9rem; color:#94a3b8;">Register a new school or open an approved campus workspace.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_back:
        st.markdown('<div style="text-align:right;">', unsafe_allow_html=True)
        if st.button("← Back to Portal", key="portal_back_btn"):
            go_portal()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    register_tab, open_tab = st.tabs([
        "📝 Register School",
        "🏫 Open Existing School",
    ])

    # ------------------------------------------------------------
    # TAB 1: REGISTER SCHOOL
    # ------------------------------------------------------------
    with register_tab:
        st.markdown(
            """
            <div class="ev-magic-card" style="margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <div class="ev-shiny-badge"><span class="ev-shiny-text">CAMPUS ONBOARDING</span></div>
                </div>
                <div style="font-size:1.2rem; font-weight:850; color:#f8fafc; margin-bottom:6px;">Register Your Institution</div>
                <p style="color:#94a3b8; font-size:0.92rem; margin:0;">
                    Complete the form below to create your school workspace. Upon submission, an EduVision platform administrator will review and approve your registration.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_reg1, col_reg2 = st.columns(2)
        with col_reg1:
            school_name = st.text_input("School Name", placeholder="e.g. Oakridge International School", key="reg_school_name")
            admin_id = st.text_input("School Admin ID", placeholder="e.g. admin_oakridge", key="reg_admin_id")

        with col_reg2:
            admin_password = st.text_input("Admin Password", type="password", placeholder="At least 6 characters", key="reg_admin_pwd")
            confirm_password = st.text_input("Confirm Admin Password", type="password", placeholder="Repeat password", key="reg_admin_confirm")

        st.write("")
        if st.button("✨ Submit School Registration", key="submit_reg_btn", use_container_width=True):
            school_name = school_name.strip()
            admin_id = admin_id.strip()

            if not school_name:
                st.error("Please enter your school name.")
            elif not admin_id:
                st.error("Please enter a School Admin ID.")
            elif len(admin_password) < 6:
                st.error("Password must be at least 6 characters long.")
            elif admin_password != confirm_password:
                st.error("Passwords do not match.")
            elif not db:
                st.error("Database connection is currently unavailable. Please verify environment credentials.")
            else:
                school_id = generate_school_id()
                try:
                    db.table("schools").insert({
                        "school_id": school_id,
                        "school_name": school_name,
                        "admin_id": admin_id,
                        "admin_password_hash": hash_password(admin_password),
                        "approval_status": "pending",
                    }).execute()

                    # Trigger subtle celebratory confetti
                    render_confetti()

                    st.success("🎉 School registration submitted successfully!")
                    st.markdown(
                        f"""
                        <div class="ev-border-beam-box" style="margin:16px 0;">
                            <div class="ev-border-beam-inner">
                                <div style="font-size:0.85rem; font-weight:800; color:#38bdf8; text-transform:uppercase;">IMPORTANT — SAVE YOUR CREDENTIALS</div>
                                <div style="font-size:1.6rem; font-weight:950; color:#ffffff; margin:6px 0;">School ID: <span style="color:#22d3ee;">{school_id}</span></div>
                                <div style="font-size:0.92rem; color:#cbd5e1;">Admin ID: <strong>{admin_id}</strong></div>
                                <div style="font-size:0.85rem; color:#f59e0b; margin-top:8px;">⚠️ Please save this School ID. You will need it to log in once an EduVision Admin approves your campus.</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as error:
                    st.error(f"School registration failed: {error}")

    # ------------------------------------------------------------
    # TAB 2: OPEN SCHOOL
    # ------------------------------------------------------------
    with open_tab:
        st.markdown(
            '<div class="ev-magic-card" style="margin-bottom:20px;">'
            '<div style="font-size:1.2rem; font-weight:850; color:#f8fafc; margin-bottom:6px;">Access Approved School</div>'
            '<p style="color:#94a3b8; font-size:0.92rem; margin:0;">Search or select your school by name to access its authentication screen.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Load approved schools from Supabase for the name-based selector
        approved_schools = []  # list of dicts: {school_name, school_id}
        if db:
            try:
                resp = db.table("schools").select("school_id, school_name").eq("approval_status", "approved").execute()
                approved_schools = resp.data if resp.data else []
            except Exception as _e:
                st.error(f"Could not load school list: {_e}")

        if not approved_schools:
            st.info("No approved schools are currently available.")
        else:
            # Build name→id mapping (names displayed to user; id used internally)
            school_name_to_id = {s["school_name"]: s["school_id"] for s in approved_schools}
            school_names = sorted(school_name_to_id.keys())

            selected_name = st.selectbox(
                "School",
                options=school_names,
                index=0,
                placeholder="Search or select your school...",
                key="open_school_name_select",
            )

            st.write("")
            if st.button("🏫 Open School Workspace  →", key="open_school_action_btn", use_container_width=True):
                selected_id = school_name_to_id.get(selected_name, "").strip()
                if not selected_id:
                    st.error("Please select a school.")
                elif not db:
                    st.error("Database connection unavailable. Please check Supabase configuration.")
                else:
                    school = get_school(selected_id)
                    if not school:
                        st.error("School record not found. Please contact EduVision Admin.")
                    else:
                        st.session_state.school_id = school["school_id"]
                        st.session_state.school_name = school["school_name"]
                        st.session_state.screen = "school_login"
                        st.rerun()


# ============================================================
# SCREEN 4 — SCHOOL LOGIN (CLEAN, DISTRACTION-FREE)
# ============================================================

def school_login():
    school_id = st.session_state.school_id
    school = get_school(school_id)

    if not school:
        st.error("School workspace not found.")
        if st.button("← Return to School Portal"):
            st.session_state.screen = "school_portal"
            st.rerun()
        return

    # Clean Header
    c_title, c_change = st.columns([3, 1])
    with c_title:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <span style="font-size:2rem;">🏫</span>
                <div>
                    <h2 style="margin:0; font-weight:950; color:#f8fafc;">{school['school_name']}</h2>
                    <div style="font-size:0.88rem; color:#38bdf8; font-weight:800;">School ID: {school_id}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_change:
        st.markdown('<div style="text-align:right;">', unsafe_allow_html=True)
        if st.button("← Change School", key="change_school_btn"):
            clear_login()
            st.session_state.screen = "school_portal"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    admin_tab, teacher_tab = st.tabs([
        "👨‍💼 School Admin Login",
        "👨‍🏫 Teacher Login",
    ])

    # ------------------------------------------------------------
    # TAB 1: SCHOOL ADMIN LOGIN
    # ------------------------------------------------------------
    with admin_tab:
        col_c1, col_center, col_c2 = st.columns([1, 2, 1])
        with col_center:
            st.markdown(
                """
                <div class="ev-magic-card" style="margin-bottom:20px; text-align:center;">
                    <div style="font-size:1.8rem; margin-bottom:6px;">👨‍💼</div>
                    <div style="font-size:1.25rem; font-weight:900; color:#f8fafc;">Administrator Access</div>
                    <div style="font-size:0.88rem; color:#94a3b8;">Full governance over students, teachers, and attendance.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            admin_id = st.text_input("Admin ID", key="school_admin_id_input")
            password = st.text_input("Admin Password", type="password", key="school_admin_pwd_input")

            st.write("")
            if st.button("🔐 Login as Admin", key="login_admin_action", use_container_width=True):
                admin_id_clean = admin_id.strip()
                school_account = get_school_by_admin(school_id, admin_id_clean)

                if (
                    school_account
                    and hash_password(password) == school_account.get("admin_password_hash")
                ):
                    st.session_state.logged_in = True
                    st.session_state.role = "School Admin"
                    st.session_state.user_id = admin_id_clean
                    st.session_state.user_name = f"{school['school_name']} Admin"
                    st.session_state.screen = "school_app"
                    st.session_state.nav_page = "🏠 Dashboard"
                    st.rerun()
                else:
                    st.error("Incorrect Admin ID or password.")

    # ------------------------------------------------------------
    # TAB 2: TEACHER LOGIN
    # ------------------------------------------------------------
    with teacher_tab:
        col_t1, col_tcenter, col_t2 = st.columns([1, 2, 1])
        with col_tcenter:
            st.markdown(
                """
                <div class="ev-magic-card" style="margin-bottom:20px; text-align:center;">
                    <div style="font-size:1.8rem; margin-bottom:6px;">👨‍🏫</div>
                    <div style="font-size:1.25rem; font-weight:900; color:#f8fafc;">Faculty Access</div>
                    <div style="font-size:0.88rem; color:#94a3b8;">Execute smart roll-call, review occupancy, and log attendance.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            teacher_id = st.text_input("Teacher ID", key="teacher_id_input")
            password = st.text_input("Teacher Password", type="password", key="teacher_pwd_input")

            st.write("")
            if st.button("🔐 Login as Teacher", key="login_teacher_action", use_container_width=True):
                teacher_id_clean = teacher_id.strip()
                teacher = get_teacher(school_id, teacher_id_clean)

                if not teacher:
                    st.error("Teacher account not found for this school.")
                elif not teacher.get("enabled", True):
                    st.error("This teacher account has been disabled by the School Admin.")
                elif hash_password(password) != teacher.get("password_hash"):
                    st.error("Incorrect teacher password.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.role = "Teacher"
                    st.session_state.user_id = teacher_id_clean
                    st.session_state.user_name = teacher.get("teacher_name") or teacher.get("name") or teacher_id_clean
                    st.session_state.screen = "school_app"
                    st.session_state.nav_page = "🏠 Dashboard"
                    st.rerun()


# ============================================================
# SCREEN 5 — EDUVISION PLATFORM ADMIN LOGIN
# ============================================================

def platform_admin_login():
    c_title, c_back = st.columns([3, 1])
    with c_title:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <span style="font-size:2rem;">👑</span>
                <div>
                    <h2 style="margin:0; font-weight:950; color:#f8fafc;">EduVision Platform Admin</h2>
                    <div style="font-size:0.9rem; color:#94a3b8;">Platform verification and multi-campus governance.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_back:
        st.markdown('<div style="text-align:right;">', unsafe_allow_html=True)
        if st.button("← Back to Portal", key="admin_login_back"):
            go_portal()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown(
            """
            <div class="ev-magic-card" style="margin-bottom:20px; text-align:center;">
                <div class="ev-shiny-badge"><span class="ev-shiny-text">SUPERADMIN VERIFICATION</span></div>
                <div style="font-size:1.3rem; font-weight:900; color:#f8fafc; margin:10px 0 4px;">Sign In to EduVision Cloud</div>
                <div style="font-size:0.86rem; color:#94a3b8;">Enter master administrative credentials.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        admin_id = st.text_input("EduVision Admin ID", key="plat_admin_id")
        password = st.text_input("Master Password", type="password", key="plat_admin_pwd")

        st.write("")
        if st.button("🔐 Master Admin Login", key="plat_login_btn", use_container_width=True):
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
                st.error("Incorrect EduVision Master Admin credentials.")


# ============================================================
# SCREEN 6 — EDUVISION PLATFORM ADMIN PANEL (APPROVAL CARDS)
# ============================================================

def platform_admin_page():
    c_title, c_logout = st.columns([3, 1])
    with c_title:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <span style="font-size:2rem;">👑</span>
                <div>
                    <h2 style="margin:0; font-weight:950; color:#f8fafc;">EduVision Administration</h2>
                    <div style="font-size:0.9rem; color:#94a3b8;">Review pending institutional registrations and govern active campuses.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_logout:
        st.markdown('<div style="text-align:right;">', unsafe_allow_html=True)
        if st.button("🚪 Master Log Out", key="master_logout_btn"):
            go_portal()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    schools = []
    if db:
        try:
            response = db.table("schools").select("*").order("created_at", desc=True).execute()
            schools = response.data or []
        except Exception:
            try:
                response = db.table("schools").select("*").execute()
                schools = response.data or []
            except Exception as error:
                st.error(f"Error loading schools from Supabase: {error}")
                schools = []

    pending = [s for s in schools if s.get("approval_status") == "pending"]
    approved = [s for s in schools if s.get("approval_status") == "approved"]
    rejected = [s for s in schools if s.get("approval_status") == "rejected"]

    # Number Ticker Metrics Row
    m1, m2, m3 = st.columns(3)
    with m1:
        render_metric_card("⏳", "Pending Requests", len(pending), "Awaiting approval")
    with m2:
        render_metric_card("✅", "Approved Schools", len(approved), "Active campuses")
    with m3:
        render_metric_card("❌", "Rejected Requests", len(rejected), "Denied registrations")

    st.write("")

    tab1, tab2, tab3 = st.tabs([
        f"⏳ Pending Requests ({len(pending)})",
        f"✅ Approved Schools ({len(approved)})",
        f"❌ Rejected Schools ({len(rejected)})",
    ])

    # ------------------------------------------------------------
    # TAB 1: PENDING REQUESTS (PROFESSIONAL APPROVAL CARDS)
    # ------------------------------------------------------------
    with tab1:
        if not pending:
            st.info("No pending school requests. All registrations are up to date.")
        else:
            for school in pending:
                school_id = school.get("school_id", "")
                school_name = school.get("school_name", "Unnamed School")
                admin_id = school.get("admin_id", "")

                st.markdown(
                    f"""
                    <div class="ev-border-beam-box" style="margin-bottom:16px;">
                        <div class="ev-border-beam-inner">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <span class="ev-shiny-badge"><span class="ev-shiny-text">PENDING REGISTRATION</span></span>
                                    <div style="font-size:1.4rem; font-weight:950; color:#f8fafc; margin-top:8px;">{school_name}</div>
                                    <div style="font-size:0.92rem; color:#38bdf8; font-weight:800; margin-top:2px;">School ID: {school_id} &bull; Admin ID: {admin_id}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c_app, c_rej = st.columns(2)
                with c_app:
                    if st.button(f"✅ Approve {school_name}", key=f"app_{school_id}", use_container_width=True):
                        try:
                            update_payload = {
                                "approval_status": "approved",
                                "approved_by": st.session_state.user_id,
                            }
                            try:
                                update_payload["approved_at"] = datetime.now(timezone.utc).isoformat()
                            except Exception:
                                pass

                            db.table("schools").update(update_payload).eq("school_id", school_id).execute()
                            render_confetti()
                            st.success(f"{school_name} successfully approved!")
                            st.rerun()
                        except Exception:
                            # Fallback if approved_at column is not present in schema
                            try:
                                db.table("schools").update({
                                    "approval_status": "approved"
                                }).eq("school_id", school_id).execute()
                                render_confetti()
                                st.success(f"{school_name} successfully approved!")
                                st.rerun()
                            except Exception as error:
                                st.error(f"Approval error: {error}")

                with c_rej:
                    if st.button(f"❌ Reject {school_name}", key=f"rej_{school_id}", use_container_width=True):
                        try:
                            db.table("schools").update({
                                "approval_status": "rejected",
                            }).eq("school_id", school_id).execute()
                            st.warning(f"{school_name} rejected.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"Rejection error: {error}")

                st.write("")

    # ------------------------------------------------------------
    # TAB 2: APPROVED SCHOOLS
    # ------------------------------------------------------------
    with tab2:
        if not approved:
            st.info("No approved schools yet.")
        else:
            rows = []
            for s in approved:
                rows.append({
                    "School Name": s.get("school_name", ""),
                    "School ID": s.get("school_id", ""),
                    "Admin ID": s.get("admin_id", ""),
                    "Status": "Approved",
                    "Approved At": s.get("approved_at", "N/A"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------
    # TAB 3: REJECTED SCHOOLS
    # ------------------------------------------------------------
    with tab3:
        if not rejected:
            st.info("No rejected schools.")
        else:
            for s in rejected:
                s_id = s.get("school_id", "")
                s_name = s.get("school_name", "")

                col_info, col_act = st.columns([3, 1])
                with col_info:
                    st.write(f"❌ **{s_name}** — School ID: `{s_id}`")
                with col_act:
                    if st.button("Restore to Pending", key=f"restore_{s_id}"):
                        try:
                            db.table("schools").update({"approval_status": "pending"}).eq("school_id", s_id).execute()
                            st.rerun()
                        except Exception as error:
                            st.error(str(error))


# ============================================================
# SCREEN 7 — MAIN SCHOOL APPLICATION (DASHBOARD & MODULES)
# ============================================================

def dashboard_page():
    students = load_students()
    attendance = load_attendance()

    today_str = datetime.now().strftime("%Y-%m-%d")
    present_today = 0
    late_today = 0
    absent_today = 0

    if not attendance.empty and "attendance_date" in attendance.columns:
        today_rows = attendance[attendance["attendance_date"].astype(str) == today_str]
        if "status" in today_rows.columns:
            present_today = len(today_rows[today_rows["status"] == "Present"])
            late_today = len(today_rows[today_rows["status"] == "Late"])
            absent_today = len(today_rows[today_rows["status"] == "Absent"])

    total_students = len(students)
    if total_students > 0:
        attendance_percentage = round((present_today / total_students) * 100, 1)
    else:
        attendance_percentage = 0.0

    # Dynamic time-of-day greeting
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good Morning"
    elif current_hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    user_display = st.session_state.user_name or st.session_state.user_id or "Educator"

    # Header
    hero(
        f"{greeting}, {user_display}",
        f"{st.session_state.school_name} &bull; Intelligent Classroom Command Center",
        f"ROLE: {st.session_state.role.upper()}"
    )

    # Metrics Row with Number Ticker
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("🎓", "Total Students", total_students, "Enrolled in campus")
    with m2:
        render_metric_card("✅", "Present Today", present_today, f"{late_today} Late recorded")
    with m3:
        render_metric_card("📋", "Attendance Logs", len(attendance), "All historical records")
    with m4:
        render_metric_card("👤", "Access Role", st.session_state.role, "Active session", is_number=False)

    st.write("")

    # Attendance Progress & Live AI Status Row
    c_chart, c_ai_info = st.columns([1.1, 1.3])

    with c_chart:
        st.markdown('<div class="ev-magic-card">', unsafe_allow_html=True)
        render_circular_progress(attendance_percentage, "Today's Attendance Rate")
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-around; text-align:center; margin-top:8px; border-top:1px solid rgba(148,163,184,0.15); padding-top:12px;">
                <div><span style="color:#10b981; font-weight:900;">{present_today}</span><br><span style="font-size:0.78rem; color:#94a3b8;">Present</span></div>
                <div><span style="color:#f59e0b; font-weight:900;">{late_today}</span><br><span style="font-size:0.78rem; color:#94a3b8;">Late</span></div>
                <div><span style="color:#f43f5e; font-weight:900;">{absent_today}</span><br><span style="font-size:0.78rem; color:#94a3b8;">Absent</span></div>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_ai_info:
        st.markdown(
            """
            <div class="ev-magic-card" style="display:flex; flex-direction:column; justify-content:space-between; height:100%;">
                <div>
                    <div class="ev-shiny-badge" style="margin-bottom:12px;"><span class="ev-shiny-text">AI CLASSROOM INTELLIGENCE</span></div>
                    <div style="font-size:1.35rem; font-weight:900; color:#f8fafc; margin-bottom:8px;">Command Center Active</div>
                    <p style="color:#cbd5e1; font-size:0.92rem; line-height:1.65; margin-bottom:16px;">
                        EduVision pairs real-time facial recognition roll-calls with edge-computed classroom occupancy detection. Launch either vision module directly from the showcase below.
                    </p>
                </div>
                <div style="border-top:1px solid rgba(148,163,184,0.15); padding-top:12px; font-size:0.85rem; color:#94a3b8;">
                    ● OpenCV LBPH Face Engine &bull; YOLO11 Person Detection &bull; WebRTC Realtime
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.write("")

    # AI Tools Section (Neon Gradient Showcase Cards)
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
            <div class="ev-shiny-badge"><span class="ev-shiny-text">✦ CORE AI SYSTEMS</span></div>
            <div style="font-size:1.25rem; font-weight:900; color:#f8fafc;">Classroom Vision Suite</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    card1, card2 = st.columns(2)

    with card1:
        st.markdown(
            """
            <div class="ev-neon-card-blue">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <span style="font-size:1.8rem;">📷</span>
                    <span class="ev-shiny-badge"><span class="ev-shiny-text">FACE AI READY</span></span>
                </div>
                <div style="font-size:1.4rem; font-weight:900; color:#f8fafc; margin-bottom:6px;">Smart Attendance</div>
                <p style="color:#94a3b8; font-size:0.92rem; line-height:1.6; margin-bottom:18px;">
                    Automatic facial detection and recognition against enrolled student face datasets. Generates audit records with teacher verification.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Open Smart Attendance  →", key="dash_goto_attendance", use_container_width=True):
            st.session_state.nav_page = "📷 Smart Attendance"
            st.session_state["sidebar_nav_radio"] = "📷 Smart Attendance"
            st.rerun()

    with card2:
        st.markdown(
            """
            <div class="ev-neon-card-purple">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <span style="font-size:1.8rem;">👥</span>
                    <span class="ev-shiny-badge"><span class="ev-shiny-text">YOLO VISION READY</span></span>
                </div>
                <div style="font-size:1.4rem; font-weight:900; color:#f8fafc; margin-bottom:6px;">Smart Occupancy</div>
                <p style="color:#94a3b8; font-size:0.92rem; line-height:1.6; margin-bottom:18px;">
                    Ultralytics YOLO11 model detects student presence in live video, counts room occupancy, and detects empty vs filled classroom states.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Open Smart Occupancy  →", key="dash_goto_occupancy", use_container_width=True):
            st.session_state.nav_page = "👥 Smart Occupancy"
            st.session_state["sidebar_nav_radio"] = "👥 Smart Occupancy"
            st.rerun()


# ============================================================
# SUBPAGE: STUDENTS MANAGEMENT
# ============================================================

def students_page():
    is_admin = st.session_state.role == "School Admin"
    is_teacher = st.session_state.role == "Teacher"

    if is_admin:
        hero(
            "Student Approvals",
            "Review teacher-submitted student registrations and manage the approved school roster.",
            "🎓 STUDENT MANAGEMENT",
        )
    else:
        hero(
            "Students Directory",
            "View your school roster and register new students for School Admin approval.",
            "🎓 CAMPUS ROSTER",
        )

    students = load_students()

    # Normalize status values so old records using "Active" continue to work.
    if students.empty or "status" not in students.columns:
        pending_students = pd.DataFrame()
        active_students = students.copy()
        declined_students = pd.DataFrame()
    else:
        normalized_status = students["status"].fillna("Active").astype(str).str.strip().str.lower()
        pending_students = students[normalized_status == "pending"].copy()
        declined_students = students[normalized_status == "declined"].copy()
        active_students = students[~normalized_status.isin(["pending", "declined"])].copy()

    m1, m2 = st.columns(2)
    with m1:
        render_metric_card("🎓", "Active Students", len(active_students), "Approved school roster")
    with m2:
        render_metric_card("⏳", "Pending Approval", len(pending_students), "Awaiting School Admin review")

    st.write("")

    # Teachers submit student registrations. They are never activated directly.
    if is_teacher:
        with st.expander("➕ Register New Student", expanded=False):
            st.caption("The student will be sent to the School Admin for approval before becoming active.")
            c1, c2 = st.columns(2)
            with c1:
                student_id = st.text_input("Student ID (e.g., ST001)", key="teacher_reg_student_id")
                student_name = st.text_input("Full Name", key="teacher_reg_student_name")
            with c2:
                class_name = st.text_input("Class / Grade", key="teacher_reg_student_class")
                roll_no = st.text_input("Roll Number", key="teacher_reg_student_roll")

            st.write("")
            if st.button("📨 Submit Student for Approval", key="teacher_submit_student_btn", use_container_width=True):
                student_id = student_id.strip()
                student_name = student_name.strip()
                class_name = class_name.strip()
                roll_no = roll_no.strip()

                if not student_id:
                    st.error("Please enter a Student ID.")
                elif not student_name:
                    st.error("Please enter the student's name.")
                elif not class_name:
                    st.error("Please enter the student's class / grade.")
                elif not db:
                    st.error("Database connection unavailable.")
                else:
                    try:
                        db.table("students").insert({
                            "school_id": st.session_state.school_id,
                            "student_id": student_id,
                            "name": student_name,
                            "class_name": class_name,
                            "roll_no": roll_no,
                            "status": "Pending",
                        }).execute()
                        render_confetti()
                        st.success(f"{student_name} was submitted to the School Admin for approval.")
                        st.rerun()
                    except Exception as error:
                        error_text = str(error).lower()
                        if "duplicate" in error_text or "unique" in error_text or "23505" in error_text:
                            st.error("That Student ID is already registered for this school.")
                        else:
                            st.error(f"Could not submit student registration: {error}")

    # School Admin reviews teacher submissions.
    if is_admin:
        st.markdown("### ⏳ Pending Student Registrations")
        if pending_students.empty:
            st.info("No student registrations are waiting for approval.")
        else:
            visible_cols = [c for c in ["student_id", "name", "class_name", "roll_no", "status"] if c in pending_students.columns]
            st.dataframe(pending_students[visible_cols], use_container_width=True, hide_index=True)

            pending_map = {
                f"{row.get('student_id')} — {row.get('name')} — {row.get('class_name', '')}": row.get("student_id")
                for _, row in pending_students.iterrows()
            }
            selected_pending = st.selectbox(
                "Select a pending student",
                list(pending_map.keys()),
                key="pending_student_review_select",
            )
            selected_pending_id = pending_map[selected_pending]

            approve_col, decline_col = st.columns(2)
            with approve_col:
                if st.button("✅ Approve Student", key="approve_student_btn", use_container_width=True):
                    try:
                        db.table("students").update({"status": "Active"}).eq(
                            "school_id", st.session_state.school_id
                        ).eq("student_id", selected_pending_id).execute()
                        render_confetti()
                        st.success("Student approved and added to the active roster.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not approve student: {error}")

            with decline_col:
                if st.button("❌ Decline Student", key="decline_student_btn", use_container_width=True):
                    try:
                        db.table("students").update({"status": "Declined"}).eq(
                            "school_id", st.session_state.school_id
                        ).eq("student_id", selected_pending_id).execute()
                        st.warning("Student registration declined.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not decline student: {error}")

        st.write("")

    # Both roles can view the approved roster.
    st.markdown("### 🎓 Active Student Roster")
    if active_students.empty:
        st.info("No approved students are currently in the school roster.")
    else:
        visible_cols = [c for c in ["student_id", "name", "class_name", "roll_no", "status"] if c in active_students.columns]
        st.dataframe(active_students[visible_cols], use_container_width=True, hide_index=True)

    # Teachers can see their own pending submissions as pending school records.
    if is_teacher and not pending_students.empty:
        st.write("")
        with st.expander(f"⏳ Pending Registrations ({len(pending_students)})"):
            visible_cols = [c for c in ["student_id", "name", "class_name", "roll_no", "status"] if c in pending_students.columns]
            st.dataframe(pending_students[visible_cols], use_container_width=True, hide_index=True)

    # School Admin can inspect declined requests and permanently remove records.
    if is_admin and not declined_students.empty:
        st.write("")
        with st.expander(f"❌ Declined Registrations ({len(declined_students)})"):
            visible_cols = [c for c in ["student_id", "name", "class_name", "roll_no", "status"] if c in declined_students.columns]
            st.dataframe(declined_students[visible_cols], use_container_width=True, hide_index=True)

    if is_admin and not students.empty:
        st.divider()
        st.markdown("### 🗑 Remove Student Record")
        student_map = {
            f"{row.get('student_id')} — {row.get('name')} — {row.get('status', 'Active')}": row.get("student_id")
            for _, row in students.iterrows()
        }
        selected_student_label = st.selectbox(
            "Select Student Record to Remove",
            list(student_map.keys()),
            key="del_student_select",
        )

        if st.button("🗑 Remove Student Record", key="del_student_btn"):
            sid = student_map[selected_student_label]
            try:
                db.table("students").delete().eq("school_id", st.session_state.school_id).eq("student_id", sid).execute()
                st.success("Student record removed successfully.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not delete student: {error}")


# ============================================================
# SUBPAGE: TEACHERS MANAGEMENT (ADMIN ONLY)
# ============================================================

def teachers_page():
    if st.session_state.role != "School Admin":
        st.error("School Admin privileges required to access Teacher Management.")
        return

    hero("Teacher Management", "Create, enable, and manage permanent faculty accounts for this campus.", "👨‍🏫 FACULTY DIRECTORY")

    teachers = []
    if db and st.session_state.school_id:
        try:
            response = db.table("teachers").select("*").eq("school_id", st.session_state.school_id).order("teacher_name").execute()
            teachers = response.data or []
        except Exception:
            try:
                response = db.table("teachers").select("*").eq("school_id", st.session_state.school_id).order("name").execute()
                teachers = response.data or []
            except Exception:
                try:
                    response = db.table("teachers").select("*").eq("school_id", st.session_state.school_id).execute()
                    teachers = response.data or []
                except Exception as error:
                    st.error(f"Error loading teachers: {error}")
                    teachers = []

    active_teachers = [t for t in teachers if t.get("enabled", True)]

    t_m1, t_m2 = st.columns(2)
    with t_m1:
        render_metric_card("👨‍🏫", "Total Teachers", len(teachers), "Registered faculty")
    with t_m2:
        render_metric_card("🟢", "Active Accounts", len(active_teachers), "Enabled for login")

    st.write("")

    # Add Teacher Expander
    with st.expander("➕ Create New Teacher Account"):
        c1, c2 = st.columns(2)
        with c1:
            t_id = st.text_input("Teacher ID (e.g. TCH01)", key="add_t_id")
            t_name = st.text_input("Teacher Name", key="add_t_name")
        with c2:
            t_pwd = st.text_input("Temporary Password", type="password", key="add_t_pwd")

        st.write("")
        if st.button("✨ Create Teacher Account", key="submit_add_teacher_btn"):
            t_id = t_id.strip()
            t_name = t_name.strip()

            if not t_id:
                st.error("Please enter a Teacher ID.")
            elif not t_name:
                st.error("Please enter the teacher's name.")
            elif len(t_pwd) < 6:
                st.error("Password must be at least 6 characters.")
            elif not db:
                st.error("Database connection unavailable.")
            else:
                try:
                    db.table("teachers").insert({
                        "school_id": st.session_state.school_id,
                        "teacher_id": t_id,
                        "teacher_name": t_name,
                        "password_hash": hash_password(t_pwd),
                        "enabled": True,
                    }).execute()

                    render_confetti()
                    st.success(f"Teacher account for {t_name} created permanently.")
                    st.rerun()
                except Exception:
                    try:
                        db.table("teachers").insert({
                            "school_id": st.session_state.school_id,
                            "teacher_id": t_id,
                            "name": t_name,
                            "password_hash": hash_password(t_pwd),
                            "enabled": True,
                        }).execute()

                        render_confetti()
                        st.success(f"Teacher account for {t_name} created permanently.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not create teacher: {error}")

    st.write("")
    if not teachers:
        st.info("No teacher accounts created yet.")
        return

    # Teachers Table
    rows = []
    for t in teachers:
        name_val = t.get("teacher_name") or t.get("name") or t.get("teacher_id", "")
        rows.append({
            "Teacher ID": t.get("teacher_id", ""),
            "Name": name_val,
            "Status": "Enabled" if t.get("enabled", True) else "Disabled",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Manage Teacher (Enable/Disable / Delete)
    st.divider()
    st.markdown("### ⚙️ Manage Teacher Account")
    t_options = {}
    for t in teachers:
        tid = t.get("teacher_id", "")
        tname = t.get("teacher_name") or t.get("name") or tid
        t_options[f"{tid} — {tname}"] = t

    selected_t_label = st.selectbox("Select Teacher", list(t_options.keys()), key="manage_t_select")
    target_t = t_options[selected_t_label]

    is_enabled = target_t.get("enabled", True)
    c_toggle, c_del = st.columns(2)

    with c_toggle:
        toggle_label = "Disable Teacher" if is_enabled else "Enable Teacher"
        if st.button(toggle_label, key="toggle_teacher_status"):
            try:
                db.table("teachers").update({"enabled": not is_enabled}).eq("school_id", st.session_state.school_id).eq("teacher_id", target_t["teacher_id"]).execute()
                st.rerun()
            except Exception as error:
                st.error(str(error))

    with c_del:
        if st.button("🗑 Delete Teacher Permanently", key="delete_teacher_btn"):
            try:
                db.table("teachers").delete().eq("school_id", st.session_state.school_id).eq("teacher_id", target_t["teacher_id"]).execute()
                st.rerun()
            except Exception as error:
                st.error(str(error))


# ============================================================
# SUBPAGE: SMART ATTENDANCE (WEBRTC + MANUAL + HISTORY)
# ============================================================

def attendance_page():
    hero(
        "Smart Attendance",
        "AI face recognition, manual roll-call corrections, and live attendance logs in one hub.",
        "📷 AI FACE RECOGNITION"
    )

    st.markdown(
        """
        <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:18px; padding:6px 14px; border-radius:999px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); color:#38bdf8; font-weight:800; font-size:0.84rem;">
            <span class="ev-pulse-dot"></span> AI Camera Ready &bull; OpenCV Face Recognition Active
        </div>
        """,
        unsafe_allow_html=True,
    )

    students = load_students()

    camera_tab, manual_tab, history_tab = st.tabs([
        "🤖 AI Camera Roll-Call",
        "✋ Manual Attendance",
        "📋 Attendance Records",
    ])

    # ------------------------------------------------------------
    # TAB 1: AI CAMERA
    # ------------------------------------------------------------
    with camera_tab:
        st.markdown(
            """
            <div class="ev-border-beam-box" style="margin-bottom:20px;">
                <div class="ev-border-beam-inner">
                    <div style="font-size:1.15rem; font-weight:900; color:#f8fafc; margin-bottom:4px;">Live Facial Recognition Stream</div>
                    <div style="font-size:0.88rem; color:#94a3b8;">
                        Press <strong>START</strong> below to activate your browser webcam. The camera will detect faces, classify recognized students, and automatically record attendance.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:
            from smart_attendance import render_page as render_smart_attendance
            render_smart_attendance()
        except Exception as error:
            st.error("Smart Attendance engine could not be initialized.")
            st.code(str(error))

    # ------------------------------------------------------------
    # TAB 2: MANUAL ATTENDANCE
    # ------------------------------------------------------------
    with manual_tab:
        if students.empty:
            st.warning("No students registered. Please enroll students first in the Students directory.")
        else:
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                student_opts = {f"{r.get('student_id')} — {r.get('name')}": r for _, r in students.iterrows()}
                selected_st = st.selectbox("Select Student", list(student_opts.keys()), key="man_student_select")
            with col_m2:
                status_choice = st.selectbox("Attendance Status", ["Present", "Late", "Absent"], key="man_status_select")

            st.write("")
            if st.button("✅ Save Attendance Record", key="save_manual_att_btn"):
                st_data = student_opts[selected_st]
                now = datetime.now()
                att_date = now.strftime("%Y-%m-%d")
                att_time = now.strftime("%H:%M:%S")

                record = {
                    "school_id": st.session_state.school_id,
                    "student_id": st_data.get("student_id", ""),
                    "name": st_data.get("name", ""),
                    "class_name": st_data.get("class_name", ""),
                    "attendance_date": att_date,
                    "attendance_time": att_time,
                    "status": status_choice,
                }

                if not db:
                    st.error("Database unavailable.")
                else:
                    try:
                        existing = (
                            db.table("attendance")
                            .select("id")
                            .eq("school_id", st.session_state.school_id)
                            .eq("student_id", record["student_id"])
                            .eq("attendance_date", att_date)
                            .execute()
                        )

                        if existing.data:
                            db.table("attendance").update({
                                "name": record["name"],
                                "class_name": record["class_name"],
                                "attendance_time": att_time,
                                "status": status_choice,
                            }).eq("id", existing.data[0]["id"]).execute()
                        else:
                            db.table("attendance").insert(record).execute()

                        st.success(f"{record['name']} marked as {status_choice}.")
                    except Exception as error:
                        st.error(f"Could not save attendance: {error}")

    # ------------------------------------------------------------
    # TAB 3: ATTENDANCE HISTORY
    # ------------------------------------------------------------
    with history_tab:
        att = load_attendance()
        if att.empty:
            st.info("No attendance records logged yet.")
        else:
            cols = [c for c in ["student_id", "name", "class_name", "attendance_date", "attendance_time", "status"] if c in att.columns]
            st.dataframe(att[cols], use_container_width=True, hide_index=True)


# ============================================================
# SUBPAGE: SMART OCCUPANCY (YOLO11 VISION)
# ============================================================

def occupancy_page():
    hero(
        "Smart Occupancy",
        "Real-time classroom person detection and head-count intelligence powered by YOLO11 AI.",
        "👥 REAL-TIME CLASSROOM INTELLIGENCE"
    )

    st.markdown(
        """
        <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:18px; padding:6px 14px; border-radius:999px; background:rgba(168,85,247,0.1); border:1px solid rgba(168,85,247,0.3); color:#c084fc; font-weight:800; font-size:0.84rem;">
            <span class="ev-pulse-dot" style="background:#a855f7;"></span> YOLO Vision Ready &bull; Ultralytics YOLO11 Model Active
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="ev-neon-card-purple" style="margin-bottom:20px;">
            <div style="font-size:1.15rem; font-weight:900; color:#f8fafc; margin-bottom:4px;">YOLO11 Live Person Detection</div>
            <div style="font-size:0.88rem; color:#cbd5e1;">
                Activate the stream below to detect and track students and faculty in the classroom. Bounding boxes and live headcounts update instantaneously.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        from smart_occupancy import render_page as render_smart_occupancy
        render_smart_occupancy()
    except Exception as error:
        st.error("Smart Occupancy engine could not be initialized.")
        st.code(str(error))


# ============================================================
# SUBPAGE: REPORTS & ANALYTICS
# ============================================================

def reports_page():
    hero("Reports & Analytics", "Institutional attendance rates, participation statistics, and audit reports.", "📊 CLASSROOM INSIGHTS")

    students = load_students()
    attendance = load_attendance()

    total_records = len(attendance)
    present_count = 0

    if not attendance.empty and "status" in attendance.columns:
        present_count = len(attendance[attendance["status"] == "Present"])

    overall_pct = round((present_count / total_records) * 100, 1) if total_records > 0 else 0.0

    r1, r2, r3 = st.columns(3)
    with r1:
        render_metric_card("🎓", "Total Students", len(students), "Roster size")
    with r2:
        render_metric_card("📋", "Total Logs", total_records, "All records logged")
    with r3:
        render_metric_card("✅", "Present Count", present_count, f"{overall_pct}% attendance rate")

    st.write("")

    c_circle, c_data = st.columns([1, 2])
    with c_circle:
        st.markdown('<div class="ev-magic-card">', unsafe_allow_html=True)
        render_circular_progress(overall_pct, "Cumulative Attendance Rate")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_data:
        st.markdown(
            """
            <div class="ev-magic-card">
                <div style="font-size:1.1rem; font-weight:850; color:#f8fafc; margin-bottom:8px;">Recent Attendance Records</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if attendance.empty:
            st.info("No records recorded yet.")
        else:
            cols = [c for c in ["student_id", "name", "class_name", "attendance_date", "attendance_time", "status"] if c in attendance.columns]
            st.dataframe(attendance[cols], use_container_width=True, hide_index=True)


# ============================================================
# SUBPAGE: SETTINGS & WORKSPACE
# ============================================================

def settings_page():
    hero("Workspace Settings", "Campus workspace information, connection status, and theme indicators.", "⚙️ CONFIGURATION")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            f"""
            <div class="ev-magic-card">
                <div style="font-size:1.2rem; font-weight:850; color:#f8fafc; margin-bottom:12px;">Account & Campus Info</div>
                <div style="font-size:0.92rem; color:#cbd5e1; line-height:1.8;">
                    <strong>School:</strong> {st.session_state.school_name}<br>
                    <strong>School ID:</strong> <span style="color:#38bdf8;">{st.session_state.school_id}</span><br>
                    <strong>Assigned Role:</strong> {st.session_state.role}<br>
                    <strong>User Account:</strong> {st.session_state.user_name or st.session_state.user_id}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        db_badge = "🟢 CONNECTED" if db else "🟡 OFFLINE / CONFIG NEEDED"
        st.markdown(
            f"""
            <div class="ev-magic-card">
                <div style="font-size:1.2rem; font-weight:850; color:#f8fafc; margin-bottom:12px;">System & AI Status</div>
                <div style="font-size:0.92rem; color:#cbd5e1; line-height:1.8;">
                    <strong>Cloud Database:</strong> {db_badge}<br>
                    <strong>WebRTC Streamer:</strong> 🟢 READY<br>
                    <strong>YOLO11 Model:</strong> 🟢 READY<br>
                    <strong>Theme Mode:</strong> 🌙 Deep Space Dark (Default Brand)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.info("☁️ School accounts, staff credentials, students, and attendance records are encrypted and synced to the Supabase cloud database.")


# ============================================================
# SCHOOL APPLICATION FRAME (SIDEBAR + ROUTING)
# ============================================================

def school_application():
    with st.sidebar:
        # Branding Header
        st.markdown(
            """
            <div style="padding:10px 0 16px; border-bottom:1px solid rgba(148,163,184,0.15); margin-bottom:14px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.8rem;">🎓</span>
                    <div>
                        <div style="font-size:1.35rem; font-weight:950; letter-spacing:-0.03em; color:#f8fafc;">EduVision</div>
                        <div style="font-size:0.75rem; color:#38bdf8; font-weight:800; letter-spacing:0.06em; text-transform:uppercase;">AI Smart Campus</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"🏫 **{st.session_state.school_name}**")
        st.markdown(
            f"""
            <div style="display:inline-flex; align-items:center; gap:8px; padding:4px 10px; border-radius:8px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); color:#7dd3fc; font-size:0.8rem; font-weight:800; margin-bottom:12px;">
                👤 {st.session_state.role}
            </div>
            <div style="font-size:0.78rem; color:#a7f3d0; margin-bottom:16px;">
                <span class="ev-pulse-dot" style="width:7px; height:7px;"></span> Cloud Synchronized
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Navigation Options strictly adhering to Role Hierarchy
        if st.session_state.role == "School Admin":
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
            ]

        # Sync navigation with session state
        curr_page = st.session_state.get("nav_page", "🏠 Dashboard")
        curr_index = pages.index(curr_page) if curr_page in pages else 0

        page = st.radio("Classroom Navigation", pages, index=curr_index, key="sidebar_nav_radio")
        st.session_state.nav_page = page

        st.divider()

        # Theme indicator (Animated visual)
        st.markdown(
            """
            <div style="padding:8px 12px; border-radius:12px; background:rgba(15,23,42,0.65); border:1px solid rgba(148,163,184,0.15); margin-bottom:16px; font-size:0.8rem; color:#cbd5e1;">
                🌙 <strong>Dark AI Mode</strong> (Active)
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚪 Log Out", key="sidebar_logout_btn"):
            clear_login()
            st.session_state.screen = "school_portal"
            st.rerun()

    # Dispatch to current selected subpage with role protection
    if page == "🏠 Dashboard":
        dashboard_page()
    elif page == "🎓 Students":
        students_page()
    elif page == "👨‍🏫 Teachers":
        if st.session_state.role == "School Admin":
            teachers_page()
        else:
            st.error("School Admin privileges required to manage teachers.")
    elif page == "📷 Smart Attendance":
        attendance_page()
    elif page == "👥 Smart Occupancy":
        occupancy_page()
    elif page == "📊 Reports":
        reports_page()
    elif page == "⚙️ Settings":
        if st.session_state.role == "School Admin":
            settings_page()
        else:
            st.error("School Admin privileges required to view settings.")


# ============================================================
# MASTER APPLICATION ROUTER
# ============================================================

# Guarantee brand-new sessions always start at the Welcome screen.
# Without this sentinel, Render/Streamlit can serve a cached script
# run where DEFAULT_SESSION has already been applied but the screen
# value gets overwritten before the router reads it.
if "ev_initialized" not in st.session_state:
    st.session_state["ev_initialized"] = True
    st.session_state.screen = "welcome"

current_screen = st.session_state.screen

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
    go_welcome()

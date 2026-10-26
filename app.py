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
# WHITE MINIMALIST / BOXY UI
# ============================================================

st.markdown(
    """
    <style>

    /* ==============================
       MAIN APP
       ============================== */

    html,
    body,
    [data-testid="stAppViewContainer"],
    .stApp {
        background: #f7f7f5 !important;
        color: #111111 !important;
        font-family: Inter, -apple-system, BlinkMacSystemFont,
                     "Segoe UI", sans-serif !important;
    }

    .stApp {
        background-image: none !important;
    }


    /* ==============================
       REMOVE HEAVY VISUAL EFFECTS
       ============================== */

    .ev-flicker-grid,
    .ev-light-rays,
    .ev-meteor,
    .ev-floating-node,
    .ev-light-sweep-overlay,
    .ev-confetti-container {
        display: none !important;
    }


    /* ==============================
       SCROLL PROGRESS
       ============================== */

    .ev-scroll-progress {
        height: 2px !important;
        background: #111111 !important;
        box-shadow: none !important;
    }


    /* ==============================
       MAIN CARDS / BOXES
       ============================== */

    .ev-welcome-hero,
    .ev-magic-card,
    .ev-border-beam-box,
    .ev-border-beam-inner,
    .ev-neon-card-blue,
    .ev-neon-card-purple,
    .ev-metric-card,
    [data-testid="stMetric"],
    [data-testid="stExpander"] {

        background: #ffffff !important;
        background-image: none !important;

        color: #111111 !important;

        border: 1px solid #dedede !important;
        border-radius: 8px !important;

        box-shadow: none !important;
        backdrop-filter: none !important;
        filter: none !important;
    }


    /* ==============================
       CARD HOVER
       ============================== */

    .ev-magic-card:hover,
    .ev-neon-card-blue:hover,
    .ev-neon-card-purple:hover,
    .ev-metric-card:hover {

        transform: translateY(-2px) !important;

        border-color: #111111 !important;

        box-shadow: none !important;
    }


    .ev-border-beam-box::before {
        display: none !important;
    }


    /* ==============================
       WELCOME PAGE
       ============================== */

    .ev-welcome-hero {

        max-width: 1000px !important;

        padding: 60px 30px 50px !important;

        border-radius: 8px !important;
    }


    /* EDUVISION */

    .ev-aurora-title,
    .ev-welcome-brand {

        color: #111111 !important;

        -webkit-text-fill-color: #111111 !important;

        background: none !important;

        text-shadow: none !important;

        filter: none !important;

        animation: none !important;

        font-size: clamp(4rem, 9vw, 6.5rem) !important;

        font-weight: 950 !important;

        letter-spacing: -0.055em !important;
    }


    /* Future of Smart Classrooms */

    .ev-kinetic-sub {

        color: #111111 !important;

        font-weight: 850 !important;
    }


    .ev-kinetic-word {

        color: #111111 !important;

        -webkit-text-fill-color: #111111 !important;

        background: none !important;

        animation: none !important;
    }


    .ev-welcome-tagline {

        color: #6b7280 !important;
    }


    /* ==============================
       BADGES
       ============================== */

    .ev-shiny-badge,
    .ev-badge-chip {

        background: #ffffff !important;

        border: 1px solid #d4d4d4 !important;

        border-radius: 5px !important;

        box-shadow: none !important;

        color: #111111 !important;
    }


    .ev-shiny-text {

        color: #111111 !important;

        -webkit-text-fill-color: #111111 !important;

        background: none !important;

        animation: none !important;
    }


    /* ==============================
       BUTTONS
       ============================== */

    div.stButton > button,
    .ev-enter-btn-wrapper div.stButton > button {

        min-height: 46px !important;

        background: #111111 !important;

        background-image: none !important;

        color: #ffffff !important;

        border: 1px solid #111111 !important;

        border-radius: 6px !important;

        box-shadow: none !important;

        font-weight: 750 !important;

        transition:
            background 0.15s ease,
            transform 0.15s ease !important;
    }


    div.stButton > button:hover,
    .ev-enter-btn-wrapper div.stButton > button:hover {

        background: #333333 !important;

        border-color: #333333 !important;

        transform: translateY(-1px) !important;

        box-shadow: none !important;
    }


    .ev-enter-btn-wrapper div.stButton > button::before {
        display: none !important;
    }


    /* ==============================
       INPUTS / LOGIN
       ============================== */

    div[data-baseweb="input"],
    div[data-baseweb="select"] > div {

        background: #ffffff !important;

        color: #111111 !important;

        border: 1px solid #d4d4d4 !important;

        border-radius: 6px !important;

        box-shadow: none !important;
    }


    div[data-baseweb="input"] input {

        color: #111111 !important;

        -webkit-text-fill-color: #111111 !important;
    }


    div[data-baseweb="select"] span {

        color: #111111 !important;
    }


    input::placeholder {

        color: #9ca3af !important;

        -webkit-text-fill-color: #9ca3af !important;
    }


    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {

        border-color: #111111 !important;

        box-shadow: 0 0 0 1px #111111 !important;
    }


    /* Dropdown options */

    li[role="option"] {

        color: #111111 !important;

        background: #ffffff !important;
    }


    li[role="option"]:hover {

        background: #f3f4f6 !important;
    }


    /* ==============================
       SIDEBAR
       ============================== */

    [data-testid="stSidebar"] {

        background: #ffffff !important;

        background-image: none !important;

        border-right: 1px solid #dedede !important;
    }


    [data-testid="stSidebar"] [role="radiogroup"] label {

        border-radius: 5px !important;

        color: #111111 !important;
    }


    [data-testid="stSidebar"] [role="radiogroup"] label:hover {

        background: #f5f5f5 !important;

        transform: none !important;
    }


    [data-testid="stSidebar"]
    [role="radiogroup"]
    label[data-checked="true"] {

        background: #eeeeec !important;

        border: 1px solid #d4d4d4 !important;
    }


    /* ==============================
       TABLES
       ============================== */

    [data-testid="stDataFrame"] {

        background: #ffffff !important;

        border: 1px solid #dedede !important;

        border-radius: 6px !important;

        box-shadow: none !important;
    }


    /* ==============================
       TABS
       ============================== */

    button[data-baseweb="tab"] {

        color: #6b7280 !important;

        border-radius: 0 !important;
    }


    button[data-baseweb="tab"][aria-selected="true"] {

        color: #111111 !important;

        border-bottom-color: #111111 !important;
    }


    /* ==============================
       TEXT
       ============================== */

    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {

        color: #111111 !important;
    }


    .ev-card-title {

        color: #111111 !important;
    }


    .ev-card-desc {

        color: #6b7280 !important;
    }


    hr {

        border-color: #e5e7eb !important;
    }


    /* ==============================
       PORTAL INLINE TEXT OVERRIDES
       ============================== */

    .ev-portal-container [style*="color:#f8fafc"],
    .ev-portal-container [style*="color: #f8fafc"] {

        color: #111111 !important;
    }


    .ev-portal-container [style*="color:#cbd5e1"],
    .ev-portal-container [style*="color: #cbd5e1"],
    .ev-portal-container [style*="color:#94a3b8"] {

        color: #6b7280 !important;
    }


    /* ==============================
       MOBILE
       ============================== */

    @media (max-width: 700px) {

        .ev-welcome-hero {

            padding: 42px 18px 36px !important;

            border-radius: 8px !important;
        }


        .ev-welcome-brand {

            font-size: clamp(
                2.8rem,
                16vw,
                4.5rem
            ) !important;
        }

    }

    </style>
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
    # ============================================================
    # MINIMAL WELCOME PAGE
    # ============================================================

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
                font-size:clamp(3.5rem, 9vw, 6.5rem);
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

    # ============================================================
    # ENTER BUTTON
    # ============================================================

    col_left, col_button, col_right = st.columns(
        [1.3, 1, 1.3]
    )

    with col_button:

        if st.button(
            "Enter EduVision →",
            key="enter_eduvision_btn",
            use_container_width=True
        ):
            st.session_state.screen = "portal"
            st.rerun()

    # ============================================================
    # SYSTEM STATUS
    # ============================================================

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
# SCREEN 2 — EDUVISION PORTAL (BENTO GRID & ACTIONS)
# ============================================================

def portal_screen():
    """Minimal EduVision workspace selection."""

    st.markdown(
        """
        <div style="
            max-width:1000px;
            margin:20px auto 35px;
            padding:0 4px;
        ">
            <div style="
                font-size:1.5rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                EduVision
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Back button
    _, back_col = st.columns([4, 1])

    with back_col:
        if st.button(
            "← Back",
            key="portal_back_welcome",
            use_container_width=True
        ):
            go_welcome()

    # Simple heading
    st.markdown(
        """
        <div style="
            max-width:1000px;
            margin:35px auto 40px;
        ">
            <h1 style="
                color:#111111;
                font-size:clamp(2.3rem,5vw,4rem);
                font-weight:900;
                letter-spacing:-0.055em;
                margin:0 0 12px 0;
            ">
                Choose your workspace
            </h1>

            <p style="
                color:#6b7280;
                font-size:1.05rem;
                margin:0;
            ">
                Select how you want to access EduVision.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    school_col, admin_col = st.columns(2, gap="large")

    # -----------------------------
    # SCHOOL PORTAL
    # -----------------------------

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
                    font-size:0.95rem;
                ">
                    Access your school workspace for attendance,
                    students and classroom management.
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
            st.session_state.screen = "school_portal"
            st.rerun()

    # -----------------------------
    # EDUVISION ADMIN
    # -----------------------------

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
                    font-size:0.95rem;
                ">
                    Review and manage school registration
                    requests.
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
            st.session_state.screen = "platform_admin_login"
            st.rerun()
# ============================================================
# SCREEN 3 — SCHOOL PORTAL (REGISTER & OPEN EXISTING)
# ============================================================
def school_portal():
    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------
    c_title, c_back = st.columns([4, 1])

    with c_title:
        st.markdown(
            """
            <div style="margin-bottom:18px;">
                <div style="
                    font-size:2rem;
                    font-weight:900;
                    letter-spacing:-0.04em;
                    color:#111111;
                ">
                    School Portal
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.95rem;
                    margin-top:5px;
                ">
                    Register a school or access an approved school.
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

    # ------------------------------------------------------------
    # TABS
    # ------------------------------------------------------------
    register_tab, open_tab = st.tabs([
        "Register School",
        "Open School",
    ])

    # ============================================================
    # REGISTER SCHOOL
    # ============================================================
    with register_tab:

        st.markdown(
            """
            <div style="
                margin:24px 0 22px;
            ">
                <div style="
                    font-size:1.35rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:6px;
                ">
                    Create a school workspace
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.92rem;
                ">
                    Enter your school and administrator details.
                    Registration must be approved before the school can be accessed.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_reg1, col_reg2 = st.columns(2)

        with col_reg1:

            school_name = st.text_input(
                "School Name",
                placeholder="Enter school name",
                key="reg_school_name",
            )

            admin_id = st.text_input(
                "School Admin ID",
                placeholder="Create admin ID",
                key="reg_admin_id",
            )

        with col_reg2:

            admin_password = st.text_input(
                "Admin Password",
                type="password",
                placeholder="Minimum 6 characters",
                key="reg_admin_pwd",
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Repeat password",
                key="reg_admin_confirm",
            )

        st.write("")

        if st.button(
            "Submit Registration",
            key="submit_reg_btn",
            use_container_width=True,
        ):

            school_name = school_name.strip()
            admin_id = admin_id.strip()

            if not school_name:

                st.error("Please enter your school name.")

            elif not admin_id:

                st.error("Please enter a School Admin ID.")

            elif len(admin_password) < 6:

                st.error(
                    "Password must be at least 6 characters long."
                )

            elif admin_password != confirm_password:

                st.error("Passwords do not match.")

            elif not db:

                st.error(
                    "Database connection is currently unavailable."
                )

            else:

                school_id = generate_school_id()

                try:

                    db.table("schools").insert({
                        "school_id": school_id,
                        "school_name": school_name,
                        "admin_id": admin_id,
                        "admin_password_hash": hash_password(
                            admin_password
                        ),
                        "approval_status": "pending",
                    }).execute()

                    st.success(
                        "School registration submitted successfully."
                    )

                    # Simple credentials box
                    st.markdown(
                        f"""
                        <div style="
                            background:#ffffff;
                            border:1px solid #d1d5db;
                            border-radius:8px;
                            padding:22px;
                            margin-top:18px;
                        ">

                            <div style="
                                font-size:0.78rem;
                                font-weight:800;
                                color:#6b7280;
                                text-transform:uppercase;
                                letter-spacing:0.06em;
                                margin-bottom:8px;
                            ">
                                Save these details
                            </div>

                            <div style="
                                font-size:1.25rem;
                                font-weight:850;
                                color:#111111;
                                margin-bottom:6px;
                            ">
                                School ID: {school_id}
                            </div>

                            <div style="
                                font-size:0.95rem;
                                color:#374151;
                            ">
                                Admin ID: <strong>{admin_id}</strong>
                            </div>

                            <div style="
                                font-size:0.85rem;
                                color:#6b7280;
                                margin-top:12px;
                            ">
                                Save your School ID. You will need it
                                after your registration is approved.
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                except Exception as error:

                    st.error(
                        f"School registration failed: {error}"
                    )

    # ============================================================
    # OPEN EXISTING SCHOOL
    # ============================================================
    with open_tab:

        st.markdown(
            """
            <div style="
                margin:24px 0 22px;
            ">

                <div style="
                    font-size:1.35rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:6px;
                ">
                    Open your school
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.92rem;
                ">
                    Select your approved school to continue.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        # --------------------------------------------------------
        # LOAD APPROVED SCHOOLS
        # --------------------------------------------------------

        approved_schools = []

        if db:

            try:

                resp = (
                    db.table("schools")
                    .select("school_id, school_name")
                    .eq("approval_status", "approved")
                    .execute()
                )

                approved_schools = (
                    resp.data if resp.data else []
                )

            except Exception as error:

                st.error(
                    f"Could not load school list: {error}"
                )

        # --------------------------------------------------------
        # SCHOOL SELECTOR
        # --------------------------------------------------------

        if not approved_schools:

            st.info(
                "No approved schools are currently available."
            )

        else:

            school_name_to_id = {
                school["school_name"]: school["school_id"]
                for school in approved_schools
            }

            school_names = sorted(
                school_name_to_id.keys()
            )

            selected_name = st.selectbox(
                "School",
                options=school_names,
                index=0,
                placeholder="Select your school",
                key="open_school_name_select",
            )

            st.write("")

            if st.button(
                "Continue →",
                key="open_school_action_btn",
                use_container_width=True,
            ):

                selected_id = (
                    school_name_to_id
                    .get(selected_name, "")
                    .strip()
                )

                if not selected_id:

                    st.error(
                        "Please select a school."
                    )

                elif not db:

                    st.error(
                        "Database connection unavailable."
                    )

                else:

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

    # ------------------------------------------------------------
    # SIMPLE HEADER
    # ------------------------------------------------------------

    c_title, c_change = st.columns([4, 1])

    with c_title:
        st.markdown(
            f"""
            <div style="margin-bottom:18px;">
                <div style="
                    font-size:2rem;
                    font-weight:900;
                    letter-spacing:-0.04em;
                    color:#111111;
                ">
                    {school['school_name']}
                </div>

                <div style="
                    font-size:0.9rem;
                    color:#6b7280;
                    margin-top:5px;
                ">
                    School ID: {school_id}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_change:

        if st.button(
            "← Change School",
            key="change_school_btn",
            use_container_width=True
        ):
            clear_login()
            st.session_state.screen = "school_portal"
            st.rerun()

    st.divider()

    # ------------------------------------------------------------
    # LOGIN TYPE
    # ------------------------------------------------------------

    admin_tab, teacher_tab = st.tabs([
        "School Admin",
        "Teacher",
    ])

    # ============================================================
    # SCHOOL ADMIN
    # ============================================================

    with admin_tab:

        col_left, col_center, col_right = st.columns([1, 2, 1])

        with col_center:

            st.markdown(
                """
                <div style="
                    margin:28px 0 24px;
                ">
                    <div style="
                        font-size:1.45rem;
                        font-weight:850;
                        color:#111111;
                        margin-bottom:6px;
                    ">
                        Admin Login
                    </div>

                    <div style="
                        color:#6b7280;
                        font-size:0.92rem;
                    ">
                        Sign in to manage your school.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            admin_id = st.text_input(
                "Admin ID",
                placeholder="Enter admin ID",
                key="school_admin_id_input"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
                key="school_admin_pwd_input"
            )

            st.write("")

            if st.button(
                "Login",
                key="login_admin_action",
                use_container_width=True
            ):

                admin_id_clean = admin_id.strip()

                school_account = get_school_by_admin(
                    school_id,
                    admin_id_clean
                )

                if (
                    school_account
                    and hash_password(password)
                    == school_account.get("admin_password_hash")
                ):

                    st.session_state.logged_in = True
                    st.session_state.role = "School Admin"
                    st.session_state.user_id = admin_id_clean
                    st.session_state.user_name = (
                        f"{school['school_name']} Admin"
                    )

                    st.session_state.screen = "school_app"
                    st.session_state.nav_page = "🏠 Dashboard"

                    st.rerun()

                else:

                    st.error(
                        "Incorrect Admin ID or password."
                    )

    # ============================================================
    # TEACHER
    # ============================================================

    with teacher_tab:

        col_left, col_center, col_right = st.columns([1, 2, 1])

        with col_center:

            st.markdown(
                """
                <div style="
                    margin:28px 0 24px;
                ">
                    <div style="
                        font-size:1.45rem;
                        font-weight:850;
                        color:#111111;
                        margin-bottom:6px;
                    ">
                        Teacher Login
                    </div>

                    <div style="
                        color:#6b7280;
                        font-size:0.92rem;
                    ">
                        Sign in to access your classroom.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            teacher_id = st.text_input(
                "Teacher ID",
                placeholder="Enter teacher ID",
                key="teacher_id_input"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
                key="teacher_pwd_input"
            )

            st.write("")

            if st.button(
                "Login",
                key="login_teacher_action",
                use_container_width=True
            ):

                teacher_id_clean = teacher_id.strip()

                teacher = get_teacher(
                    school_id,
                    teacher_id_clean
                )

                if not teacher:

                    st.error(
                        "Teacher account not found for this school."
                    )

                elif not teacher.get("enabled", True):

                    st.error(
                        "This teacher account has been disabled."
                    )

                elif (
                    hash_password(password)
                    != teacher.get("password_hash")
                ):

                    st.error(
                        "Incorrect teacher password."
                    )

                else:

                    st.session_state.logged_in = True
                    st.session_state.role = "Teacher"
                    st.session_state.user_id = teacher_id_clean

                    st.session_state.user_name = (
                        teacher.get("teacher_name")
                        or teacher.get("name")
                        or teacher_id_clean
                    )

                    st.session_state.screen = "school_app"
                    st.session_state.nav_page = "🏠 Dashboard"

                    st.rerun()
# ============================================================
# SCREEN 5 — EDUVISION PLATFORM ADMIN LOGIN
# ============================================================

def platform_admin_login():
    # ============================================================
    # HEADER
    # ============================================================

    c_title, c_back = st.columns([4, 1])

    with c_title:
        st.markdown(
            """
            <div style="margin-bottom:18px;">
                <div style="
                    font-size:2rem;
                    font-weight:900;
                    letter-spacing:-0.04em;
                    color:#111111;
                ">
                    EduVision Admin
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.95rem;
                    margin-top:5px;
                ">
                    Sign in to manage school registrations.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_back:
        if st.button(
            "← Back",
            key="admin_login_back",
            use_container_width=True
        ):
            go_portal()

    st.divider()

    # ============================================================
    # LOGIN FORM
    # ============================================================

    col_left, col_center, col_right = st.columns(
        [1, 2, 1]
    )

    with col_center:

        st.markdown(
            """
            <div style="margin:28px 0 24px;">
                <div style="
                    font-size:1.4rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:6px;
                ">
                    Admin Login
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.92rem;
                ">
                    Enter your EduVision administrator credentials.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        admin_id = st.text_input(
            "Admin ID",
            placeholder="Enter Admin ID",
            key="plat_admin_id"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
            key="plat_admin_pwd"
        )

        st.write("")

        if st.button(
            "Login",
            key="plat_login_btn",
            use_container_width=True
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
# SCREEN 6 — EDUVISION PLATFORM ADMIN PANEL (APPROVAL CARDS)
# ============================================================

def platform_admin_page():
    # ============================================================
    # HEADER
    # ============================================================

    c_title, c_logout = st.columns([4, 1])

    with c_title:
        st.markdown(
            """
            <div style="margin-bottom:18px;">
                <div style="
                    font-size:2rem;
                    font-weight:900;
                    letter-spacing:-0.04em;
                    color:#111111;
                ">
                    EduVision Admin
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.95rem;
                    margin-top:5px;
                ">
                    Review and manage school registration requests.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_logout:
        if st.button(
            "Log Out",
            key="master_logout_btn",
            use_container_width=True
        ):
            go_portal()

    st.divider()

    # ============================================================
    # LOAD SCHOOLS
    # ============================================================

    schools = []

    if db:
        try:
            response = (
                db.table("schools")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )

            schools = response.data or []

        except Exception:
            try:
                response = (
                    db.table("schools")
                    .select("*")
                    .execute()
                )

                schools = response.data or []

            except Exception as error:
                st.error(
                    f"Error loading schools: {error}"
                )
                schools = []

    pending = [
        school
        for school in schools
        if school.get("approval_status") == "pending"
    ]

    approved = [
        school
        for school in schools
        if school.get("approval_status") == "approved"
    ]

    rejected = [
        school
        for school in schools
        if school.get("approval_status") == "rejected"
    ]

    # ============================================================
    # OVERVIEW
    # ============================================================

    st.markdown("### Overview")

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

    st.write("")

    # ============================================================
    # TABS
    # ============================================================

    tab1, tab2, tab3 = st.tabs([
        f"Pending ({len(pending)})",
        f"Approved ({len(approved)})",
        f"Rejected ({len(rejected)})",
    ])

    # ============================================================
    # PENDING SCHOOLS
    # ============================================================

    with tab1:

        st.markdown("### Pending Registrations")

        if not pending:

            st.info(
                "No school registrations are waiting for approval."
            )

        else:

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
                            color:#111111;
                            margin-bottom:12px;
                        ">
                            {school_name}
                        </div>

                        <div style="
                            display:grid;
                            grid-template-columns:
                                repeat(auto-fit, minmax(180px, 1fr));
                            gap:18px;
                        ">

                            <div>
                                <div style="
                                    color:#6b7280;
                                    font-size:0.75rem;
                                    font-weight:700;
                                    margin-bottom:4px;
                                ">
                                    SCHOOL ID
                                </div>

                                <div style="
                                    color:#111111;
                                    font-size:0.92rem;
                                    font-weight:700;
                                ">
                                    {school_id}
                                </div>
                            </div>

                            <div>
                                <div style="
                                    color:#6b7280;
                                    font-size:0.75rem;
                                    font-weight:700;
                                    margin-bottom:4px;
                                ">
                                    ADMIN ID
                                </div>

                                <div style="
                                    color:#111111;
                                    font-size:0.92rem;
                                    font-weight:700;
                                ">
                                    {admin_id}
                                </div>
                            </div>

                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c_approve, c_reject = st.columns(2)

                # ------------------------------------------------
                # APPROVE
                # ------------------------------------------------

                with c_approve:

                    if st.button(
                        "Approve",
                        key=f"app_{school_id}",
                        use_container_width=True
                    ):

                        try:

                            update_payload = {
                                "approval_status": "approved",
                                "approved_by":
                                    st.session_state.user_id,
                            }

                            try:
                                update_payload[
                                    "approved_at"
                                ] = datetime.now(
                                    timezone.utc
                                ).isoformat()

                            except Exception:
                                pass

                            (
                                db.table("schools")
                                .update(update_payload)
                                .eq(
                                    "school_id",
                                    school_id
                                )
                                .execute()
                            )

                            st.success(
                                f"{school_name} approved."
                            )

                            st.rerun()

                        except Exception:

                            # Fallback for databases without
                            # approved_at / approved_by columns.
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

                                st.success(
                                    f"{school_name} approved."
                                )

                                st.rerun()

                            except Exception as error:

                                st.error(
                                    f"Approval error: {error}"
                                )

                # ------------------------------------------------
                # REJECT
                # ------------------------------------------------

                with c_reject:

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

                            st.warning(
                                f"{school_name} rejected."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"Rejection error: {error}"
                            )

                st.write("")

    # ============================================================
    # APPROVED SCHOOLS
    # ============================================================

    with tab2:

        st.markdown("### Approved Schools")

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

                    "Approved At":
                        school.get(
                            "approved_at",
                            "N/A"
                        ),
                })

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )

    # ============================================================
    # REJECTED SCHOOLS
    # ============================================================

    with tab3:

        st.markdown("### Rejected Schools")

        if not rejected:

            st.info(
                "No rejected school registrations."
            )

        else:

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
                        padding:18px 20px;
                        margin:14px 0 10px;
                    ">
                        <div style="
                            font-size:1rem;
                            font-weight:800;
                            color:#111111;
                            margin-bottom:4px;
                        ">
                            {school_name}
                        </div>

                        <div style="
                            font-size:0.85rem;
                            color:#6b7280;
                        ">
                            School ID: {school_id}
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
# SCREEN 7 — MAIN SCHOOL APPLICATION (DASHBOARD & MODULES)
# ============================================================

def dashboard_page():
    students = load_students()
    attendance = load_attendance()

    # ------------------------------------------------------------
    # TODAY'S ATTENDANCE
    # ------------------------------------------------------------

    today_str = datetime.now().strftime("%Y-%m-%d")

    present_today = 0
    late_today = 0
    absent_today = 0

    if not attendance.empty and "attendance_date" in attendance.columns:

        today_rows = attendance[
            attendance["attendance_date"].astype(str) == today_str
        ]

        if "status" in today_rows.columns:

            present_today = len(
                today_rows[today_rows["status"] == "Present"]
            )

            late_today = len(
                today_rows[today_rows["status"] == "Late"]
            )

            absent_today = len(
                today_rows[today_rows["status"] == "Absent"]
            )

    total_students = len(students)

    if total_students > 0:
        attendance_percentage = round(
            (present_today / total_students) * 100,
            1
        )
    else:
        attendance_percentage = 0.0

    # ------------------------------------------------------------
    # GREETING
    # ------------------------------------------------------------

    current_hour = datetime.now().hour

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

    # ------------------------------------------------------------
    # SIMPLE HEADER
    # ------------------------------------------------------------

    st.markdown(
        f"""
        <div style="margin-bottom:32px;">

            <div style="
                font-size:2.2rem;
                font-weight:900;
                letter-spacing:-0.045em;
                color:#111111;
                margin-bottom:6px;
            ">
                {greeting}, {user_display}
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
            ">
                {st.session_state.school_name}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # OVERVIEW
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="
            font-size:1.15rem;
            font-weight:850;
            color:#111111;
            margin-bottom:14px;
        ">
            Today's Overview
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)

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

    # ------------------------------------------------------------
    # SMALL ATTENDANCE SUMMARY
    # ------------------------------------------------------------

    st.write("")

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:20px 24px;
            display:flex;
            gap:40px;
            flex-wrap:wrap;
            margin-bottom:34px;
        ">

            <div>
                <div style="
                    font-size:0.78rem;
                    color:#6b7280;
                    margin-bottom:4px;
                ">
                    PRESENT
                </div>

                <div style="
                    font-size:1.35rem;
                    font-weight:850;
                    color:#111111;
                ">
                    {present_today}
                </div>
            </div>

            <div>
                <div style="
                    font-size:0.78rem;
                    color:#6b7280;
                    margin-bottom:4px;
                ">
                    LATE
                </div>

                <div style="
                    font-size:1.35rem;
                    font-weight:850;
                    color:#111111;
                ">
                    {late_today}
                </div>
            </div>

            <div>
                <div style="
                    font-size:0.78rem;
                    color:#6b7280;
                    margin-bottom:4px;
                ">
                    ABSENT
                </div>

                <div style="
                    font-size:1.35rem;
                    font-weight:850;
                    color:#111111;
                ">
                    {absent_today}
                </div>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # QUICK ACTIONS
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="
            font-size:1.15rem;
            font-weight:850;
            color:#111111;
            margin-bottom:14px;
        ">
            Quick Actions
        </div>
        """,
        unsafe_allow_html=True,
    )

    action1, action2 = st.columns(2)

    # SMART ATTENDANCE
    with action1:

        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:24px;
                min-height:135px;
            ">

                <div style="
                    font-size:1.2rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:8px;
                ">
                    Smart Attendance
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.9rem;
                    line-height:1.5;
                ">
                    Take and review classroom attendance.
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

            st.session_state.nav_page = "📷 Smart Attendance"
            st.session_state["sidebar_nav_radio"] = (
                "📷 Smart Attendance"
            )

            st.rerun()

    # SMART OCCUPANCY
    with action2:

        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:24px;
                min-height:135px;
            ">

                <div style="
                    font-size:1.2rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:8px;
                ">
                    Smart Occupancy
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.9rem;
                    line-height:1.5;
                ">
                    View classroom occupancy and room status.
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

            st.session_state.nav_page = "👥 Smart Occupancy"
            st.session_state["sidebar_nav_radio"] = (
                "👥 Smart Occupancy"
            )

            st.rerun()

# ============================================================
# SUBPAGE: STUDENTS MANAGEMENT
# ============================================================

def students_page():
    is_admin = st.session_state.role == "School Admin"
    is_teacher = st.session_state.role == "Teacher"

    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    if is_admin:
        page_title = "Students"
        page_subtitle = "Review registrations and manage your school roster."
    else:
        page_title = "Students"
        page_subtitle = "View students and submit new registrations."

    st.markdown(
        f"""
        <div style="margin-bottom:28px;">
            <div style="
                font-size:2rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                {page_title}
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
                margin-top:5px;
            ">
                {page_subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    students = load_students()

    # ------------------------------------------------------------
    # STUDENT STATUS
    # ------------------------------------------------------------

    if students.empty or "status" not in students.columns:

        pending_students = pd.DataFrame()
        active_students = students.copy()
        declined_students = pd.DataFrame()

    else:

        normalized_status = (
            students["status"]
            .fillna("Active")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        pending_students = students[
            normalized_status == "pending"
        ].copy()

        declined_students = students[
            normalized_status == "declined"
        ].copy()

        active_students = students[
            ~normalized_status.isin(
                ["pending", "declined"]
            )
        ].copy()

    # ------------------------------------------------------------
    # SIMPLE METRICS
    # ------------------------------------------------------------

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

    st.write("")

    # ============================================================
    # TEACHER — REGISTER STUDENT
    # ============================================================

    if is_teacher:

        with st.expander(
            "Register New Student",
            expanded=False
        ):

            st.caption(
                "The School Admin must approve the student before they are added to the active roster."
            )

            c1, c2 = st.columns(2)

            with c1:

                student_id = st.text_input(
                    "Student ID",
                    placeholder="ST001",
                    key="teacher_reg_student_id"
                )

                student_name = st.text_input(
                    "Full Name",
                    placeholder="Student name",
                    key="teacher_reg_student_name"
                )

            with c2:

                class_name = st.text_input(
                    "Class / Grade",
                    placeholder="Class 10-A",
                    key="teacher_reg_student_class"
                )

                roll_no = st.text_input(
                    "Roll Number",
                    placeholder="Roll number",
                    key="teacher_reg_student_roll"
                )

            st.write("")

            if st.button(
                "Submit for Approval",
                key="teacher_submit_student_btn",
                use_container_width=True
            ):

                student_id = student_id.strip()
                student_name = student_name.strip()
                class_name = class_name.strip()
                roll_no = roll_no.strip()

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
                        "Please enter the student's class / grade."
                    )

                elif not db:

                    st.error(
                        "Database connection unavailable."
                    )

                else:

                    try:

                        db.table("students").insert({
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
                            f"{student_name} was submitted for approval."
                        )

                        st.rerun()

                    except Exception as error:

                        error_text = str(error).lower()

                        if (
                            "duplicate" in error_text
                            or "unique" in error_text
                            or "23505" in error_text
                        ):

                            st.error(
                                "That Student ID is already registered for this school."
                            )

                        else:

                            st.error(
                                f"Could not submit student registration: {error}"
                            )

    # ============================================================
    # ADMIN — PENDING APPROVALS
    # ============================================================

    if is_admin:

        st.markdown("### Pending Registrations")

        if pending_students.empty:

            st.info(
                "No student registrations are waiting for approval."
            )

        else:

            visible_cols = [
                c for c in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status"
                ]
                if c in pending_students.columns
            ]

            st.dataframe(
                pending_students[visible_cols],
                use_container_width=True,
                hide_index=True
            )

            pending_map = {
                f"{row.get('student_id')} — "
                f"{row.get('name')} — "
                f"{row.get('class_name', '')}":
                row.get("student_id")

                for _, row
                in pending_students.iterrows()
            }

            selected_pending = st.selectbox(
                "Select Student",
                list(pending_map.keys()),
                key="pending_student_review_select"
            )

            selected_pending_id = (
                pending_map[selected_pending]
            )

            approve_col, decline_col = st.columns(2)

            # APPROVE
            with approve_col:

                if st.button(
                    "Approve",
                    key="approve_student_btn",
                    use_container_width=True
                ):

                    try:

                        (
                            db.table("students")
                            .update({
                                "status": "Active"
                            })
                            .eq(
                                "school_id",
                                st.session_state.school_id
                            )
                            .eq(
                                "student_id",
                                selected_pending_id
                            )
                            .execute()
                        )

                        st.success(
                            "Student approved."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Could not approve student: {error}"
                        )

            # DECLINE
            with decline_col:

                if st.button(
                    "Decline",
                    key="decline_student_btn",
                    use_container_width=True
                ):

                    try:

                        (
                            db.table("students")
                            .update({
                                "status": "Declined"
                            })
                            .eq(
                                "school_id",
                                st.session_state.school_id
                            )
                            .eq(
                                "student_id",
                                selected_pending_id
                            )
                            .execute()
                        )

                        st.warning(
                            "Student registration declined."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Could not decline student: {error}"
                        )

        st.write("")

    # ============================================================
    # ACTIVE STUDENTS
    # ============================================================

    st.markdown("### Active Students")

    if active_students.empty:

        st.info(
            "No approved students are currently registered."
        )

    else:

        visible_cols = [
            c for c in [
                "student_id",
                "name",
                "class_name",
                "roll_no",
                "status"
            ]
            if c in active_students.columns
        ]

        st.dataframe(
            active_students[visible_cols],
            use_container_width=True,
            hide_index=True
        )

    # ============================================================
    # TEACHER — PENDING STUDENTS
    # ============================================================

    if is_teacher and not pending_students.empty:

        st.write("")

        with st.expander(
            f"Pending Registrations ({len(pending_students)})"
        ):

            visible_cols = [
                c for c in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status"
                ]
                if c in pending_students.columns
            ]

            st.dataframe(
                pending_students[visible_cols],
                use_container_width=True,
                hide_index=True
            )

    # ============================================================
    # ADMIN — DECLINED STUDENTS
    # ============================================================

    if is_admin and not declined_students.empty:

        st.write("")

        with st.expander(
            f"Declined Registrations ({len(declined_students)})"
        ):

            visible_cols = [
                c for c in [
                    "student_id",
                    "name",
                    "class_name",
                    "roll_no",
                    "status"
                ]
                if c in declined_students.columns
            ]

            st.dataframe(
                declined_students[visible_cols],
                use_container_width=True,
                hide_index=True
            )

    # ============================================================
    # ADMIN — REMOVE STUDENT
    # ============================================================

    if is_admin and not students.empty:

        st.divider()

        with st.expander(
            "Remove Student",
            expanded=False
        ):

            student_map = {
                f"{row.get('student_id')} — "
                f"{row.get('name')} — "
                f"{row.get('status', 'Active')}":
                row.get("student_id")

                for _, row
                in students.iterrows()
            }

            selected_student_label = st.selectbox(
                "Student",
                list(student_map.keys()),
                key="del_student_select"
            )

            if st.button(
                "Remove Student",
                key="del_student_btn",
                use_container_width=True
            ):

                sid = student_map[
                    selected_student_label
                ]

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

                    st.success(
                        "Student record removed."
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Could not delete student: {error}"
                    )

# ============================================================
# SUBPAGE: TEACHERS MANAGEMENT (ADMIN ONLY)
# ============================================================

def teachers_page():
    if st.session_state.role != "School Admin":
        st.error("School Admin access required.")
        return

    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="margin-bottom:28px;">
            <div style="
                font-size:2rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                Teachers
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
                margin-top:5px;
            ">
                Create and manage teacher accounts.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # LOAD TEACHERS
    # ------------------------------------------------------------

    teachers = []

    if db and st.session_state.school_id:
        try:
            response = (
                db.table("teachers")
                .select("*")
                .eq("school_id", st.session_state.school_id)
                .order("teacher_name")
                .execute()
            )

            teachers = response.data or []

        except Exception:
            try:
                response = (
                    db.table("teachers")
                    .select("*")
                    .eq("school_id", st.session_state.school_id)
                    .order("name")
                    .execute()
                )

                teachers = response.data or []

            except Exception:
                try:
                    response = (
                        db.table("teachers")
                        .select("*")
                        .eq("school_id", st.session_state.school_id)
                        .execute()
                    )

                    teachers = response.data or []

                except Exception as error:
                    st.error(
                        f"Error loading teachers: {error}"
                    )
                    teachers = []

    active_teachers = [
        teacher
        for teacher in teachers
        if teacher.get("enabled", True)
    ]

    # ------------------------------------------------------------
    # SIMPLE METRICS
    # ------------------------------------------------------------

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

    st.write("")

    # ============================================================
    # CREATE TEACHER
    # ============================================================

    with st.expander(
        "Create Teacher Account",
        expanded=False
    ):

        c1, c2 = st.columns(2)

        with c1:

            t_id = st.text_input(
                "Teacher ID",
                placeholder="TCH01",
                key="add_t_id"
            )

            t_name = st.text_input(
                "Teacher Name",
                placeholder="Teacher name",
                key="add_t_name"
            )

        with c2:

            t_pwd = st.text_input(
                "Temporary Password",
                type="password",
                placeholder="Minimum 6 characters",
                key="add_t_pwd"
            )

        st.write("")

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

            elif not db:

                st.error(
                    "Database connection unavailable."
                )

            else:

                try:

                    db.table("teachers").insert({
                        "school_id":
                            st.session_state.school_id,

                        "teacher_id":
                            t_id,

                        "teacher_name":
                            t_name,

                        "password_hash":
                            hash_password(t_pwd),

                        "enabled":
                            True,

                    }).execute()

                    st.success(
                        f"Teacher account for {t_name} created."
                    )

                    st.rerun()

                except Exception:

                    # Compatibility with older database
                    # versions that use "name"
                    try:

                        db.table("teachers").insert({
                            "school_id":
                                st.session_state.school_id,

                            "teacher_id":
                                t_id,

                            "name":
                                t_name,

                            "password_hash":
                                hash_password(t_pwd),

                            "enabled":
                                True,

                        }).execute()

                        st.success(
                            f"Teacher account for {t_name} created."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Could not create teacher: {error}"
                        )

    st.write("")

    # ============================================================
    # TEACHER LIST
    # ============================================================

    st.markdown("### Teacher Accounts")

    if not teachers:

        st.info(
            "No teacher accounts have been created yet."
        )

        return

    rows = []

    for teacher in teachers:

        name_val = (
            teacher.get("teacher_name")
            or teacher.get("name")
            or teacher.get("teacher_id", "")
        )

        rows.append({
            "Teacher ID":
                teacher.get("teacher_id", ""),

            "Name":
                name_val,

            "Status":
                "Enabled"
                if teacher.get("enabled", True)
                else "Disabled",
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True
    )

    # ============================================================
    # MANAGE TEACHER
    # ============================================================

    st.write("")

    with st.expander(
        "Manage Teacher",
        expanded=False
    ):

        t_options = {}

        for teacher in teachers:

            tid = teacher.get(
                "teacher_id",
                ""
            )

            tname = (
                teacher.get("teacher_name")
                or teacher.get("name")
                or tid
            )

            t_options[
                f"{tid} — {tname}"
            ] = teacher

        selected_t_label = st.selectbox(
            "Teacher",
            list(t_options.keys()),
            key="manage_t_select"
        )

        target_t = t_options[
            selected_t_label
        ]

        is_enabled = target_t.get(
            "enabled",
            True
        )

        c_toggle, c_delete = st.columns(2)

        # ENABLE / DISABLE
        with c_toggle:

            toggle_label = (
                "Disable Teacher"
                if is_enabled
                else "Enable Teacher"
            )

            if st.button(
                toggle_label,
                key="toggle_teacher_status",
                use_container_width=True
            ):

                try:

                    (
                        db.table("teachers")
                        .update({
                            "enabled": not is_enabled
                        })
                        .eq(
                            "school_id",
                            st.session_state.school_id
                        )
                        .eq(
                            "teacher_id",
                            target_t["teacher_id"]
                        )
                        .execute()
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        str(error)
                    )

        # DELETE
        with c_delete:

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
                            target_t["teacher_id"]
                        )
                        .execute()
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        str(error)
                    )
# ============================================================
# SUBPAGE: SMART ATTENDANCE (WEBRTC + MANUAL + HISTORY)
# ============================================================

def attendance_page():
    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="margin-bottom:28px;">
            <div style="
                font-size:2rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                Smart Attendance
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
                margin-top:5px;
            ">
                Take attendance and review attendance records.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    students = load_students()

    # ------------------------------------------------------------
    # TABS
    # ------------------------------------------------------------

    camera_tab, manual_tab, history_tab = st.tabs([
        "Camera",
        "Manual",
        "Records",
    ])

    # ============================================================
    # CAMERA ATTENDANCE
    # ============================================================

    with camera_tab:

        st.markdown(
            """
            <div style="margin:22px 0 18px;">
                <div style="
                    font-size:1.25rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:6px;
                ">
                    Camera Attendance
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.92rem;
                    line-height:1.5;
                ">
                    Start the camera to recognize registered students
                    and record attendance.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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

    # ============================================================
    # MANUAL ATTENDANCE
    # ============================================================

    with manual_tab:

        st.markdown(
            """
            <div style="margin:22px 0 18px;">
                <div style="
                    font-size:1.25rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:6px;
                ">
                    Manual Attendance
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.92rem;
                ">
                    Select a student and update their attendance.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if students.empty:

            st.info(
                "No students are currently registered."
            )

        else:

            col_m1, col_m2 = st.columns(2)

            with col_m1:

                student_opts = {
                    f"{row.get('student_id')} — {row.get('name')}": row
                    for _, row in students.iterrows()
                }

                selected_st = st.selectbox(
                    "Student",
                    list(student_opts.keys()),
                    key="man_student_select"
                )

            with col_m2:

                status_choice = st.selectbox(
                    "Status",
                    [
                        "Present",
                        "Late",
                        "Absent"
                    ],
                    key="man_status_select"
                )

            st.write("")

            if st.button(
                "Save Attendance",
                key="save_manual_att_btn",
                use_container_width=True
            ):

                st_data = student_opts[
                    selected_st
                ]

                now = datetime.now()

                att_date = now.strftime(
                    "%Y-%m-%d"
                )

                att_time = now.strftime(
                    "%H:%M:%S"
                )

                record = {
                    "school_id":
                        st.session_state.school_id,

                    "student_id":
                        st_data.get(
                            "student_id",
                            ""
                        ),

                    "name":
                        st_data.get(
                            "name",
                            ""
                        ),

                    "class_name":
                        st_data.get(
                            "class_name",
                            ""
                        ),

                    "attendance_date":
                        att_date,

                    "attendance_time":
                        att_time,

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
                            db.table("attendance")
                            .select("id")
                            .eq(
                                "school_id",
                                st.session_state.school_id
                            )
                            .eq(
                                "student_id",
                                record["student_id"]
                            )
                            .eq(
                                "attendance_date",
                                att_date
                            )
                            .execute()
                        )

                        # Update existing record instead
                        # of creating a duplicate.
                        if existing.data:

                            (
                                db.table("attendance")
                                .update({
                                    "name":
                                        record["name"],

                                    "class_name":
                                        record["class_name"],

                                    "attendance_time":
                                        att_time,

                                    "status":
                                        status_choice,
                                })
                                .eq(
                                    "id",
                                    existing.data[0]["id"]
                                )
                                .execute()
                            )

                        else:

                            (
                                db.table("attendance")
                                .insert(record)
                                .execute()
                            )

                        st.success(
                            f"{record['name']} marked as {status_choice}."
                        )

                    except Exception as error:

                        st.error(
                            f"Could not save attendance: {error}"
                        )

    # ============================================================
    # ATTENDANCE RECORDS
    # ============================================================

    with history_tab:

        st.markdown(
            """
            <div style="margin:22px 0 18px;">
                <div style="
                    font-size:1.25rem;
                    font-weight:850;
                    color:#111111;
                    margin-bottom:6px;
                ">
                    Attendance Records
                </div>

                <div style="
                    color:#6b7280;
                    font-size:0.92rem;
                ">
                    View recorded student attendance.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        att = load_attendance()

        if att.empty:

            st.info(
                "No attendance records yet."
            )

        else:

            cols = [
                column
                for column in [
                    "student_id",
                    "name",
                    "class_name",
                    "attendance_date",
                    "attendance_time",
                    "status",
                ]
                if column in att.columns
            ]

            st.dataframe(
                att[cols],
                use_container_width=True,
                hide_index=True
            )

# ============================================================
# SUBPAGE: SMART OCCUPANCY (YOLO11 VISION)
# ============================================================

def occupancy_page():
    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="margin-bottom:28px;">
            <div style="
                font-size:2rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                Smart Occupancy
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
                margin-top:5px;
            ">
                Monitor classroom occupancy in real time.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # CLASSROOM VIEW
    # ------------------------------------------------------------

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
                color:#111111;
                margin-bottom:6px;
            ">
                Live Classroom View
            </div>

            <div style="
                font-size:0.9rem;
                color:#6b7280;
                line-height:1.5;
            ">
                Start the camera to view the classroom
                and monitor the number of people present.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # OCCUPANCY SYSTEM
    # ------------------------------------------------------------

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
# SUBPAGE: REPORTS & ANALYTICS
# ============================================================

def reports_page():
    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="margin-bottom:28px;">
            <div style="
                font-size:2rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                Reports
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
                margin-top:5px;
            ">
                View attendance statistics and records.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------------

    students = load_students()
    attendance = load_attendance()

    total_records = len(attendance)
    present_count = 0

    if not attendance.empty and "status" in attendance.columns:
        present_count = len(
            attendance[
                attendance["status"] == "Present"
            ]
        )

    overall_pct = (
        round(
            (present_count / total_records) * 100,
            1
        )
        if total_records > 0
        else 0.0
    )

    # ------------------------------------------------------------
    # OVERVIEW
    # ------------------------------------------------------------

    st.markdown("### Overview")

    r1, r2, r3 = st.columns(3)

    with r1:
        st.metric(
            "Total Students",
            len(students)
        )

    with r2:
        st.metric(
            "Attendance Records",
            total_records
        )

    with r3:
        st.metric(
            "Present",
            present_count
        )

    st.write("")

    # ------------------------------------------------------------
    # ATTENDANCE RATE
    # ------------------------------------------------------------

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:24px;
            margin-bottom:30px;
        ">
            <div style="
                color:#6b7280;
                font-size:0.82rem;
                font-weight:700;
                margin-bottom:6px;
            ">
                OVERALL ATTENDANCE RATE
            </div>

            <div style="
                color:#111111;
                font-size:2.4rem;
                font-weight:900;
                letter-spacing:-0.04em;
            ">
                {overall_pct}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # ATTENDANCE RECORDS
    # ------------------------------------------------------------

    st.markdown("### Attendance Records")

    if attendance.empty:

        st.info(
            "No attendance records yet."
        )

    else:

        cols = [
            column
            for column in [
                "student_id",
                "name",
                "class_name",
                "attendance_date",
                "attendance_time",
                "status",
            ]
            if column in attendance.columns
        ]

        st.dataframe(
            attendance[cols],
            use_container_width=True,
            hide_index=True
        )

# ============================================================
# SUBPAGE: SETTINGS & WORKSPACE
# ============================================================

def settings_page():
    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    st.markdown(
        """
        <div style="margin-bottom:28px;">
            <div style="
                font-size:2rem;
                font-weight:900;
                letter-spacing:-0.04em;
                color:#111111;
            ">
                Settings
            </div>

            <div style="
                color:#6b7280;
                font-size:0.95rem;
                margin-top:5px;
            ">
                View your school and account information.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # SCHOOL INFORMATION
    # ------------------------------------------------------------

    st.markdown("### School Information")

    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:24px;
            margin-bottom:28px;
        ">
            <div style="
                display:grid;
                grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));
                gap:24px;
            ">

                <div>
                    <div style="
                        color:#6b7280;
                        font-size:0.78rem;
                        font-weight:700;
                        margin-bottom:5px;
                    ">
                        SCHOOL
                    </div>

                    <div style="
                        color:#111111;
                        font-size:1rem;
                        font-weight:750;
                    ">
                        {st.session_state.school_name}
                    </div>
                </div>

                <div>
                    <div style="
                        color:#6b7280;
                        font-size:0.78rem;
                        font-weight:700;
                        margin-bottom:5px;
                    ">
                        SCHOOL ID
                    </div>

                    <div style="
                        color:#111111;
                        font-size:1rem;
                        font-weight:750;
                    ">
                        {st.session_state.school_id}
                    </div>
                </div>

                <div>
                    <div style="
                        color:#6b7280;
                        font-size:0.78rem;
                        font-weight:700;
                        margin-bottom:5px;
                    ">
                        ROLE
                    </div>

                    <div style="
                        color:#111111;
                        font-size:1rem;
                        font-weight:750;
                    ">
                        {st.session_state.role}
                    </div>
                </div>

                <div>
                    <div style="
                        color:#6b7280;
                        font-size:0.78rem;
                        font-weight:700;
                        margin-bottom:5px;
                    ">
                        ACCOUNT
                    </div>

                    <div style="
                        color:#111111;
                        font-size:1rem;
                        font-weight:750;
                    ">
                        {st.session_state.user_name or st.session_state.user_id}
                    </div>
                </div>

            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # CONNECTION
    # ------------------------------------------------------------

    st.markdown("### Connection")

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
            padding:22px 24px;
        ">
            <div style="
                color:#6b7280;
                font-size:0.78rem;
                font-weight:700;
                margin-bottom:5px;
            ">
                DATABASE
            </div>

            <div style="
                color:#111111;
                font-size:1rem;
                font-weight:750;
            ">
                {connection_status}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
# ============================================================
# SCHOOL APPLICATION FRAME (SIDEBAR + ROUTING)
# ============================================================

def school_application():
    # ============================================================
    # SIDEBAR
    # ============================================================

    with st.sidebar:

        # --------------------------------------------------------
        # BRAND
        # --------------------------------------------------------

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
                    letter-spacing:-0.04em;
                    color:#111111;
                ">
                    EduVision
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --------------------------------------------------------
        # SCHOOL / ACCOUNT
        # --------------------------------------------------------

        st.markdown(
            f"""
            <div style="margin-bottom:18px;">

                <div style="
                    font-size:0.78rem;
                    color:#6b7280;
                    font-weight:700;
                    margin-bottom:4px;
                ">
                    SCHOOL
                </div>

                <div style="
                    font-size:0.95rem;
                    color:#111111;
                    font-weight:750;
                    margin-bottom:14px;
                ">
                    {st.session_state.school_name}
                </div>

                <div style="
                    font-size:0.78rem;
                    color:#6b7280;
                    font-weight:700;
                    margin-bottom:4px;
                ">
                    ACCOUNT
                </div>

                <div style="
                    font-size:0.9rem;
                    color:#111111;
                    font-weight:650;
                ">
                    {st.session_state.user_name or st.session_state.user_id}
                </div>

                <div style="
                    font-size:0.82rem;
                    color:#6b7280;
                    margin-top:2px;
                ">
                    {st.session_state.role}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # --------------------------------------------------------
        # NAVIGATION
        # --------------------------------------------------------

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

        # Convert old navigation values to the new clean names.
        old_nav_names = {
            "🏠 Dashboard": "Dashboard",
            "🎓 Students": "Students",
            "👨‍🏫 Teachers": "Teachers",
            "📷 Smart Attendance": "Smart Attendance",
            "👥 Smart Occupancy": "Smart Occupancy",
            "📊 Reports": "Reports",
            "⚙️ Settings": "Settings",
        }

        curr_page = st.session_state.get(
            "nav_page",
            "Dashboard"
        )

        curr_page = old_nav_names.get(
            curr_page,
            curr_page
        )

        if curr_page not in pages:
            curr_page = "Dashboard"

        curr_index = pages.index(curr_page)

        page = st.radio(
            "Navigation",
            pages,
            index=curr_index,
            key="sidebar_nav_radio"
        )

        st.session_state.nav_page = page

        st.divider()

        # --------------------------------------------------------
        # LOG OUT
        # --------------------------------------------------------

        if st.button(
            "Log Out",
            key="sidebar_logout_btn",
            use_container_width=True
        ):
            clear_login()
            st.session_state.screen = "school_portal"
            st.rerun()

    # ============================================================
    # PAGE ROUTING
    # ============================================================

    if page == "Dashboard":

        dashboard_page()

    elif page == "Students":

        students_page()

    elif page == "Teachers":

        if st.session_state.role == "School Admin":
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

        if st.session_state.role == "School Admin":
            settings_page()
        else:
            st.error(
                "School Admin access required."
            )
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

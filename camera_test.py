import streamlit as st
from streamlit_webrtc import webrtc_streamer

st.set_page_config(
    page_title="VisionED AI - Camera Test",
    page_icon="📷",
    layout="wide"
)

st.title("🎓 VisionED AI")
st.subheader("📷 Camera Test")

st.info("Press START below and allow your browser to access the camera.")

webrtc_streamer(
    key="visioned-camera",
    media_stream_constraints={
        "video": True,
        "audio": False
    }
)

st.success("Camera system loaded successfully.")
import cv2
import av
import streamlit as st

from streamlit_webrtc import (
    VideoProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)


# -------------------------------------------------
# PAGE SETTINGS
# -------------------------------------------------

st.set_page_config(
    page_title="VisionED AI - Face Detection",
    page_icon="🎓",
    layout="wide"
)


# -------------------------------------------------
# LOAD OPENCV FACE DETECTOR
# -------------------------------------------------

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)


# -------------------------------------------------
# VIDEO PROCESSOR
# -------------------------------------------------

class FaceDetector(VideoProcessorBase):

    def recv(self, frame):

        # Convert browser video frame to OpenCV image
        img = frame.to_ndarray(format="bgr24")

        # Convert to grayscale
        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        # Draw results
        for (x, y, w, h) in faces:

            cv2.rectangle(
                img,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3
            )

            cv2.putText(
                img,
                "FACE DETECTED",
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        # Face counter
        cv2.putText(
            img,
            f"Faces: {len(faces)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


# -------------------------------------------------
# WEBSITE
# -------------------------------------------------

st.title("🎓 VisionED AI")

st.subheader("AI Smart Attendance")

st.write(
    "This test detects faces using your browser camera "
    "and OpenCV."
)

st.info(
    "Press START and allow camera access."
)


# -------------------------------------------------
# WEB CAMERA
# -------------------------------------------------

webrtc_streamer(

    key="face-detection",

    mode=WebRtcMode.SENDRECV,

    video_processor_factory=FaceDetector,

    media_stream_constraints={
        "video": True,
        "audio": False
    },

    async_processing=True
)


st.caption(
    "VisionED AI • OpenCV Face Detection"
)
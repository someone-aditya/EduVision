import av
import cv2
import streamlit as st

from pathlib import Path
from ultralytics import YOLO
from streamlit_webrtc import (
    VideoProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
YOLO_MODEL_PATH = BASE_DIR / "yolo11n.pt"


# ============================================================
# LOAD YOLO
# ============================================================

@st.cache_resource
def load_model():

    if not YOLO_MODEL_PATH.exists():
        return None

    try:
        return YOLO(str(YOLO_MODEL_PATH))

    except Exception:
        return None


model = load_model()


# ============================================================
# VIDEO PROCESSOR
# ============================================================

class OccupancyProcessor(VideoProcessorBase):

    def __init__(self):

        self.people_count = 0


    def recv(self, frame):

        img = frame.to_ndarray(
            format="bgr24"
        )

        # ----------------------------------------
        # MODEL CHECK
        # ----------------------------------------

        if model is None:

            cv2.putText(
                img,
                "YOLO MODEL NOT READY",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            return av.VideoFrame.from_ndarray(
                img,
                format="bgr24"
            )


        # ----------------------------------------
        # YOLO PERSON DETECTION
        # ----------------------------------------

        try:

            results = model(
                img,
                classes=[0],
                conf=0.45,
                verbose=False
            )

        except Exception:

            cv2.putText(
                img,
                "DETECTION ERROR",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            return av.VideoFrame.from_ndarray(
                img,
                format="bgr24"
            )


        people_count = 0


        # ----------------------------------------
        # DRAW PEOPLE
        # ----------------------------------------

        for result in results:

            if result.boxes is None:
                continue

            boxes = (
                result.boxes
                .xyxy
                .cpu()
                .numpy()
            )

            people_count += len(boxes)

            for box in boxes:

                x1, y1, x2, y2 = map(
                    int,
                    box
                )

                # Person box
                cv2.rectangle(
                    img,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                # Person label
                cv2.putText(
                    img,
                    "PERSON",
                    (
                        x1,
                        max(
                            y1 - 10,
                            20
                        )
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )


        self.people_count = people_count


        # ----------------------------------------
        # PEOPLE COUNTER
        # ----------------------------------------

        cv2.rectangle(
            img,
            (10, 10),
            (310, 60),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            img,
            f"People Detected: {people_count}",
            (20, 43),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


        # ----------------------------------------
        # ROOM STATUS
        # ----------------------------------------

        if people_count == 0:

            status_text = "ROOM EMPTY"

            status_color = (
                0,
                165,
                255
            )

        else:

            status_text = (
                f"ROOM OCCUPIED: {people_count}"
            )

            status_color = (
                0,
                255,
                0
            )


        cv2.putText(
            img,
            status_text,
            (
                20,
                img.shape[0] - 25
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2
        )


        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


# ============================================================
# SMART OCCUPANCY PAGE
# ============================================================

def render_page():

    st.title(
        "👥 Smart Occupancy"
    )

    st.subheader(
        "AI Classroom Occupancy Monitoring"
    )

    st.write(
        "EduVision uses YOLO computer vision to detect "
        "people visible in the classroom camera."
    )

    st.info(
        "📷 Press START below and allow camera access."
    )


    # ----------------------------------------
    # CHECK YOLO MODEL
    # ----------------------------------------

    if not YOLO_MODEL_PATH.exists():

        st.error(
            "yolo11n.pt was not found."
        )

        st.caption(
            "Keep yolo11n.pt in the main EduVision folder."
        )

        return


    if model is None:

        st.error(
            "YOLO could not be loaded."
        )

        st.warning(
            "Check that ultralytics is installed."
        )

        return


    # ----------------------------------------
    # CAMERA
    # ----------------------------------------

    try:

        webrtc_streamer(

            key="eduvision-occupancy-camera",

            mode=WebRtcMode.SENDRECV,

            video_processor_factory=OccupancyProcessor,

            media_stream_constraints={
                "video": True,
                "audio": False
            },

            async_processing=True
        )

    except Exception as error:

        st.error(
            "Smart Occupancy camera could not start."
        )

        st.info(
            "Allow camera permission for EduVision "
            "and refresh the page."
        )

        st.code(
            str(error)
        )


    # ----------------------------------------
    # INFORMATION
    # ----------------------------------------

    st.divider()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "🤖 AI Model",
        "YOLO11"
    )

    c2.metric(
        "👤 Detection",
        "People"
    )

    c3.metric(
        "📡 Status",
        "Ready"
    )

    st.caption(
        "EduVision • AI-Powered Smart Classroom Management"
    )


# ============================================================
# RUN FILE DIRECTLY
# ============================================================

if __name__ == "__main__":

    st.set_page_config(
        page_title="EduVision - Smart Occupancy",
        page_icon="👥",
        layout="wide"
    )

    render_page()

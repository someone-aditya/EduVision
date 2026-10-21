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
        return YOLO(
            str(YOLO_MODEL_PATH)
        )

    except Exception as error:
        print(
            "YOLO loading error:",
            error
        )

        return None


model = load_model()


# ============================================================
# VIDEO PROCESSOR
# ============================================================

class OccupancyProcessor(
    VideoProcessorBase
):

    def recv(
        self,
        frame
    ):

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

            return (
                av.VideoFrame
                .from_ndarray(
                    img,
                    format="bgr24"
                )
            )


        # ----------------------------------------
        # PERSON DETECTION
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

            return (
                av.VideoFrame
                .from_ndarray(
                    img,
                    format="bgr24"
                )
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

            people_count += len(
                boxes
            )

            for box in boxes:

                x1, y1, x2, y2 = map(
                    int,
                    box
                )

                # Green person box
                cv2.rectangle(
                    img,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                # PERSON text
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


        # ----------------------------------------
        # COUNTER
        # ----------------------------------------

        cv2.rectangle(
            img,
            (10, 10),
            (320, 60),
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

            status_text = (
                "ROOM EMPTY"
            )

            status_color = (
                0,
                165,
                255
            )

        else:

            status_text = (
                f"ROOM OCCUPIED: "
                f"{people_count}"
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


        return (
            av.VideoFrame
            .from_ndarray(
                img,
                format="bgr24"
            )
        )


# ============================================================
# SMART OCCUPANCY PAGE
# ============================================================

def render_page():

    st.subheader(
        "🤖 AI Classroom Occupancy"
    )

    st.write(
        "EduVision uses YOLO AI computer vision "
        "to detect and count people visible in "
        "the classroom camera."
    )

    st.info(
        "📷 Press START and allow camera access."
    )


    # ----------------------------------------
    # MODEL FILE CHECK
    # ----------------------------------------

    if not YOLO_MODEL_PATH.exists():

        st.error(
            "yolo11n.pt was not found."
        )

        st.caption(
            "Keep yolo11n.pt in the main "
            "EduVision folder."
        )

        return


    # ----------------------------------------
    # MODEL CHECK
    # ----------------------------------------

    if model is None:

        st.error(
            "YOLO could not be loaded."
        )

        st.warning(
            "Check that ultralytics is "
            "installed correctly."
        )

        return


    # ----------------------------------------
    # CAMERA
    # ----------------------------------------

    try:

        webrtc_streamer(

            key="eduvision-occupancy-camera",

            mode=WebRtcMode.SENDRECV,

            video_processor_factory=(
                OccupancyProcessor
            ),

            media_stream_constraints={
                "video": True,
                "audio": False
            },

            async_processing=True
        )

    except Exception as error:

        st.error(
            "Smart Occupancy camera "
            "could not start."
        )

        st.info(
            "Allow camera permission "
            "and refresh EduVision."
        )

        st.code(
            str(error)
        )


    # ----------------------------------------
    # DETAILS
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
        "📡 System",
        "Ready"
    )

    st.caption(
        "EduVision • AI-Powered "
        "Smart Classroom Management"
    )


# ============================================================
# RUN DIRECTLY FOR TESTING
# ============================================================

if __name__ == "__main__":

    st.set_page_config(
        page_title=(
            "EduVision - Smart Occupancy"
        ),
        page_icon="👥",
        layout="wide"
    )

    st.title(
        "🎓 EduVision"
    )

    render_page()

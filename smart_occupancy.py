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

    # --------------------------------------------------------
    # INFORMATION
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            background:#ffffff;
            border:1px solid #dedede;
            border-radius:8px;
            padding:20px;
            margin-bottom:20px;
        ">
            <div style="
                font-size:1.05rem;
                font-weight:800;
                color:#111111;
                margin-bottom:6px;
            ">
                Classroom Monitoring
            </div>

            <div style="
                color:#6b7280;
                font-size:0.9rem;
                line-height:1.5;
            ">
                Use the classroom camera to monitor
                the number of people currently visible.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # MODEL FILE CHECK
    # --------------------------------------------------------

    if not YOLO_MODEL_PATH.exists():

        st.error(
            "Classroom monitoring is currently unavailable."
        )

        return

    # --------------------------------------------------------
    # MODEL CHECK
    # --------------------------------------------------------

    if model is None:

        st.error(
            "Classroom monitoring could not be started."
        )

        return

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    st.markdown("### Camera")

    st.caption(
        "Press START below and allow camera access."
    )

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
            "Camera could not start."
        )

        st.info(
            "Check your browser camera permission and try again."
        )

        st.code(
            str(error)
        )

    # --------------------------------------------------------
    # INFORMATION
    # --------------------------------------------------------

    st.divider()

    st.markdown("### Classroom Status")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:18px;
            ">
                <div style="
                    color:#6b7280;
                    font-size:0.8rem;
                    font-weight:700;
                    margin-bottom:5px;
                ">
                    MONITORING
                </div>

                <div style="
                    color:#111111;
                    font-size:1.15rem;
                    font-weight:800;
                ">
                    People
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div style="
                background:#ffffff;
                border:1px solid #dedede;
                border-radius:8px;
                padding:18px;
            ">
                <div style="
                    color:#6b7280;
                    font-size:0.8rem;
                    font-weight:700;
                    margin-bottom:5px;
                ">
                    STATUS
                </div>

                <div style="
                    color:#111111;
                    font-size:1.15rem;
                    font-weight:800;
                ">
                    Ready
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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

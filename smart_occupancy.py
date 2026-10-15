import av
import cv2
import streamlit as st

from ultralytics import YOLO
from streamlit_webrtc import (
    VideoProcessorBase,
    WebRtcMode,
    webrtc_streamer,
)


# ------------------------------------------
# LOAD YOLO
# ------------------------------------------

@st.cache_resource
def load_model():
    return YOLO("yolo11n.pt")


model = load_model()


# ------------------------------------------
# VIDEO PROCESSOR
# ------------------------------------------

class OccupancyProcessor(VideoProcessorBase):

    def recv(self, frame):

        img = frame.to_ndarray(format="bgr24")

        # Detect people
        results = model(
            img,
            classes=[0],      # 0 = person
            conf=0.45,
            verbose=False
        )

        people_count = 0

        for result in results:

            if result.boxes is not None:

                boxes = result.boxes.xyxy.cpu().numpy()

                people_count = len(boxes)

                for box in boxes:

                    x1, y1, x2, y2 = map(int, box)

                    # Person box
                    cv2.rectangle(
                        img,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        img,
                        "PERSON",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

        # Current number visible
        cv2.putText(
            img,
            f"People Detected: {people_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


# ------------------------------------------
# EDVISION WEBSITE
# ------------------------------------------

st.set_page_config(
    page_title="EduVision - Smart Occupancy",
    page_icon="🚪",
    layout="wide"
)

st.title("🎓 EduVision")

st.subheader("🚪 Smart Room Occupancy")

st.write(
    "EduVision uses AI computer vision to detect "
    "people in the camera feed and monitor classroom occupancy."
)

st.info(
    "Press START and allow camera access."
)


# ------------------------------------------
# CAMERA
# ------------------------------------------

webrtc_streamer(
    key="eduvision-occupancy",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=OccupancyProcessor,
    media_stream_constraints={
        "video": True,
        "audio": False
    },
    async_processing=True
)

st.caption(
    "EduVision • AI-Powered Smart Classroom Management"
)

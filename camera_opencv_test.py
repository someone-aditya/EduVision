import cv2

print("OpenCV version:", cv2.__version__)
print("\nSearching for webcam...")

working_camera = None

for index in range(5):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if cap.isOpened():
        ret, frame = cap.read()

        if ret:
            print(f"Camera {index}: WORKING")
            working_camera = index
            cap.release()
            break

    print(f"Camera {index}: Not available")
    cap.release()

if working_camera is None:
    print("\nNo working camera found.")
else:
    print(f"\nUse camera index: {working_camera}")
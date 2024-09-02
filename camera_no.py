# from pygrabber.dshow_graph import FilterGraph

# def get_available_cameras() :

#     devices = FilterGraph().get_input_devices()

#     available_cameras = {}

#     for device_index, device_name in enumerate(devices):
#         available_cameras[device_index] = device_name

#     return available_cameras

# print(get_available_cameras())


import cv2

# Attempt to open each camera and display its feed
for i in range(3):  # Assuming you have up to 3 cameras, adjust as needed
    cap = cv2.VideoCapture(i)
    if not cap.isOpened():
        print(f"Camera {i} not found")
    else:
        print(f"Camera {i} found")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow(f"Camera {i}", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

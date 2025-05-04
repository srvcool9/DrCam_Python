from flask import Flask, render_template, Response, request
from pygrabber.dshow_graph import FilterGraph
import cv2
import threading
import logging
from src import app  # your Flask instance
from src.db_config.database_service import DatabaseService
from src.models.profile_model import ProfileModel
from src.db_config import database_service

logging.basicConfig(level=logging.DEBUG)
db=DatabaseService()


recording = False
out = None
zoom = 1.0
brightness = 0
lock = threading.Lock()
cam = None


def initialize_camera():
    global cam
    graph = FilterGraph()
    devices = graph.get_input_devices()
    logging.debug(f"Available Cameras: {devices}")

    target_device_name = None

    for name in devices:
        if "H1600 Cam" or "VMware Virtual USB Video Device" in name:
            target_device_name = name
            break

    if not target_device_name:
        logging.warning("No compatible camera (H1600 Cam) found.")
        cam = None
        return

    # Get device index from pygrabber
    index = devices.index(target_device_name)
    logging.info(f"Using camera: {target_device_name} at index {index}")

    # Open camera with DirectShow backend
    cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cam.isOpened():
        logging.error("Failed to open selected camera.")
        cam = None


def apply_zoom(frame, zoom_factor):
    if zoom_factor == 1.0:
        return frame
    h, w = frame.shape[:2]
    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
    y1 = (h - new_h) // 2
    x1 = (w - new_w) // 2
    cropped = frame[y1:y1 + new_h, x1:x1 + new_w]
    return cv2.resize(cropped, (w, h))


def generate_frames():
    global cam, recording, out, zoom, brightness

    if cam is None or not cam.isOpened():
        yield (b'--frame\r\n'
               b'Content-Type: text/plain\r\n\r\nNo compatible camera (H1600 Cam) found.\r\n\r\n')
        return

    while True:
        with lock:
            success, frame = cam.read()
            if not success:
                break

            frame = apply_zoom(frame, zoom)
            frame = cv2.convertScaleAbs(frame, alpha=1, beta=brightness)

            if recording and out:
                out.write(frame)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/camera')
def camera():
    profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    if (profile):
        agency_name = profile.agency_name
    return render_template('camera.html',agency_name=agency_name)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/set_zoom', methods=['POST'])
def set_zoom():
    global zoom
    zoom = float(request.form['zoom'])
    return ('', 204)


@app.route('/set_brightness', methods=['POST'])
def set_brightness():
    global brightness
    brightness = int(request.form['brightness'])
    return ('', 204)


@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording, out, cam
    with lock:
        if cam and cam.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter('recording.avi', fourcc, 20.0, (width, height))
            recording = True
    return ('', 204)


@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording, out
    with lock:
        recording = False
        if out:
            out.release()
            out = None
    return ('', 204)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    global cam
    with lock:
        if cam:
            cam.release()
    return ('', 204)

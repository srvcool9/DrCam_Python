
from src import app
from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading


camera = cv2.VideoCapture(0)
recording = False
out = None
zoom = 1.0
brightness = 0

lock = threading.Lock()

def apply_zoom(frame, zoom_factor):
    if zoom_factor == 1.0:
        return frame
    h, w = frame.shape[:2]
    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
    y1 = (h - new_h) // 2
    x1 = (w - new_w) // 2
    cropped = frame[y1:y1+new_h, x1:x1+new_w]
    return cv2.resize(cropped, (w, h))

def generate_frames():
    global camera, recording, out, zoom, brightness

    while True:
        with lock:
            if not camera.isOpened():
                break
            success, frame = camera.read()
            if not success:
                break

            # Apply zoom and brightness
            frame = apply_zoom(frame, zoom)
            frame = cv2.convertScaleAbs(frame, alpha=1, beta=brightness)

            # Write if recording
            if recording and out:
                out.write(frame)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/camera')
def camera():
    return render_template('camera.html')

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
    global recording, out, camera
    with lock:
        if camera and camera.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
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
    global camera
    with lock:
        if camera:
            camera.release()
    return ('', 204)

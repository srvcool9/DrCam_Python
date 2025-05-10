from flask import Flask, render_template, Response, request, send_from_directory, jsonify
from plyer import notification
from pygrabber.dshow_graph import FilterGraph
import cv2
import threading
import logging
import os
from datetime import datetime
from src import app  # your Flask instance
from src.db_config.database_service import DatabaseService
from src.models.patient_history_model import PatientHistoryModel
from src.models.patient_model import PatientsModel
from src.models.profile_model import ProfileModel

logging.basicConfig(level=logging.DEBUG)
db = DatabaseService()

recording = False
out = None
zoom = 1.0
brightness = 0
lock = threading.Lock()
cam = None

CAPTURE_DIR = 'static/captures'
os.makedirs(CAPTURE_DIR, exist_ok=True)

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

    index = devices.index(target_device_name)
    logging.info(f"Using camera: {target_device_name} at index {index}")
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
    agency_name = profile.agency_name if profile and profile.agency_name else 'Mex Enterprise'
    return render_template('camera.html', agency_name=agency_name)

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
            out = cv2.VideoWriter(os.path.join(CAPTURE_DIR, 'recording.avi'), fourcc, 20.0, (width, height))
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

@app.route('/capture_photo', methods=['POST'])
def capture_photo():
    global cam
    with lock:
        if cam and cam.isOpened():
            ret, frame = cam.read()
            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"img_{timestamp}.jpg"
                path = os.path.join(CAPTURE_DIR, filename)
                cv2.imwrite(path, frame)
                return {'status': 'ok', 'filename': filename}
    return {'status': 'fail'}, 500

@app.route('/media')
def list_media():
    files = sorted(os.listdir(CAPTURE_DIR), reverse=True)
    files = [f for f in files if f.endswith(('.jpg', '.avi'))]
    return {'files': files}

@app.route('/captures/<path:filename>')
def get_file(filename):
    return send_from_directory(CAPTURE_DIR, filename)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global cam
    with lock:
        if cam:
            cam.release()
    return ('', 204)

@app.route('/save_patient', methods=['POST'])
def save_patient():
    data = request.form
    appointmentId = data.get('id')
    patientName = data.get('patient_name')
    gender = data.get('gender')
    dateOfBirth = data.get('dob')
    phone = data.get('phone')
    address = data.get('address')

    exists=db.query_by_column("patients","phone",phone,PatientsModel.from_map)
    if(exists):
      patient= PatientsModel(exists.patient_id,appointmentId,patientName,gender,dateOfBirth,phone, address)
      db.updatePatient(patient)
      save_patient_history(appointmentId,exists.patient_id)
      notification.notify(
          title='New Notification',
          message='Patient details updated successfully!',
          app_name='',
          timeout=5
      )
    else:
        patient = PatientsModel(None, appointmentId, patientName, gender,dateOfBirth, phone, address)
        persist_id= db.insert(patient)
        patients= db.query_by_column("patients","patientId",persist_id,PatientsModel.from_map)
        if(patients):
            save_patient_history(patients.appointment_id,patients.patient_id)
            print(patients)
        notification.notify(
            title='New Notification',
            message='Patient details registered successfully!',
            app_name='',
            timeout=5
        )

    return jsonify({'status': 'success'})

def save_patient_history(appointment_id,patient_id):
    patient_history = PatientHistoryModel(None,appointment_id, patient_id,datetime.now().strftime('%Y-%m-%d'),datetime.now().strftime('%Y-%m-%d'))
    db.insert(patient_history)
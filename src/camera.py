import ctypes
import shutil
from pathlib import Path

from flask import Flask,send_file, render_template, Response, request, send_from_directory, jsonify
from plyer import notification
from pygrabber.dshow_graph import FilterGraph
import cv2
import threading
import logging
import os
from datetime import datetime
from src import app  # your Flask instance
from src.contants.queries import Queries
from src.db_config.database_service import DatabaseService
from src.models.patient_history_model import PatientHistoryModel
from src.models.patient_images_model import PatientImagesModel
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
images_list = []
clicked_images= []

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
    return render_template('camera.html', agency_name=agency_name,images=images_list)

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


@app.route('/capture_photo/<string:public_flag>/<string:patient_name>', methods=['POST'])
def capture_photo(public_flag,patient_name):
    global cam
    global images_list
    with lock:
        if cam and cam.isOpened():
            ret, frame = cam.read()
            if ret:
                timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S%f")
                filename = f"img_{timestamp}.jpg"

                if public_flag.lower() == 'true':
                    path = os.path.join(_get_documents_path(), 'DrCamApp', 'public','images')
                    clicked_images.append(path+'/'+filename)
                else:
                    path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'images')
                    images_list.append(filename)
                    clicked_images.append(path + '/' + filename)

                os.makedirs(path, exist_ok=True)
                cv2.imwrite(path+'/'+filename, frame)
                return {'status': 'ok', 'filename': filename}

    return {'status': 'fail'}, 500

@app.route('/media')
def list_media():
    global clicked_images
    return {'files': clicked_images}

@app.route('/temp_images/<filename>')
def temp_images(filename):
    temp_dir = os.path.join(app.root_path, 'temp_images', 'captures')
    return send_from_directory(temp_dir, filename)


@app.route('/get_image')
def get_image():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return "Image not found", 404
    return send_file(path, mimetype='image/jpeg')

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
      save_patient_history(patient)
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
            save_patient_history(patients)
            print(patients)
        notification.notify(
            title='New Notification',
            message='Patient details registered successfully!',
            app_name='',
            timeout=5
        )

    return jsonify({'status': 'success'})

def save_patient_history(patient):
    patient_history = PatientHistoryModel(
        None,
        patient.appointment_id,
        patient.patient_id,
        datetime.now().strftime('%Y-%m-%d'),
        datetime.now().strftime('%Y-%m-%d')
    )
    saved_history_id = db.insert(patient_history)

    if images_list:
        image_filenames = list(images_list)  # copy list before clearing

        src_path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'images')
        dest_path = os.path.join(_get_documents_path(), 'DrCamApp', patient.patient_name, 'images')
        os.makedirs(dest_path, exist_ok=True)

        for filename in image_filenames:
            temp_path = os.path.join(src_path, filename)
            dest_file_path = os.path.join(dest_path, filename)
            try:
                if os.path.exists(temp_path):
                    shutil.move(temp_path, dest_file_path)
            except Exception as e:
                print(f"Failed to move {filename}: {e}")

        # Create DB entries
        patient_images = [
            PatientImagesModel(None, patient.patient_id, saved_history_id, filename, datetime.now())
            for filename in image_filenames
        ]
        db.bulk_insert(patient_images)
        images_list.clear()


@app.route('/get_patient/<string:patient_id>')
def get_patient(patient_id):
    patient = db.query_by_column("patients","patientId",patient_id,PatientsModel.from_map)
    if patient:
        get_all_patient_images(patient_id, patient.patient_name)
        return jsonify({
            'status': 'success',
            'patient': {
                'id': patient.appointment_id,
                'patient_name': patient.patient_name,
                'gender': patient.gender,
                'dob': str(patient.date_of_birth),
                'phone': patient.phone,
                'address': patient.address
            },
            'images': images_list
        })

    return jsonify({'status': 'error', 'message': 'Patient not found'})

def _get_documents_path():
        """Get Windows 'Documents' folder using SHGetKnownFolderPath"""
        try:
            from ctypes import windll, POINTER, byref
            from uuid import UUID
            SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.POINTER(ctypes.c_byte), ctypes.wintypes.DWORD,
                ctypes.wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
            ]
            FOLDERID_Documents = UUID('{FDD39AD0-238F-46AF-ADB4-6C85480369C7}')
            path_ptr = ctypes.c_wchar_p()
            SHGetKnownFolderPath(
                (ctypes.c_byte * 16).from_buffer_copy(FOLDERID_Documents.bytes_le),
                0, 0, byref(path_ptr)
            )
            return Path(path_ptr.value)
        except Exception as e:
            print("Error getting Documents path, falling back to home/Documents:", e)
            return Path.home() / "Documents"
def get_all_patient_images(patient_id, patient_name):
    global images_list
    images_list.clear()

    # Ensure temp_images/captures exists
    temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
    os.makedirs(temp_path, exist_ok=True)

    # Get DB image filenames
    patient_images = db.custom_query(
        Queries.GET_ALL_PATIENT_IMAGES,
        from_map=lambda row: row["imageBase64"],
        args=[patient_id]
    )

    # Path where actual images are stored
    image_path = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'images')

    for filename in patient_images:
        src_file = os.path.join(image_path, filename)
        dst_file = os.path.join(temp_path, filename)
        try:
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                images_list.append(filename)  # store just filename for `url_for`
        except Exception as e:
            print(f"Failed to copy image: {e}")

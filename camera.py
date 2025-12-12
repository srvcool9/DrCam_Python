import base64
import ctypes
import shutil
from pathlib import Path
import re

import ffmpeg
from PIL import Image
from io import BytesIO
import time

from _ctypes import byref
from flask import Flask,send_file, render_template, Response, request, send_from_directory, jsonify
from plyer import notification

import cv2
import threading
import logging
import os
from flask import abort

from datetime import datetime

# from win10toast import ToastNotifier

from contants.queries import Queries
from db_config.database_service import DatabaseService
from models.camera_setting import CameraSettingsModel
from models.patient_history_model import PatientHistoryModel
from models.patient_images_model import PatientImagesModel
from models.patient_model import PatientsModel
from models.patient_videos_model import PatientVideosModel
from models.profile_model import ProfileModel

logging.basicConfig(level=logging.DEBUG)
db = DatabaseService()
# toaster = ToastNotifier()
patientData = PatientsModel()
recording_is_flipped = False
recording_rotation_angle = 0
recording = False
out = None
zoom = 1.0
brightness = 0
lock = threading.Lock()
cam = None
contrast = 0
exposure = 0
white_balance = 0
frame_rate=0
width, height = 640, 480
rec_rotation_state=0
recording_with_thread = False

# CAPTURE_DIR = 'static/captures'
# os.makedirs(CAPTURE_DIR, exist_ok=True)

images_list = []
clicked_images= []
videos_path_list=[]
videos_file_names=[]
prefilled_image_list=[]
prefilled_videos_list=[]

import platform
if platform.system() == "Windows":
    from ctypes import windll
    from pygrabber.dshow_graph import FilterGraph



def register_camera(app):

 def video_recording_loop():
     global cam, recording, out, recording_is_flipped, recording_rotation_angle, recording_with_thread

     setting = load_camera_settings()
     if setting:
         recording_rotation_angle=setting.get('rotation_angle')
     # Wait until camera is ready and out has been created by start_recording
     if cam is None or not cam.isOpened():
         print("No camera available for recording.")
         return

     # Ensure the writer (out) has been created by start_recording
     wait_start = time.time()
     while out is None and time.time() - wait_start < 3.0:
         time.sleep(0.01)
     if out is None:
         print("VideoWriter not initialized by start_recording(), aborting recording loop.")
         return

     recording_with_thread = True
     # Attempt to find FPS (fall back to 20.0)
     fps = cam.get(cv2.CAP_PROP_FPS) or 20.0
     frame_interval = 1.0 / fps
     last_time = time.time()

     try:
         while recording and cam.isOpened():
             ret, frame = cam.read()
             if not ret:
                 break

             # Apply flip if needed
             if recording_is_flipped:
                 frame = cv2.flip(frame, 1)

             # # Apply rotation if needed
             if recording_rotation_angle == 90:
                 frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
             elif recording_rotation_angle == 180:
                 frame = cv2.rotate(frame, cv2.ROTATE_180)
             elif recording_rotation_angle == 270:
                 frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

             # Ensure frame matches writer size (some backends require exact dimensions)
             # out expects (width, height) that were set in start_recording()
             try:
                 out.write(frame)
             except Exception as e:
                 print("Failed to write frame to out:", e)
                 # Try resizing to expected size if out was created with a different shape
                 # But we don't have direct access to out's expected dims here. Optionally handle if necessary.

             # Maintain timing (reduce busy loop)
             now = time.time()
             elapsed = now - last_time
             if elapsed < frame_interval:
                 time.sleep(frame_interval - elapsed)
             last_time = time.time()
     finally:
         # Release writer here if still set by start_recording
         try:
             if out:
                 out.release()
         except Exception:
             pass
         out = None
         recording_with_thread = False
         print("Recording stopped (thread exit).")

 def initialize_camera():
        import time
        global cam, exposure, white_balance, zoom, brightness, contrast, frame_rate
        # Initialize to None in case no camera is found or initialization fails
        cam = None
        exposure = None
        white_balance = None

        # Check if FilterGraph is defined before using it
        try:
            graph = FilterGraph()
            devices = graph.get_input_devices()
            logging.debug(f"Available Cameras: {devices}")
        except NameError:
            logging.error("FilterGraph is not defined.  Cannot list available devices.")
            return

        target_device_name = None

        # Prioritize "H1600 Cam"
        for name in devices:
          if "H1600 Cam" in name:
            target_device_name = name
            break

        # If H1600 cam is not found, check for "VMware Virtual USB Video Device"
        if target_device_name is None:
            for name in devices:
                if "HP HD Camera" in name:
                    target_device_name = name
                    break

        if not target_device_name:
            logging.warning("No compatible camera (H1600 Cam or VMware Virtual USB Video Device) found.")
            return

        try:
            index = devices.index(target_device_name)
        except ValueError:
            logging.error(f"Camera '{target_device_name}' not found in device list after initial detection.")
            return

        logging.info(f"Using camera: {target_device_name} at index {index}")
        cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)

        if not cam.isOpened():
            logging.error("Failed to open selected camera.")
            cam = None
            return

        setting = load_camera_settings()
        if setting:
            zoom = setting.get('zoom')
            brightness = setting.get('brightness')
            contrast = setting.get('contrast')
            exposure = setting.get('exposure')
            white_balance = setting.get('white_balance')
            frame_rate = setting.get('framerate')

            with lock:
                if cam:
                    time.sleep(0.5)
                    # exposure = cam.get(cv2.CAP_PROP_EXPOSURE)
                    # white_balance = cam.get(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U)
                    cam.set(cv2.CAP_PROP_EXPOSURE, exposure)
                    cam.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, white_balance)
        else:
            # If no saved settings, use defaults
            zoom = 1.0
            brightness = 0
            contrast = 0
            exposure = 0.0
            white_balance = 0.0
            frame_rate = 20.0

 def generate_frames():
     global cam, recording, out, zoom, brightness, contrast, recording_with_thread,recording_rotation_angle

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
             alpha = 1.0 + contrast / 100.0  # Contrast control
             beta = brightness
             frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
             setting = load_camera_settings()
             if setting:
                 recording_rotation_angle = setting.get('rotation_angle')

             if recording_rotation_angle == 90:
                 frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
             elif recording_rotation_angle == 180:
                 frame = cv2.rotate(frame, cv2.ROTATE_180)
             elif recording_rotation_angle == 270:
                 frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

             # If you are using a recording thread, don't write here (avoid double writes)
             if recording and out and not recording_with_thread:
                 try:
                     out.write(frame)
                 except Exception as e:
                     print("Warning: failed to write frame in generate_frames():", e)

             _, buffer = cv2.imencode('.jpg', frame)
             frame_bytes = buffer.tobytes()

         yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

 def apply_zoom(frame, zoom_factor):
    if zoom_factor == 1.0:
        return frame
    h, w = frame.shape[:2]
    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
    y1 = (h - new_h) // 2
    x1 = (w - new_w) // 2
    cropped = frame[y1:y1 + new_h, x1:x1 + new_w]
    return cv2.resize(cropped, (w, h))




 @app.route('/camera')
 def camera():
    initialize_camera()
    profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    agency_name = profile.agency_name if profile and profile.agency_name else 'Mex Enterprise'
    data = load_camera_settings()
    if data:
        setting = data
    else:
        setting = {
            'zoom': 1.0,
            'brightness': 0,
            'contrast': 0,
            'exposure': 0,
            'white_balance': 4500,
            'framerate': 20.0
        }

    return render_template('camera.html', agency_name=agency_name,images=images_list, zoom=setting.get('zoom'),
        brightness=setting.get('brightness'),
        contrast=setting.get('contrast'),
        exposure=setting.get('exposure'),
        white_balance=setting.get('white_balance'))

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

 @app.route('/set_contrast', methods=['POST'])
 def set_contrast():
     global contrast
     contrast = int(request.form['contrast'])
     return ('', 204)

 @app.route('/set_exposure', methods=['POST'])
 def set_exposure():
     global exposure, cam
     exposure = float(request.form['exposure'])
     with lock:
         if cam and cam.isOpened():
             cam.set(cv2.CAP_PROP_EXPOSURE, exposure)
     return ('', 204)

 @app.route('/set_white_balance', methods=['POST'])
 def set_white_balance():
     global white_balance, cam
     white_balance = float(request.form['white_balance'])
     with lock:
         if cam and cam.isOpened():
             cam.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, white_balance)
     return ('', 204)

 @app.route('/set_framerate', methods=['POST'])
 def set_framerate():
     global frame_rate
     try:
         frame_rate = float(request.form['framerate'])
         if frame_rate <= 0:
             frame_rate = 20.0
     except:
         frame_rate = 20.0
     return ('', 204)

 # ---- start_recording: create writer with rotated dimensions and start thread ----
 @app.route('/start_recording/<string:public_flag>/<string:patient_name>/<string:isFlipped>/<int:rotationAngle>',
            methods=['POST'])
 def start_recording(public_flag, patient_name, isFlipped, rotationAngle):
     global recording, out, cam, videos_path_list, videos_file_names
     global recording_is_flipped, recording_rotation_angle, recording_with_thread

     with lock:
         if cam and cam.isOpened():
             recording_is_flipped = (isFlipped.lower() == "true")
             setting = load_camera_settings()
             if setting:
                 recording_rotation_angle = setting.get('rotation_angle')
             logging.info(f"recording at angle: {recording_rotation_angle}")

             # Get original camera frame size
             orig_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
             orig_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

             # Adjust output dimensions if rotation is 90 or 270 (swap)
             if recording_rotation_angle in [90, 270, -90, -270]:
                 out_width, out_height = orig_height, orig_width
             else:
                 out_width, out_height = orig_width, orig_height

             fourcc = cv2.VideoWriter_fourcc(*'mp4v')

             timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S%f")
             filename = f"vid_{timestamp}.mp4"

             if public_flag.lower() == 'true':
                 path = os.path.join(_get_documents_path(), 'DrCamApp', 'public', 'videos')
                 full_path = os.path.join(path, filename)
                 videos_path_list.append(full_path)
             else:
                 path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'videos')
                 full_path = os.path.join(path, filename)
                 videos_file_names.append(filename)
                 videos_path_list.append(full_path)

             os.makedirs(path, exist_ok=True)

             # Ensure any previous writer is released first
             if out:
                 try:
                     out.release()
                 except Exception:
                     pass
                 out = None

             # Create writer here with correct (width, height) that matches frames after rotation
             out = cv2.VideoWriter(full_path, fourcc, 20.0, (out_width, out_height))

             recording = True
             # Start the recording thread (thread will use the 'out' created above)
             thread = threading.Thread(target=video_recording_loop, daemon=True)
             thread.start()
             print(
                 f"Recording started: {full_path}, flipped={recording_is_flipped}, rotation={recording_rotation_angle}")
     return ('', 204)

 # ---- stop_recording: ensure flags and writer are cleaned ----
 @app.route('/stop_recording', methods=['POST'])
 def stop_recording():
     global recording, out, videos_path_list
     global recording_is_flipped, recording_rotation_angle, recording_with_thread
     with lock:
         recording = False

         # Wait briefly for thread to finish and release writer
         wait_start = time.time()
         while recording_with_thread and time.time() - wait_start < 2.0:
             time.sleep(0.05)

         if out:
             try:
                 out.release()
             except Exception as e:
                 print("Error releasing writer on stop:", e)
             out = None
             print(" Recording stopped and writer released.")

         # Then convert last recorded video as you already do
         if videos_path_list:
             original_path = videos_path_list[-1]
             converted_path = original_path.replace('.mp4', '_converted.mp4')
             try:
                 ffmpeg.input(original_path).output(
                     converted_path,
                     vcodec='libx264',
                     movflags='faststart',
                     preset='ultrafast',
                     crf=23
                 ).run(overwrite_output=True)
                 print(f" Converted video saved to: {converted_path}")
             except Exception as e:
                 print(f"FFmpeg conversion failed: {e}")

     return ('', 204)

 @app.route('/get_captured_image/<string:patient_id>', methods=['GET'])
 def get_captured_images(patient_id):
     global images_list

     if not patient_id.strip() or patient_id.lower() == 'null':
         # Return public images (no patient context)
         return jsonify({'images': fetch_public_images()})

     # Fetch base64-encoded image names from DB for the patient
     fetched_images = db.custom_query(
         Queries.GET_ALL_PATIENT_IMAGES_BY_APPOINTMENT_ID,
         from_map=lambda row: row["imageBase64"],
         args=[patient_id]
     )

     # Ensure images_list has only unique entries
     if fetched_images:
         for image_name in fetched_images:
             if image_name not in images_list:
                 images_list.append(image_name)

     return jsonify({'images': images_list})


 @app.route('/get_image_comment/<filename>')
 def get_image_comment(filename):
     db = DatabaseService()
     image = db.query_by_column('patient_images', 'imageBase64', filename, PatientImagesModel.from_map)
     if image and image.comment:
         return jsonify({'comment': image.comment})
     return jsonify({'comment': ''})

 @app.route('/get_patient_id_name/<string:patient_id>', methods=['GET'])
 def get_patient_details(patient_id):
     patient=db.query_by_column('patients','patientId',patient_id,PatientsModel.from_map)
     return jsonify({'patient_id': patient.patient_id,'patient_name':patient.patient_name})

 @app.route('/capture_photo/<string:public_flag>/<string:patient_name>/<string:isFlipped>/<int:rotationAngle>', methods=['POST'])
 def capture_photo(public_flag,patient_name,isFlipped, rotationAngle):
    global cam,recording_rotation_angle
    global images_list
    with lock:
        if cam and cam.isOpened():
            ret, frame = cam.read()
            if ret:
                if isFlipped == 'true':
                    frame = cv2.flip(frame, 1)
                if recording_rotation_angle and recording_rotation_angle != 0:
                    (h, w) = frame.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, -recording_rotation_angle, 1.0)
                    frame = cv2.warpAffine(frame, M, (w, h))


                timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S%f")
                filename = f"img_{timestamp}.jpg"

                if public_flag.lower() == 'true':
                    path = os.path.join(_get_documents_path(), 'DrCamApp', 'public','images')
                    clicked_images.append(path+'/'+filename)
                else:
                    path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'images')
                    images_list.append(filename)
                    clicked_images.append(path + '/' + filename)
                    temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
                    os.makedirs(temp_path, exist_ok=True)
                    cv2.imwrite(temp_path + '/' + filename, frame)

                os.makedirs(path, exist_ok=True)
                cv2.imwrite(path+'/'+filename, frame)
                return {'status': 'ok', 'filename': filename}

    return {'status': 'fail'}, 500

 @app.route('/save_comment_image/<string:file_name>', methods=['POST'])
 def save_image_comment(file_name):
     data = request.get_json()
     comment = data.get('comment')
     try:
      if (comment):
         patient_image = db.query_by_column('patient_images', 'imageBase64', file_name,
                                            PatientImagesModel.from_map)
         if patient_image:
             patient_image.comment = comment
             db.update(patient_image)
             return jsonify({'status': 'ok'})

     except Exception as e:
         print("❌ Error saving comment image:", e)
         return jsonify({'status': 'fail', 'error': str(e)}), 500

 @app.route('/save_edited_image/<string:patient_name>', methods=['POST'])
 def save_edited_image(patient_name):
     data = request.get_json()
     comment=data.get('comment')
     image_data = data.get('image_data')
     original_filename = data.get('original_filename')
     jpg_index = original_filename.lower().find('.jpg')
     if jpg_index != -1:
         original_filename = original_filename[:jpg_index + 4]
     if not image_data or not original_filename:
         return jsonify({'status': 'fail', 'reason': 'missing_data'}), 400


     try:
         # Decode base64 string
         header, encoded = image_data.split(",", 1)
         img_bytes = base64.b64decode(encoded)

         # Load image via PIL
         image = Image.open(BytesIO(img_bytes)).convert("RGB")

         # Use original filename to overwrite (or save new)
         filename = f"{original_filename}"
         path = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'images')
         full_save_path = os.path.join(path, filename)
         os.makedirs(path, exist_ok=True)
         image.save(full_save_path, format='JPEG')

         # Also save in temp_images/captures for UI access
         temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
         os.makedirs(temp_path, exist_ok=True)
         image.save(os.path.join(temp_path, filename), format='JPEG')

         if filename not in images_list:
             images_list.append(filename)
             clicked_images.append(path + '/' + filename)

         return jsonify({'status': 'ok', 'filename': filename})

     except Exception as e:
         print("❌ Error saving edited image:", e)
         return jsonify({'status': 'fail', 'error': str(e)}), 500

 @app.route('/media')
 def list_media():
    global clicked_images
    return {'files': clicked_images}

 @app.route('/temp_images/<filename>')
 def temp_images(filename):
    temp_dir = os.path.join(app.root_path, 'temp_images', 'captures')
    return send_from_directory(temp_dir, filename)

 from flask import send_from_directory

 @app.route('/temp_videos/<path:filename>')
 def stream_video(filename):
     path = os.path.join(app.root_path, 'temp_images', 'videos', filename)
     if not os.path.isfile(path):
         abort(404)

     range_header = request.headers.get('Range', None)
     if not range_header:
         return Response(open(path, 'rb'), mimetype='video/mp4')

     size = os.path.getsize(path)
     byte1, byte2 = 0, None

     try:
         parts = range_header.strip().replace('bytes=', '').split('-')
         byte1 = int(parts[0])
         if len(parts) == 2 and parts[1]:
             byte2 = int(parts[1])
     except ValueError:
         abort(400)

     byte2 = byte2 if byte2 is not None else size - 1
     length = byte2 - byte1 + 1

     with open(path, 'rb') as f:
         f.seek(byte1)
         data = f.read(length)

     response = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
     response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
     response.headers.add('Accept-Ranges', 'bytes')
     response.headers.add('Content-Length', str(length))
     return response

 @app.route('/get_image')
 def get_image():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return "Image not found", 404
    return send_file(path, mimetype='image/jpeg')

 # @app.route('/captures/<path:filename>')
 # def get_file(filename):
 #     return send_from_directory(CAPTURE_DIR, filename)

 @app.route('/shutdown', methods=['POST'])
 def shutdown():
    global cam
    dir = os.path.join(app.root_path, 'temp_images', 'captures')
    delete_all_files_in_dir(dir)
    dir = os.path.join(app.root_path, 'temp_images', 'videos')
    delete_all_files_in_dir(dir)
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
      # toaster.show_toast("New Notification", "Patient details updated successfully!", duration=5)
    else:
        patient = PatientsModel(None, appointmentId, patientName, gender,dateOfBirth, phone, address)
        persist_id= db.insert(patient)
        patients= db.query_by_column("patients","patientId",persist_id,PatientsModel.from_map)
        if(patients):
            save_patient_history(patients)
            print(patients)
        # toaster.show_toast("New Notification", "Patient details registered successfully", duration=5)


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

     # Process Images
     if images_list:
         image_filenames = list(images_list)  # copy before clearing
         src_path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'images')
         dest_path = os.path.join(_get_documents_path(), 'DrCamApp', patient.patient_name, 'images')
         os.makedirs(dest_path, exist_ok=True)

         for filename in image_filenames:
             temp_path = os.path.join(src_path, filename)
             dest_file_path = os.path.join(dest_path, filename)
             try:
                 if os.path.exists(temp_path):
                     # If file exists in destination, remove it to avoid conflict
                     if os.path.exists(dest_file_path):
                         os.remove(dest_file_path)
                     shutil.move(temp_path, dest_file_path)
             except Exception as e:
                 print(f"Failed to move {filename}: {e}")

         images_to_save=[]
         for filename in image_filenames:
             existing_image = db.custom_query(
                 Queries.CHECK_IF_IMAGE_EXISTS,
                 from_map=lambda row: row["imageBase64"],
                 args=[patient.patient_id,filename]
             )
             if not existing_image:
                 images_to_save.append(filename)

         # Save image metadata
         patient_images = [
             PatientImagesModel(None, patient.patient_id, saved_history_id, filename, datetime.now())
             for filename in images_to_save
         ]
         db.bulk_insert(patient_images)
         images_list.clear()

     # Process Videos
     if videos_path_list:
         video_filenames = []  # store only filenames for DB insert
         dest_path = os.path.join(_get_documents_path(), 'DrCamApp', patient.patient_name, 'videos')
         os.makedirs(dest_path, exist_ok=True)

         for full_path in videos_path_list:
             filename = os.path.basename(full_path)
             temp_path = full_path
             dest_file_path = os.path.join(dest_path, filename)

             try:
                 if os.path.exists(temp_path):
                     # If file exists in destination, remove it
                     if os.path.exists(dest_file_path):
                         os.remove(dest_file_path)
                     shutil.move(temp_path, dest_file_path)
                     video_filenames.append(filename)
             except Exception as e:
                 print(f"Failed to move {filename}: {e}")

         if video_filenames:
             patient_videos = [
                 PatientVideosModel(None, patient.patient_id, saved_history_id, filename, datetime.now())
                 for filename in video_filenames
             ]
             db.bulk_insert(patient_videos)

         videos_path_list.clear()

 @app.route('/api/save_images', methods=['POST'])
 def save_images_and_videos():
     try:
         data = request.get_json(silent=True) or {}
         patient_id = data.get('patient_id')
         patient_name = data.get('patient_name')
         appointment_id=data.get('id')

         if not patient_id or not patient_name:
             return jsonify({"error": "patient_id and patient_name are required"}), 400

         images_saved = 0
         videos_saved = 0
         check_query = '''
                        SELECT *
                        FROM patient_history
                        WHERE patientId = ? AND date(appointmentDate) = ? LIMIT 1;
                    '''
         today = datetime.now().strftime('%Y-%m-%d')
         existing_history = db.custom_query_v1(check_query, [
             patient_id,
             today
         ])


         # Create one history row for this call (use None for id so DB autogenerates it)
         patient_history = PatientHistoryModel(
             existing_history if existing_history else None,
             appointment_id,
             patient_id,
             datetime.now(),
             datetime.now()
         )
         if existing_history:
             history_id = db.update(patient_history)
         else:
          history_id = db.insert(patient_history)  # make sure this returns the PK

         # ------- IMAGES -------
         if images_list:
             image_filenames = list(images_list)  # copy before clearing
             src_path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'images')
             dest_path = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'images')
             os.makedirs(dest_path, exist_ok=True)

             for filename in image_filenames:
                 temp_path = os.path.join(src_path, filename)
                 dest_file_path = os.path.join(dest_path, filename)
                 try:
                     if os.path.exists(temp_path):
                         if os.path.exists(dest_file_path):
                             os.remove(dest_file_path)
                         shutil.move(temp_path, dest_file_path)
                 except Exception as e:
                     app.logger.exception(f"Failed to move image {filename}: {e}")

             images_to_save = []
             for filename in image_filenames:
                 existing_image = db.custom_query(
                     Queries.CHECK_IF_IMAGE_EXISTS,
                     from_map=lambda row: row["imageBase64"],
                     args=[patient_id, filename]
                 )
                 if not existing_image:
                     images_to_save.append(filename)

             if images_to_save:
                 patient_images = [
                     PatientImagesModel(
                         None,  # id
                         patient_id,
                         history_id,  # <-- use the history_id we just created
                         filename,
                         datetime.now()
                     )
                     for filename in images_to_save
                 ]
                 db.bulk_insert(patient_images)
                 images_saved = len(patient_images)

             images_list.clear()

         # ------- VIDEOS -------
         if videos_path_list:
             video_filenames = []
             dest_path = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'videos')
             os.makedirs(dest_path, exist_ok=True)

             for full_path in videos_path_list:
                 filename = os.path.basename(full_path)
                 dest_file_path = os.path.join(dest_path, filename)
                 try:
                     if os.path.exists(full_path):
                         if os.path.exists(dest_file_path):
                             os.remove(dest_file_path)
                         shutil.move(full_path, dest_file_path)
                         video_filenames.append(filename)
                 except Exception as e:
                     app.logger.exception(f"Failed to move video {filename}: {e}")

             if video_filenames:
                 patient_videos = [
                     PatientVideosModel(
                         None,
                         patient_id,
                         history_id,  # <-- use the same history_id!
                         filename,
                         datetime.now()
                     )
                     for filename in video_filenames
                 ]
                 db.bulk_insert(patient_videos)
                 videos_saved = len(patient_videos)

             videos_path_list.clear()

         return jsonify({
             "status": "ok",
             "history_id": history_id,
             "images_saved": images_saved,
             "videos_saved": videos_saved
         }), 201

     except Exception as e:
         # Make sure you SEE the DB error
         app.logger.exception("save_images_and_videos failed")
         return jsonify({"error": str(e)}), 500
 @app.route('/get_patient/<string:patient_id>')
 def get_patient(patient_id):
    appointment_date = request.args.get('appointment_date')
    patient = db.query_by_column("patients","patientId",patient_id,PatientsModel.from_map)
    if patient:
        get_all_patient_images(patient_id, patient.patient_name,appointment_date)
        get_all_patient_videos(patient_id,patient.patient_name)
        return jsonify({
            'status': 'success',
            'patient': {
                'id': patient.appointment_id,
                'patient_name': patient.patient_name,
                'gender': patient.gender,
                'dob': str(patient.date_of_birth),
                'phone': patient.phone,
                'address': patient.address,
                'patient_id':patient.patient_id
            },  'images': prefilled_image_list,
            'videos':prefilled_videos_list
        })

    return jsonify({'status': 'error', 'message': 'Patient not found'})

 def fetch_public_images():
     image_names = []
     temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
     os.makedirs(temp_path, exist_ok=True)
     image_path = os.path.join(_get_documents_path(), 'DrCamApp', 'public', 'images')

     # Collect image file metadata
     image_files = []
     for filename in os.listdir(image_path):
         src_file = os.path.join(image_path, filename)
         dst_file = os.path.join(temp_path, filename)

         if not os.path.isfile(src_file):
             continue
         try:
             # Get last modified time
             mtime = os.path.getmtime(src_file)
             image_files.append((filename, mtime))

             # Copy image to temp folder
             shutil.copy2(src_file, dst_file)
         except Exception as e:
             print(f"[ERROR] Failed to copy {filename} → {dst_file}: {e}")

     # Sort images by modified time (latest first)
     image_files.sort(key=lambda x: x[1], reverse=True)
     image_names = [filename for filename, _ in image_files]
     return image_names

 def get_all_patient_images(patient_id, patient_name,appointment_date):
    global prefilled_image_list
    prefilled_image_list.clear()

    # Ensure temp_images/captures exists
    temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
    os.makedirs(temp_path, exist_ok=True)
    patient_images=None
    if(appointment_date):
        # Get DB image filenames
        patient_images = db.custom_query(
            Queries.GET_ALL_PATIENT_IMAGES_BY_APPOINTMENT,
            from_map=lambda row: row["imageBase64"],
            args=[patient_id,appointment_date]
        )
    else:
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
                prefilled_image_list.append(filename)
        except Exception as e:
            print(f"Failed to copy image: {e}")

 def get_all_patient_videos(patient_id, patient_name):
     global prefilled_videos_list
     prefilled_videos_list.clear()

     # Ensure temp_images/videos exists
     temp_path = os.path.join(app.root_path, 'temp_images', 'videos')
     os.makedirs(temp_path, exist_ok=True)

     # Get DB video filenames
     patient_videos = db.custom_query(
         Queries.GET_ALL_PATIENT_VIDEOS,
         from_map=lambda row: row["videoPath"],
         args=[patient_id]
     )

     # Path where actual videos are stored
     video_path = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'videos')

     for filename in patient_videos:
         src_file = os.path.join(video_path, filename)
         dst_file = os.path.join(temp_path, filename)
         try:
             if os.path.exists(src_file):
                 shutil.copy2(src_file, dst_file)
                 prefilled_videos_list.append(filename)
         except Exception as e:
             print(f"Failed to copy video: {e}")

 def delete_all_files_in_dir(dir_path):
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")


 def _get_documents_path():
    """Get Windows 'Documents' folder using SHGetKnownFolderPath"""
    try:
        #from ctypes import windll, POINTER, byref
        from uuid import UUID
        import ctypes.wintypes

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

 @app.route('/save_settings', methods=['POST'])
 def save_camera_settings():
     global zoom, brightness, contrast, exposure, white_balance, frame_rate,recording_rotation_angle
     payload = request.get_json()
     settings = CameraSettingsModel(
         zoom=zoom,
         brightness=brightness,
         contrast=contrast,
         exposure=exposure,
         white_balance=white_balance,
         frame_rate=frame_rate,
         rotation_angle=payload.get('rotation_angle') if payload.get('rotation_angle') else 0
     )
     existing = db.query_by_column(settings.get_table_name(), "id", 1, CameraSettingsModel.from_map)

     if existing:
         db.update(settings)
     else:
         db.insert(settings)

     return jsonify({"status": "success", "message": "Camera settings saved"})


 def load_camera_settings():
     global zoom, brightness, contrast, exposure, white_balance, frame_rate,recording_rotation_angle
     db = DatabaseService()

     settings = db.query_by_column("camera_settings", "id", 1, CameraSettingsModel.from_map)

     if settings:
         # Apply saved settings
         zoom = settings.zoom
         brightness = settings.brightness
         contrast = settings.contrast
         exposure = settings.exposure
         white_balance = settings.white_balance
         frame_rate = settings.frame_rate
         recording_rotation_angle=settings.rotation_angle

         return settings.to_map()  # ✅ Return dict instead of jsonify
     else:
         # Apply default values
         zoom = 1.0
         brightness = 0
         contrast = 0
         exposure = 0.0
         white_balance = 0.0
         frame_rate = 20.0

         return {
             "zoom": zoom,
             "brightness": brightness,
             "contrast": contrast,
             "exposure": exposure,
             "white_balance": white_balance,
             "frame_rate": frame_rate
         }

 from flask import jsonify

 @app.route('/fetch_settings', methods=['GET'])
 def load_settings():
     global zoom, brightness, contrast, exposure, white_balance, frame_rate, recording_rotation_angle
     db = DatabaseService()

     settings = db.query_by_column("camera_settings", "id", 1, CameraSettingsModel.from_map)

     if settings:
         # Apply saved settings
         zoom = settings.zoom
         brightness = settings.brightness
         contrast = settings.contrast
         exposure = settings.exposure
         white_balance = settings.white_balance
         frame_rate = settings.frame_rate
         recording_rotation_angle = settings.rotation_angle

         return jsonify({
             "status": "ok",
             "settings": settings.to_map()
         })
     else:
         # Apply default values
         zoom = 1.0
         brightness = 0
         contrast = 0
         exposure = 0.0
         white_balance = 0.0
         frame_rate = 20.0
         recording_rotation_angle = 0

         return jsonify({
             "status": "default",
             "settings": {
                 "zoom": zoom,
                 "brightness": brightness,
                 "contrast": contrast,
                 "exposure": exposure,
                 "white_balance": white_balance,
                 "frame_rate": frame_rate,
                 "rotation_angle": recording_rotation_angle
             }
         })

 @app.route('/reset_settings', methods=['POST'])
 def reset_camera_settings():
     global zoom, brightness, contrast, exposure, white_balance, frame_rate
     conn = db.get_connection()
     cursor = conn.cursor()
     cursor.execute("DELETE FROM camera_settings")
     conn.commit()
     conn.close()
     return jsonify({
         "status": "success",
         "message": "Camera settings reset to default."
     })

import base64
import ctypes
import shutil
from pathlib import Path
import re

import ffmpeg
from PIL import Image
from io import BytesIO


from flask import Flask,send_file, render_template, Response, request, send_from_directory, jsonify
from plyer import notification
from pygrabber.dshow_graph import FilterGraph
import cv2
import threading
import logging
import os
from flask import abort

from datetime import datetime

from win10toast import ToastNotifier

from contants.queries import Queries
from db_config.database_service import DatabaseService
from models.patient_history_model import PatientHistoryModel
from models.patient_images_model import PatientImagesModel
from models.patient_model import PatientsModel
from models.patient_videos_model import PatientVideosModel
from models.profile_model import ProfileModel

logging.basicConfig(level=logging.DEBUG)
db = DatabaseService()
toaster = ToastNotifier()

recording = False
out = None
zoom = 1.0
brightness = 0
lock = threading.Lock()
cam = None
contrast = 0
exposure = 0
white_balance = 0

# CAPTURE_DIR = 'static/captures'
# os.makedirs(CAPTURE_DIR, exist_ok=True)

images_list = []
clicked_images= []
videos_path_list=[]
videos_file_names=[]
prefilled_image_list=[]
prefilled_videos_list=[]

def register_camera(app):

 def initialize_camera():
    global cam,exposure,white_balance
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
    exposure = cam.get(cv2.CAP_PROP_EXPOSURE)
    white_balance = cam.get(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U)
    if exposure == -1:  # Property unsupported, set default 0
        exposure = 0
    if white_balance == -1:
        white_balance = 0


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
    global cam, recording, out, zoom, brightness,contrast

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
            alpha = 1.0 + contrast / 100.0  # Contrast control (1.0 is no change)
            beta = brightness  # Brightness control (0 is no change)
            frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
            #frame = cv2.convertScaleAbs(frame, alpha=1, beta=brightness)

            if recording and out:
                out.write(frame)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

 @app.route('/camera')
 def camera():
    initialize_camera()
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

 @app.route('/set_contrast', methods=['POST'])
 def set_contrast():
     global contrast
     contrast = int(request.form['contrast'])
     return ('', 204)

 @app.route('/set_exposure', methods=['POST'])
 def set_exposure():
     global exposure, cam
     #exposure = float(request.form['exposure'])
     # with lock:
     #     if cam and cam.isOpened():
     #         cam.set(cv2.CAP_PROP_EXPOSURE, exposure)
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

 @app.route('/start_recording/<string:public_flag>/<string:patient_name>', methods=['POST'])
 def start_recording(public_flag, patient_name):
     global recording, out, cam, videos_path_list, videos_file_names
     with lock:
         if cam and cam.isOpened():
             fourcc = cv2.VideoWriter_fourcc(*'mp4v')
             width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
             height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
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
             out = cv2.VideoWriter(full_path, fourcc, 20.0, (width, height))
             recording = True
             print(f"✅ Started recording: {full_path}")
     return ('', 204)

 @app.route('/stop_recording', methods=['POST'])
 def stop_recording():
     global recording, out, videos_path_list
     with lock:
         recording = False
         if out:
             out.release()
             out = None
             print("🛑 Recording stopped.")

         # Convert last recorded video to browser-compatible format
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
                 print(f"✅ Converted video saved to: {converted_path}")
             except Exception as e:
                 print(f"❌ FFmpeg conversion failed: {e}")

     return ('', 204)

 @app.route('/get_captured_image/<string:patient_id>', methods=['GET'])
 def get_captured_images(patient_id):
     global images_list

     # If patient_id is 'null' or empty, return existing images_list as-is
     if not patient_id.strip() or patient_id.lower() == 'null':
         return jsonify({'images': images_list})


     # Fetch image base64s from DB
     fetched_images = db.custom_query(
         Queries.GET_ALL_PATIENT_IMAGES_BY_APPOINTMENT_ID,
         from_map=lambda row: row["imageBase64"],
         args=[patient_id]
     )

     # Append only new images to the global list
     if fetched_images:
         for image_name in fetched_images:
             if image_name not in images_list:
                 images_list.append(image_name)

     return jsonify({'images': images_list})

 @app.route('/get_patient_id_name/<string:patient_id>', methods=['GET'])
 def get_patient_details(patient_id):
     patient=db.query_by_column('patients','appointmentId',patient_id,PatientsModel.from_map)
     return jsonify({'patient_id': patient.patient_id,'patient_name':patient.patient_name})

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
                    temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
                    os.makedirs(temp_path, exist_ok=True)
                    cv2.imwrite(temp_path + '/' + filename, frame)

                os.makedirs(path, exist_ok=True)
                cv2.imwrite(path+'/'+filename, frame)
                return {'status': 'ok', 'filename': filename}

    return {'status': 'fail'}, 500

 @app.route('/save_edited_image', methods=['POST'])
 def save_edited_image():
     data = request.get_json()
     image_data = data.get('image_data')
     original_filename = data.get('original_filename')

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
         path = os.path.join(_get_documents_path(), 'DrCamApp', 'temp', 'images')
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
      toaster.show_toast("New Notification", "Patient details updated successfully!", duration=5)
    else:
        patient = PatientsModel(None, appointmentId, patientName, gender,dateOfBirth, phone, address)
        persist_id= db.insert(patient)
        patients= db.query_by_column("patients","patientId",persist_id,PatientsModel.from_map)
        if(patients):
            save_patient_history(patients)
            print(patients)
        toaster.show_toast("New Notification", "Patient details registered successfully", duration=5)


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

 @app.route('/get_patient/<string:patient_id>')
 def get_patient(patient_id):
    patient = db.query_by_column("patients","patientId",patient_id,PatientsModel.from_map)
    if patient:
        get_all_patient_images(patient_id, patient.patient_name)
        get_all_patient_videos(patient_id,patient.patient_name)
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
            'images': prefilled_image_list,
            'videos':prefilled_videos_list
        })

    return jsonify({'status': 'error', 'message': 'Patient not found'})




 def get_all_patient_images(patient_id, patient_name):
    global prefilled_image_list
    prefilled_image_list.clear()

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
        from ctypes import windll, POINTER, byref
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


import os
import shutil
from ctypes import windll
from datetime import datetime
from pathlib import Path

from _ctypes import byref
from flask import redirect, request, url_for, render_template, jsonify
from db_config.database_service import DatabaseService
from models.patient_history_model import PatientHistoryModel
from models.patient_model import PatientsModel
from models.profile_model import ProfileModel

db = DatabaseService()

def register_pat_reg_routes(app):
    @app.route('/patient_registration', methods=["GET", "POST"])
    def patient_registration():
        profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
        if profile and profile.agency_name:
            agency_name = profile.agency_name
        else:
            agency_name = 'Mex Enterprise'

        return render_template("patient_registeration.html", agency_name=agency_name)

    from flask import jsonify, request
    import os
    import shutil

    @app.route('/register_patient', methods=['POST'])
    def register_patient():
        status = None
        persist_id = None
        data = request.form
        appointmentId = data.get('id')
        patientName = data.get('patient_name')
        gender = data.get('gender')
        dateOfBirth = data.get('dob')
        phone = data.get('phone')
        address = data.get('address')

        try:
            # Check existing patient
            exists = db.query_by_column("patients", "phone", phone, PatientsModel.from_map)
            exists_by_id = db.query_by_column("patients", "appointmentId", appointmentId, PatientsModel.from_map)

            if exists:
                patient = PatientsModel(exists.patient_id, appointmentId, patientName, gender, dateOfBirth, phone,
                                        address)

                # Rename folder safely
                old_path = os.path.join(_get_documents_path(), 'DrCamApp', exists.patient_name, 'images')
                new_path = os.path.join(_get_documents_path(), 'DrCamApp', patientName, 'images')

                if os.path.exists(old_path):
                    # If new_path exists, remove to avoid conflict
                    if os.path.exists(new_path):
                        shutil.rmtree(new_path)
                    os.rename(old_path, new_path)
                    print(f"Renamed {old_path} -> {new_path}")
                else:
                    os.makedirs(new_path, exist_ok=True)
                    print(f"No old folder. Created new folder: {new_path}")

                db.updatePatient(patient)
                persist_id = exists.patient_id
                status = 'updated'
                save_patient_history(patient)

            elif exists_by_id:
                patient = PatientsModel(exists_by_id.patient_id, appointmentId, patientName, gender, dateOfBirth, phone,
                                        address)

                old_path = os.path.join(_get_documents_path(), 'DrCamApp', exists_by_id.patient_name)
                new_path = os.path.join(_get_documents_path(), 'DrCamApp', patientName)

                if os.path.exists(old_path):
                    if os.path.exists(new_path):
                        shutil.rmtree(new_path)
                    os.rename(old_path, new_path)
                    print(f"Renamed {old_path} -> {new_path}")
                else:
                    os.makedirs(new_path, exist_ok=True)
                    print(f"No old folder. Created new folder: {new_path}")

                db.updatePatient(patient)
                persist_id = exists_by_id.patient_id
                status = 'updated'
                save_patient_history(patient)

            else:
                patient = PatientsModel(None, appointmentId, patientName, gender, dateOfBirth, phone, address)
                persist_id = db.insert(patient)
                patients = db.query_by_column("patients", "patientId", persist_id, PatientsModel.from_map)
                if patients:
                    save_patient_history(patients)
                    print(patients)
                status = 'saved'

            # Commit transaction if using SQLAlchemy or similar
            db.commit() if hasattr(db, 'commit') else None

            return jsonify({'status': status, 'patient_id': persist_id})

        except Exception as e:
            # Rollback transaction in case of error
            db.rollback() if hasattr(db, 'rollback') else None
            print(f"Error registering patient: {e}")
            return jsonify({'status': 'error', 'message': str(e), 'patient_id': persist_id}), 500

    def save_patient_history(patient):
        try:
            today = datetime.now().strftime('%Y-%m-%d')

            # SQL to check if patient history already exists for today
            check_query = '''
                SELECT COUNT(1)
                FROM patient_history
                WHERE patientId = ? AND date(appointmentDate) = ?
            '''

            existing_count = db.custom_query_v1(check_query, [
                patient.patient_id,
                today
            ])

            if existing_count > 0:
                print("Patient history for today already exists. Skipping insert.")
                return None

            # No existing entry — insert new record
            patient_history = PatientHistoryModel(
                None,
                patient.appointment_id,
                patient.patient_id,
                today,
                today
            )
            saved_history_id = db.insert(patient_history)
            print(f"Patient history saved with ID: {saved_history_id}")
            return saved_history_id

        except Exception as e:
            print(f"[ERROR] Failed to save patient history: {e}")
            return None

    @app.route('/load_patient/<string:patient_id>')
    def get_patient_deta(patient_id):
        patient = db.query_by_column("patients", "appointmentId", patient_id, PatientsModel.from_map)
        if patient:
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
            })

        return jsonify({'status': 'error', 'message': 'Patient not found'})

    def _get_documents_path():
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

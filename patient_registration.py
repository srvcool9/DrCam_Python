from datetime import datetime
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

    @app.route('/register_patient', methods=['POST'])
    def register_patient():
        status=None
        data = request.form
        appointmentId = data.get('id')
        patientName = data.get('patient_name')
        gender = data.get('gender')
        dateOfBirth = data.get('dob')
        phone = data.get('phone')
        address = data.get('address')

        exists = db.query_by_column("patients", "phone", phone, PatientsModel.from_map)
        if (exists):
            patient = PatientsModel(exists.patient_id, appointmentId, patientName, gender, dateOfBirth, phone, address)
            db.updatePatient(patient)
            status='updated'
            save_patient_history(patient)

        else:
            patient = PatientsModel(None, appointmentId, patientName, gender, dateOfBirth, phone, address)
            persist_id = db.insert(patient)
            patients = db.query_by_column("patients", "patientId", persist_id, PatientsModel.from_map)
            if (patients):
                save_patient_history(patients)
                print(patients)
                status='saved'
        return jsonify({'status': status})


    def save_patient_history(patient):
        try:
            today = datetime.now().strftime('%Y-%m-%d')

            # SQL to check if patient history already exists for today
            check_query = '''
                SELECT COUNT(1)
                FROM patient_history
                WHERE patientId = ? AND appointmentDate = ?
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

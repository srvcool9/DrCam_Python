from flask import redirect, request, url_for, render_template
from db_config.database_service import DatabaseService
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

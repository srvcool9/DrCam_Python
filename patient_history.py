from flask import render_template

from contants.queries import Queries
from db_config.database_service import DatabaseService
from dto.patient_visit_dto import PatientVisitDTO
from models.profile_model import ProfileModel

db=DatabaseService()

def register_patient_history(app):

 @app.route("/patient_history")
 def patient_history():
     profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
     if (profile and profile.agency_name):
          agency_name = profile.agency_name
     else:
          agency_name = 'Mex Enterprise'
     dto_list = db.custom_query(Queries.GET_GRID_DATA, PatientVisitDTO.from_map)

     return render_template("patient_history.html",dto_list=dto_list,agency_name=agency_name)




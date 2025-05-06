from flask import render_template
from src import app
from src.contants.queries import Queries
from src.db_config.database_service import DatabaseService
from src.dto.patient_visit_dto import PatientVisitDTO
from src.models.profile_model import ProfileModel

db=DatabaseService()


@app.route("/patient_history")
def patient_history():
     profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
     if (profile and profile.agency_name):
          agency_name = profile.agency_name
     else:
          agency_name = 'Mex Enterprise'
     dto_list = db.custom_query(Queries.GET_GRID_DATA, PatientVisitDTO.from_map)

     return render_template("patient_history.html",dto_list=dto_list,agency_name=agency_name)
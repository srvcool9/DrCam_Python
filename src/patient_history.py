from flask import render_template
from src import app
from src.contants.queries import Queries
from src.db_config.database_service import DatabaseService
from src.dto.patient_visit_dto import PatientVisitDTO

db=DatabaseService()


@app.route("/patient_history")
def patient_history():
     data= db.custom_query(Queries.GET_GRID_DATA,PatientVisitDTO.from_map)
     dto_list = [PatientVisitDTO.from_map(row) for row in data]
     return render_template("patient_history.html",dto_list=dto_list)
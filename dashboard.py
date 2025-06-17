
from flask import Flask, render_template

from contants.queries import Queries
from db_config.database_service import DatabaseService
from models.profile_model import ProfileModel



def register_dashboard_route(app):
 db=DatabaseService()

 @app.route("/dashboard")
 def dashboard():
    profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    if (profile and profile.agency_name):
        agency_name = profile.agency_name
    else:
        agency_name = 'Mex Enterprise'

    total_registered_stats= db.custom_query_v1(Queries.GET_TOTAL_REGISTERED_PATIENTS)
    patient_visited_this_week_stats=db.custom_query_v1(Queries.GET_PATIENTS_COUNT_VISITED_CURRENT_WEEK)
    patient_visited_this_month_stats=db.custom_query_v1(Queries.GET_PATIENTS_COUNT_VISITED_CURRENT_MONTH)
    patient_visited_this_year_stats=db.custom_query_v1(Queries.GET_PATIENTS_COUNT_VISITED_CURRENT_YEAR)
    stats = {
        "total_patients": total_registered_stats,
        "week_visits": patient_visited_this_week_stats,
        "month_visits": patient_visited_this_month_stats,
        "year_visits": patient_visited_this_year_stats,
        "frequent_patients": 0
    }
    return render_template("dashboard.html", stats=stats,agency_name=agency_name)


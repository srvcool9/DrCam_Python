
from flask import Flask, render_template
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
    stats = {
        "total_patients": 500,
        "week_visits": 10,
        "month_visits": 50,
        "year_visits": 350,
        "frequent_patients": 70
    }
    return render_template("dashboard.html", stats=stats,agency_name=agency_name)


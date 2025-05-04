
from flask import Flask, render_template
from src import app
from src.db_config.database_service import DatabaseService
from src.models.profile_model import ProfileModel
from src.db_config import database_service


db=DatabaseService()

@app.route("/dashboard")
def dashboard():
    global agency_name
    profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    if (profile):
        agency_name = profile.agency_name
    stats = {
        "total_patients": 500,
        "week_visits": 10,
        "month_visits": 50,
        "year_visits": 350,
        "frequent_patients": 70
    }
    return render_template("dashboard.html", stats=stats,agency_name=agency_name)


from urllib import request

from flask import render_template,request
from src import app
from src.db_config.database_service import DatabaseService
from src.models.profile_model import ProfileModel

db=DatabaseService()

@app.route("/setting")
def setting():
    return render_template("setting.html")

@app.route('/save_information', methods=["POST"])
def save_information():
    if request.method == 'POST':
        agency_name = request.form['agency_name']
        contact_number = request.form['contact_number']
        email = request.form['email']
        password = request.form['password']
        persist = db.query_by_column("doctor_profile", "email", "sgawli@gmail.com", ProfileModel.from_map)
        print(persist)
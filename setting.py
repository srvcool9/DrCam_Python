from urllib import request
from flask import render_template, request, jsonify
from plyer import notification
from db_config.database_service import DatabaseService
from models.profile_model import ProfileModel
from win10toast import ToastNotifier

db=DatabaseService()
toaster = ToastNotifier()

def register_setting(app):
 @app.route("/setting")
 def setting():
    profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    if (profile and profile.agency_name):
        agency_name = profile.agency_name
    else:
        agency_name = 'Mex Enterprise'
    data = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    if data:
        data_tuple = [
            data.id,  # data[0]
            data.agency_name,  # data[1]
            data.contact_number,  # data[2]
            data.email,  # data[3]
            data.password,  # data[4]
            "support@mextech.com",
            "9876543210"
        ]
    else:
        data_tuple = None
    return render_template("setting.html",data=data_tuple,agency_name=agency_name)

 @app.route('/save_information', methods=["POST"])
 def save_information():

        agency_name = request.form['agency_name']
        contact_number = request.form['contact_number']
        email = request.form['email']
        password = request.form['password']
        persist = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
        if(persist):
             print(persist)
             doctor_profile = ProfileModel(1,agency_name, contact_number, email, password)
             db.update(doctor_profile)
             toaster.show_toast("New Notification", "Profile updated successfully!", duration=5)
             return jsonify({"status": "updated"})
        else:
            doctor_profile= ProfileModel(1,agency_name,contact_number,email,password)
            db.insert(doctor_profile)
            toaster.show_toast("New Notification", "Profile saved successfully!", duration=5)
            return jsonify({"status": "saved"})

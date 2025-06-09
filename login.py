from flask import  redirect, request, url_for, render_template

from db_config.database_service import DatabaseService
from models.profile_model import ProfileModel
db=DatabaseService()

def register_login_routes(app):
 print("[DEBUG] register_login_routes called")

 @app.route('/', methods=["GET", "POST"])
 def login():
    profile=db.query_by_column("doctor_profile","id",1,ProfileModel.from_map)
    if(profile and profile.agency_name):
        agency_name=profile.agency_name
    else:
        agency_name='Mex Enterprise'
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        return handle_login(email, password)
    return render_template("login.html",agency_name=agency_name)

 def handle_login(email, password):
    if email == 'admin@mex.com' and password == 'admin':
        print(f"Login with {email} / {password}")
        return redirect(url_for('dashboard'))
    else:
        profile= db.query_by_column("doctor_profile","email",email,ProfileModel.from_map)
        if(profile and profile.get('password')==password):
            print("Logged in success")
            return redirect(url_for('dashboard'))
        else:
            print("Invalid email or password")
            return "Invalid email or password", 401


from flask import render_template_string, redirect, request, url_for

from src import app
from src.db_config.database_service import DatabaseService
from src.models.profile_model import ProfileModel

db=DatabaseService()
html_template = """
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.7.4/lottie.min.js"></script>
    <title>Doctor's Agency Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0;
            height: 100vh;
            padding: 0 5%;
        }
        .left-section {
            max-width: 45%;
        }
        .left-section h1 {
            color: #4688A0;
            font-size: 2.5rem;
        }
        .left-section label {
            display: block;
            margin-top: 20px;
            font-weight: bold;
            color: #666;
        }
        .left-section input {
            width: 100%;
            padding: 10px;
            font-size: 1rem;
            margin-top: 5px;
            border-radius: 8px;
            border: 1px solid #ccc;
        }
        .remember-me {
            margin-top: 10px;
        }
        .login-btn {
            margin-top: 30px;
            padding: 15px;
            width: 100%;
            background-color: #4688A0;
            color: white;
            font-weight: bold;
            font-size: 1.5rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .right-section img {
            max-height: 300px;
        }
        .logo-container {
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .logo-container img {
      max-width: 200px;
      height: auto;
    }

    .clinic-name {
      margin-top: 20px;
      font-size: 2rem;
      color: #2c3e50;
      font-weight: bold;
    }

    .tagline {
      font-size: 1rem;
      color: #6c757d;
    }
    </style>
</head>
<body>
    <div class="left-section">
     <div class="logo-container">
    <img src="{{ url_for('static', filename='clinical_logo.jpg') }}" alt="Medical Logo">
    <div class="clinic-name">{{agency_name}}</div>
    <div class="tagline">Your Health, Our Priority</div>
  </div>
        <h2>Login</h2>
        <form method="POST" action="/">
            <label>Email</label>
            <input type="email" name="email" required />
            <label>Password</label>
            <input type="password" name="password" required />

            <button type="submit"  class="login-btn">Login</button>
        </form>
    </div>
    <div class="right-section" style="height: 300px;width: 600px;">
       <div id="lottie-container"></div>
    </div>
    <script>
    lottie.loadAnimation({
        container: document.getElementById('lottie-container'),
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: '/static/my_animation.json' 
    });
</script>
</body>
</html>
"""



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
    return render_template_string(html_template,agency_name=agency_name)

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


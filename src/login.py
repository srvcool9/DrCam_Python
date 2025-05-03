from flask import render_template_string, redirect, request, url_for

from src import app

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
    </style>
</head>
<body>
    <div class="left-section">
        <h1>Doctor’s Agency Name</h1>
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
        path: '../static/my_animation.json' 
    });
</script>
</body>
</html>
"""



@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        return handle_login(email, password)
    return render_template_string(html_template)

def handle_login(email, password):
    if email == 'admin@mex.com' and password == 'admin':
        print(f"Login with {email} / {password}")
        return redirect(url_for('dashboard'))
    else:
        print("Invalid email or password")
        return "Invalid email or password", 401


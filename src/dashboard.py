
from flask import Flask, render_template
from src import app


@app.route("/dashboard")
def dashboard():

    stats = {
        "total_patients": 500,
        "week_visits": 10,
        "month_visits": 50,
        "year_visits": 350,
        "frequent_patients": 70
    }
    return render_template("dashboard.html", stats=stats)


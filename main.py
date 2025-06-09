import os
import sys
import threading
import webview
from flask import Flask

from camera import register_camera
from login import register_login_routes
from dashboard import register_dashboard_route
from db_config.database_service import DatabaseService
from patient_history import register_patient_history
from pdf_generater import register_pdf_route
from setting import register_setting

# Initialize the Flask app
app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)

register_login_routes(app)
register_dashboard_route(app)
register_camera(app)
register_patient_history(app)
register_setting(app)
register_pdf_route(app)

# Initialize DB
db = DatabaseService()


# Start Flask server in a thread
def start_flask():
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
    app.run(debug=True, use_reloader=False, port=5000)

# Entry point
if __name__ == '__main__':

    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    # Launch the UI window
    webview.create_window("Doctor's Agency Login", "http://127.0.0.1:5000", width=2000, height=800)
    webview.start()

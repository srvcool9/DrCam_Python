import webview
import threading
from src import app
from src import camera
from src import dashboard
from src import setting
from src import patient_history
from src.db_config.database_service import DatabaseService

# Initialize the camera once when the app is imported
camera.initialize_camera()


def start_flask():
    app.run(debug=True,use_reloader=False, port=5000)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    db=DatabaseService()
    webview.create_window("Doctor's Agency Login", "http://127.0.0.1:5000", width=2000, height=800)
    webview.start()

import webview
import threading
from src import app
from src import camera
from src.db_config import database_configuration

# Initialize the camera once when the app is imported
camera.initialize_camera()

#Initialize db on app
database_configuration.setup_database()

def start_flask():
    app.run(debug=False, port=5000)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    webview.create_window("Doctor's Agency Login", "http://127.0.0.1:5000", width=2000, height=800)
    webview.start()

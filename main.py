import os
import sys
import threading
from pathlib import Path

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
    app.run(debug=True, use_reloader=False, port=5000)

# # Entry point
# if __name__ == '__main__':
#
#     flask_thread = threading.Thread(target=start_flask)
#     flask_thread.daemon = True
#     flask_thread.start()
#     # Launch the UI window
#     webview.create_window("Doctor's Agency Login", "http://127.0.0.1:5000", width=2000, height=800)
#     webview.start()

def _get_documents_path():
    """Get Windows 'Documents' folder using SHGetKnownFolderPath"""
    try:
        from ctypes import windll, POINTER, byref
        from uuid import UUID
        import ctypes.wintypes

        SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(ctypes.c_byte), ctypes.wintypes.DWORD,
            ctypes.wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
        ]

        FOLDERID_Documents = UUID('{FDD39AD0-238F-46AF-ADB4-6C85480369C7}')
        path_ptr = ctypes.c_wchar_p()

        SHGetKnownFolderPath(
            (ctypes.c_byte * 16).from_buffer_copy(FOLDERID_Documents.bytes_le),
            0, 0, byref(path_ptr)
        )
        return Path(path_ptr.value)
    except Exception as e:
        print("Error getting Documents path, falling back to home/Documents:", e)
        return Path.home() / "Documents"


if __name__ == '__main__':
    import logging

    log_dir = os.path.join(_get_documents_path(),'DrCamApp','ApplicationLogs')
    log_file_path = os.path.join(log_dir, "app.log")

    # Create directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    sys.stdout = open(log_file_path, "a", buffering=1)
    sys.stderr = open(log_file_path, "a", buffering=1)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )

    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Launch the UI window
    webview.create_window("Doctor's Agency Login", "http://127.0.0.1:5000", width=2000, height=800)
    webview.start()

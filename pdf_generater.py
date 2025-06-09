import os
import shutil
from pathlib import Path


from flask import render_template, jsonify, request, send_file
from fpdf import FPDF

from contants.queries import Queries
from db_config.database_service import DatabaseService
from models.profile_model import ProfileModel

prefilled_image_list = []
TEMP_IMAGE_DIR = os.path.join(os.getcwd(), "temp_images", "captures")  # Change path as needed
TEMP_PDF_DIR = os.path.join(os.getcwd(), "temp_images", "pdfs")
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

def register_pdf_route(app):
 db=DatabaseService()

 @app.route("/pdf_gen/<int:patient_id>/<string:patient_name>")
 def pdf_generate(patient_id,patient_name):
    profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
    if (profile and profile.agency_name):
        agency_name = profile.agency_name
    else:
        agency_name = 'Mex Enterprise'

    get_all_patient_images(patient_id,patient_name)
    return render_template("pdf_generater.html",agency_name=agency_name,files=prefilled_image_list)

 def get_all_patient_images(patient_id, patient_name):
    global prefilled_image_list
    prefilled_image_list.clear()

    # Ensure temp_images/captures exists
    temp_path = os.path.join(app.root_path, 'temp_images', 'captures')
    os.makedirs(temp_path, exist_ok=True)

    # Get DB image filenames
    patient_images = db.custom_query(
        Queries.GET_ALL_PATIENT_IMAGES,
        from_map=lambda row: row["imageBase64"],
        args=[patient_id]
    )

    # Path where actual images are stored
    image_path = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'images')

    for filename in patient_images:
        src_file = os.path.join(image_path, filename)
        dst_file = os.path.join(temp_path, filename)
        try:
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                prefilled_image_list.append(filename)
        except Exception as e:
            print(f"Failed to copy image: {e}")

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

 @app.route("/api/selected_images", methods=["POST"])
 def handle_selected_images():
     try:
         data = request.get_json()
         selected_images = data.get("images")
         count_per_page = int(data.get("count_per_page", 1))

         profile = db.query_by_column("doctor_profile", "id", 1, ProfileModel.from_map)
         agency_name = profile.agency_name if profile and profile.agency_name else "Mex Enterprise"

         if not selected_images or not isinstance(selected_images, list):
             return jsonify({"status": "fail", "message": "Invalid or missing image list"}), 400

         pdf = FPDF(orientation='P', unit='mm', format='A4')
         pdf.set_auto_page_break(auto=True, margin=10)

         total_images = len(selected_images)
         images_per_page = count_per_page
         images_per_row = 2 if count_per_page > 1 else 1
         image_w = 90 if images_per_row == 2 else 180
         image_h = 70  # Adjusted for 2 rows

         for i in range(0, total_images, images_per_page):
             pdf.add_page()
             pdf.set_font("Arial", "B", 14)
             pdf.set_text_color(51, 153, 204)
             pdf.cell(0, 10, agency_name, ln=True, align="C")

             page_images = selected_images[i:i + images_per_page]

             for idx, img_name in enumerate(page_images):
                 image_path = os.path.join(TEMP_IMAGE_DIR, img_name)
                 if os.path.exists(image_path):
                     row = idx // images_per_row
                     col = idx % images_per_row
                     x = 10 + (image_w + 10) * col
                     y = 25 + (image_h + 10) * row
                     pdf.image(image_path, x=x, y=y, w=image_w, h=image_h)
                 else:
                     print(f"Image not found: {image_path}")

         # Save PDF
         pdf_filename = f"selected_images.pdf"
         pdf_path = os.path.join(TEMP_PDF_DIR, pdf_filename)
         pdf.output(pdf_path)

         return send_file(
             pdf_path,
             as_attachment=True,
             download_name=pdf_filename,
             mimetype="application/pdf"
         )

     except Exception as e:
         return jsonify({"status": "error", "message": str(e)}), 500
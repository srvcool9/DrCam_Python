import os
import shutil
import subprocess
from pathlib import Path
from flask import render_template, jsonify, request, send_file
from contants.queries import Queries
from db_config.database_service import DatabaseService
from models.profile_model import ProfileModel
import os
import io
from flask import request, jsonify, send_file
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter

prefilled_image_list = []
TEMP_IMAGE_DIR = ""
TEMP_PDF_DIR = ""


def register_pdf_route(app):
 db=DatabaseService()

 def ensure_temp_folder(temp_path):
     os.makedirs(temp_path, exist_ok=True)

 def copy_pdf_to_temp(original_pdf_path, temp_path):
     ensure_temp_folder(temp_path)

     file_name = os.path.basename(original_pdf_path)
     temp_pdf_path = os.path.join(temp_path, file_name)

     # Only copy if not already copied
     if not os.path.exists(temp_pdf_path):
         shutil.copy2(original_pdf_path, temp_pdf_path)

     return temp_pdf_path

 @app.route("/pdf_gen/<int:patient_id>/<string:patient_name>")
 def pdf_generate(patient_id,patient_name):
    global TEMP_IMAGE_DIR,TEMP_PDF_DIR
    TEMP_IMAGE_DIR = os.path.join(_get_documents_path(), 'DrCamApp', patient_name, 'images')
    TEMP_PDF_DIR=os.path.join(_get_documents_path(), 'DrCamApp', patient_name, "pdfs")
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

         if not selected_images:
             return jsonify({"status": "fail"}), 400

         pdf = FPDF()
         pdf.set_auto_page_break(True, 10)

         images_per_row = 2 if count_per_page > 1 else 1
         image_w = 90 if images_per_row == 2 else 180
         image_h = 70

         for i in range(0, len(selected_images), count_per_page):
             pdf.add_page()
             pdf.set_font("Arial", "B", 14)
             pdf.cell(0, 10, agency_name, ln=True, align="C")

             page_images = selected_images[i:i + count_per_page]

             for idx, img_name in enumerate(page_images):
                 image_path = os.path.join(TEMP_IMAGE_DIR, img_name)
                 if os.path.exists(image_path):
                     row = idx // images_per_row
                     col = idx % images_per_row
                     x = 10 + (image_w + 10) * col
                     y = 30 + (image_h + 10) * row
                     pdf.image(image_path, x, y, image_w, image_h)

         # Save PREVIEW PDF
         ensure_temp_folder(TEMP_PDF_DIR)
         preview_path = os.path.join(TEMP_PDF_DIR, "preview.pdf")

         # temp_pdf_path = os.path.join(app.root_path, 'temp_pdf')
         # send_file(temp_pdf_path, as_attachment=False)
         # pdf_path = copy_pdf_to_temp(temp_pdf_path,preview_path)
         pdf.output(preview_path)

         return send_file(preview_path, as_attachment=False)

     except Exception as e:
         return jsonify({"error": str(e)}), 500



 @app.route("/api/finalize_pdf", methods=["POST"])
 def finalize_pdf():
     data = request.get_json()
     comment = data.get("comment", "")

     preview_path = os.path.join(TEMP_PDF_DIR, "preview.pdf")
     final_path = os.path.join(TEMP_PDF_DIR, "final_report.pdf")

     if not os.path.exists(preview_path):
         return jsonify({"error": "Preview PDF not found"}), 400

     # ---------------------------------------------------------
     # STEP 1: Create comment page PDF in memory
     # ---------------------------------------------------------
     pdf = FPDF()
     pdf.add_page()
     pdf.set_auto_page_break(True, margin=15)
     pdf.set_font("Arial", size=12)

     pdf.multi_cell(0, 8, "Doctor Comments:")
     pdf.ln(3)

     # FPDF supports only latin-1
     safe_comment = comment.encode("latin-1", "replace").decode("latin-1")
     pdf.multi_cell(0, 8, safe_comment)

     pdf.ln(10)
     pdf.set_font("Arial", "B", 12)
     pdf.cell(0, 10, "Attached Medical Images", ln=True)

     comments_pdf_bytes = pdf.output(dest="S")

     comments_stream = io.BytesIO(comments_pdf_bytes)

     # Load the generated comment PDF
     comment_reader = PdfReader(comments_stream)

     # ---------------------------------------------------------
     # STEP 2: Merge comment page + preview pages
     # ---------------------------------------------------------
     writer = PdfWriter()

     # Add comment page
     writer.add_page(comment_reader.pages[0])

     # Add preview pages
     preview_reader = PdfReader(preview_path)
     for page in preview_reader.pages:
         writer.add_page(page)

     # ---------------------------------------------------------
     # STEP 3: Save final PDF
     # ---------------------------------------------------------
     with open(final_path, "wb") as fp:
         writer.write(fp)

     # ---------------------------------------------------------
     # STEP 4: Send final PDF
     # ---------------------------------------------------------
     return send_file(
         final_path,
         as_attachment=True,
         download_name="Final_Report.pdf",
         mimetype="application/pdf"
     )

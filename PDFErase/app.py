# app.py
from flask import Flask, render_template, request, send_file, jsonify
import fitz  # PyMuPDF
import os
import base64
import io

app = Flask(__name__, static_folder='static', static_url_path='/static')

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


# Save uploaded original PDF so server can rebuild from it later.
@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    fname = f.filename
    save_path = os.path.join(UPLOAD_FOLDER, fname)
    f.save(save_path)

    # get page count to help front-end UI if needed
    doc = fitz.open(save_path)
    pages = doc.page_count
    doc.close()
    return jsonify({"filename": fname, "pages": pages})


# Accept edited pages as data URLs and rebuild a new PDF.
# JSON body: { "filename": "original.pdf", "edited": [ {"page": 0, "data": "data:image/png;base64,..."}, ... ] }
@app.route("/save", methods=["POST"])
def save():
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "no json"}), 400
    fname = payload.get("filename")
    edited = payload.get("edited", [])

    original_path = os.path.join(UPLOAD_FOLDER, fname)
    if not os.path.exists(original_path):
        return jsonify({"error": "original not found"}), 400

    src = fitz.open(original_path)
    out = fitz.open()  # new pdf

    # Build a dict for quick lookup
    edited_map = {int(e["page"]): e["data"] for e in edited}

    for pno in range(src.page_count):
        page = src.load_page(pno)
        rect = page.rect  # use original page size

        if pno in edited_map:
            # insert edited image as the whole page
            data_url = edited_map[pno]
            header, b64 = data_url.split(",", 1)
            image_bytes = base64.b64decode(b64)
            # create a new page with same dims and insert the image to cover full page
            new_page = out.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(new_page.rect, stream=image_bytes)
        else:
            # preserve original page by converting it into an image and inserting
            # (this avoids complex copy semantics and preserves visual)
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            img_bytes = pix.tobytes("png")
            new_page = out.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes)

    out_path = os.path.join(UPLOAD_FOLDER, "edited_output.pdf")
    out.save(out_path)
    src.close()
    out.close()
    return send_file(out_path, as_attachment=True, download_name="edited.pdf")


if __name__ == "__main__":
    app.run(debug=True)

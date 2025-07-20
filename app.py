from flask import Flask, render_template, request, jsonify, send_from_directory
import fitz  # PyMuPDF
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def clean_pdf(input_path, output_path, remove_text="Nikhil Saroha"):
    doc = fitz.open(input_path)
    for page in doc:
        words = page.get_text("words")
        page.clean_contents()
        for x0, y0, x1, y1, word, *_ in words:
            if not word.strip() or remove_text.lower() in word.lower():
                continue
            font_size = max(8, int(y1 - y0))
            page.insert_textbox(
                fitz.Rect(x0, y0, x1, y1),
                word,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
                align=0
            )
        for img in page.get_images(full=True):
            xref = img[0]
            info = doc.extract_image(xref)
            width, height = info["width"], info["height"]
            if width < 50 and height < 50:
                page.delete_image(xref)
    doc.save(output_path)


def change_red_green_to_black(input_path, output_path):
    doc = fitz.open(input_path)
    for page in doc:
        spans_to_fix = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        color = span.get("color", 0)
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b = color & 255
                        # Detect red or green text
                        if (r > 150 and g < 100 and b < 100) or (g > 150 and r < 100 and b < 100):
                            spans_to_fix.append(span)
        for span in spans_to_fix:
            page.add_redact_annot(span["bbox"], fill=(1, 1, 1))
        if spans_to_fix:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            for span in spans_to_fix:
                x0, y0, x1, y1 = span["bbox"]
                page.insert_text(
                    (x0, y1 - span["size"]),
                    span["text"],
                    fontname="helv",
                    fontsize=span["size"],
                    color=(0, 0, 0),
                )
    doc.save(output_path)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            if "pdf" not in request.files:
                return jsonify({"error": "No PDF uploaded"}), 400

            pdf_file = request.files["pdf"]

            # Secure original filename
            filename = secure_filename(pdf_file.filename)
            name, ext = os.path.splitext(filename)
            if not ext:
                ext = ".pdf"

            # Define paths dynamically
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            cleaned_path = os.path.join(OUTPUT_FOLDER, f"{name}_step1{ext}")
            final_name = f"{name}_cleaned{ext}"
            final_path = os.path.join(OUTPUT_FOLDER, final_name)

            # Save uploaded PDF
            pdf_file.save(input_path)

            # Step 1: Clean PDF
            clean_pdf(input_path, cleaned_path)

            # Step 2: Change red/green text to black
            change_red_green_to_black(cleaned_path, final_path)

            # Return JSON with dynamic download URL
            return jsonify({"download_url": f"/download/{final_name}"})

        except Exception as e:
            print("Error during processing:", e)
            return jsonify({"error": str(e)}), 500

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT automatically
    app.run(host="0.0.0.0", port=port)

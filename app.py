from flask import Flask, render_template, request, jsonify, send_from_directory
import fitz  # PyMuPDF
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
FONT_PATH = 'NotoSansDevanagari-Regular.ttf'  # Font file must be in same folder as app.py
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Register the Hindi font globally
hindi_font_name = "noto"
if os.path.exists(FONT_PATH):
    try:
        hindi_font = fitz.Font(file=FONT_PATH)  # Create a Font object
        print("Hindi font loaded successfully.")
    except Exception as e:
        hindi_font = None
        print("Failed to load Hindi font. Falling back to Helvetica:", e)
else:
    hindi_font = None
    print(f"Warning: {FONT_PATH} not found. Falling back to Helvetica (Hindi may break).")

def process_pdf(input_path, output_path):
    doc = fitz.open(input_path)

    for page in doc:
        spans_to_replace = []

        # Loop through text blocks
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        size = span.get("size", 0)
                        color = span.get("color", 0)

                        # Extract RGB from integer color value
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b = color & 255

                        # Remove watermark text (as before)
                        if (
                            "prateek" in text.lower()
                            or "shivalik" in text.lower()
                            or "android app" in text.lower()
                            or size > 40
                        ):
                            x0, y0, x1, y1 = span["bbox"]
                            page.add_redact_annot((x0, y0, x1, y1), fill=(1, 1, 1))
                            continue

                        # Detect red or green text (including Hindi)
                        if (r > 150 and g < 100 and b < 100) or (g > 150 and r < 100 and b < 100):
                            spans_to_replace.append(span)

        # Apply redaction to remove only the spans (red/green text)
        for span in spans_to_replace:
            x0, y0, x1, y1 = span["bbox"]
            page.add_redact_annot((x0, y0, x1, y1), fill=(1, 1, 1))

        if spans_to_replace:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            for span in spans_to_replace:
                x0, y0, x1, y1 = span["bbox"]
                # Reinsert the same text in **black** at the same position
                page.insert_text(
                    (x0, y1 - span["size"]),
                    span["text"],
                    # fontname="helv",  # Use built-in Helvetica (supports Hindi if embedded)
                    fontsize=span["size"],
                    color=(0, 0, 0),
                )

        # Keep background as is (no forced white fill this time)

    doc.save(output_path)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            if "pdf" not in request.files:
                return jsonify({"error": "No PDF uploaded"}), 400

            pdf_file = request.files["pdf"]
            filename = secure_filename(pdf_file.filename)
            name, ext = os.path.splitext(filename)
            if not ext:
                ext = ".pdf"

            input_path = os.path.join(UPLOAD_FOLDER, filename)
            final_name = f"{name}_cleaned{ext}"
            final_path = os.path.join(OUTPUT_FOLDER, final_name)

            pdf_file.save(input_path)

            # Clean and fix PDF
            process_pdf(input_path, final_path)

            return jsonify({"download_url": f"/download/{final_name}"})

        except Exception as e:
            print("Error during processing:", e)
            return jsonify({"error": str(e)}), 500

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

from flask import Flask, render_template, request, jsonify, send_from_directory
import fitz  # PyMuPDF
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def process_pdf(input_path, output_path):
    doc = fitz.open(input_path)

    for page in doc:
        spans_to_fix = []  # store text spans that need color change

        # Loop through all text blocks
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].lower()
                        size = span.get("size", 0)
                        color = span.get("color", 0)
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b = color & 255

                        # Check if text is a watermark (remove it)
                        if (
                            "prateek" in text
                            or "shivalik" in text
                            or "android app" in text
                            or size > 40  # diagonal watermark
                        ):
                            x0, y0, x1, y1 = span["bbox"]
                            page.add_redact_annot((x0, y0, x1, y1), fill=(1, 1, 1))
                            continue

                        # Convert red or green text (including Hindi) to black
                        if (r > 150 and g < 100 and b < 100) or (g > 150 and r < 100 and b < 100):
                            spans_to_fix.append(span)

        # Apply redaction for watermark text/images
        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.alpha or pix.n - pix.alpha > 0 or pix.width > 400:
                page.delete_image(xref)
            pix = None

        # Actually apply redactions (deletes watermarks)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

        # Re-insert fixed text spans (red/green -> black)
        for span in spans_to_fix:
            x0, y0, x1, y1 = span["bbox"]
            page.add_redact_annot((x0, y0, x1, y1), fill=(1, 1, 1))
        if spans_to_fix:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            for span in spans_to_fix:
                x0, y0, x1, y1 = span["bbox"]
                page.insert_text(
                    (x0, y1 - span["size"]),
                    span["text"],
                    fontname="helv",
                    fontsize=span["size"],
                    color=(0, 0, 0),  # Always black
                )

        # Ensure full page white background
        page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))

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

            # Clean PDF
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

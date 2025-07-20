import fitz  # PyMuPDF

input_pdf = "DSSSB_Cleaned_Final.pdf"
output_pdf = "output_black.pdf"

def change_red_green_to_black(input_path, output_path):
    doc = fitz.open(input_path)

    for page in doc:
        spans_to_fix = []

        # Collect spans with red/green text
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        color = span.get("color", 0)
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b = color & 255

                        if (r > 150 and g < 100 and b < 100) or (g > 150 and r < 100 and b < 100):
                            spans_to_fix.append(span)

        # Redact all old text
        for span in spans_to_fix:
            page.add_redact_annot(span["bbox"], fill=(1, 1, 1))

        if spans_to_fix:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            # Write new text in black using a standard font
            for span in spans_to_fix:
                x0, y0, x1, y1 = span["bbox"]
                page.insert_text(
                    (x0, y1 - span["size"]),
                    span["text"],
                    fontname="helv",  # Use built-in Helvetica instead of span["font"]
                    fontsize=span["size"],
                    color=(0, 0, 0),
                )

    doc.save(output_path)
    print(f"Processed PDF saved as {output_path}")

change_red_green_to_black(input_pdf, output_pdf)

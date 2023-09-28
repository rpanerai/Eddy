import fitz


def PNGFrontPageFromPDF(pdf_file):
    pdf = fitz.open(pdf_file)
    return pdf[0].get_pixmap().tobytes()

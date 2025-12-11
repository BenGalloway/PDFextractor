import fitz # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import sys

def convert_to_searchable_pdf(input_pdf_path):
    """
    Checks if a PDF is searchable. If not, performs OCR on the first page 
    and saves the output as a new searchable PDF.
    """
    if not os.path.exists(input_pdf_path):
        print(f"🛑 Error: File not found at path: {input_pdf_path}")
        return None

    # Check the first page for text (quick check)
    try:
        doc = fitz.open(input_pdf_path)
        page = doc[0]
        text_on_page = page.get_text()
        doc.close()

        if len(text_on_page.strip()) > 100:
            print(f"✅ File is already searchable. Proceeding to extraction.")
            return input_pdf_path

    except Exception as e:
        print(f"Error reading PDF with fitz: {e}")
        return None

    # If we reached here, the PDF is likely scanned/unsearchable. Perform OCR.
    print(f"⚠️ File is unsearchable. Performing OCR on Page 1...")

    output_pdf_path = f"{os.path.basename(input_pdf_path).replace('.pdf', '')}_OCR_Layer.pdf"
    
    try:
        # Use Tesseract's built-in PDF output functionality for the OCR layer
        pytesseract.pytesseract.tesseract_cmd = 'tesseract'
        
        # 1. Convert the first page to a high-res image using PyMuPDF (fitz)
        doc = fitz.open(input_pdf_path)
        page = doc[0]
        
        # Define the rendering matrix (300 DPI) for a high-quality image
        matrix = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("ppm")
        image = Image.open(io.BytesIO(img_data))
        
        # 2. Run Tesseract on the image and output a PDF with the hidden text layer
        pdf_data = pytesseract.image_to_pdf_or_hocr(image, lang='eng', extension='pdf')
        
        with open(output_pdf_path, 'wb') as f:
            f.write(pdf_data)

        print(f"✅ OCR Success! Searchable PDF saved as: {output_pdf_path}")
        doc.close()
        return output_pdf_path

    except pytesseract.TesseractNotFoundError:
        print("🛑 Tesseract is not installed or not in your PATH. Did you run 'sudo apt install tesseract-ocr'?")
        return None
    except Exception as e:
        print(f"🛑 Error during OCR processing: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_ocr.py <path/to/unsearchable_pdf>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    convert_to_searchable_pdf(pdf_path)
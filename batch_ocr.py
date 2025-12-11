import fitz # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import sys
import glob

def convert_to_searchable_pdf(input_pdf_path):
    """
    Checks if a PDF is searchable. If not, performs OCR on the first page 
    and saves the output as a new searchable PDF.
    """
    filename = os.path.basename(input_pdf_path)
    if not os.path.exists(input_pdf_path):
        print(f"🛑 Error: File not found at path: {filename}. Skipping.")
        return None

    try:
        doc = fitz.open(input_pdf_path)
        page = doc[0]
        text_on_page = page.get_text()
        doc.close()

        # Check for sufficient text to determine searchability
        if len(text_on_page.strip()) > 100 and "_OCR_Layer.pdf" not in filename:
            print(f"  -> File appears searchable. Skipping OCR.")
            return input_pdf_path

    except Exception as e:
        print(f"  -> Error reading PDF with fitz: {e}. Assuming unsearchable and proceeding to OCR.")
        pass # Proceed to OCR if read fails

    # Prevent running OCR on a file that has already been OCR'd
    if "_OCR_Layer.pdf" in filename:
        print(f"  -> File already processed (contains '_OCR_Layer.pdf'). Skipping.")
        return None
    
    # If we reached here, the PDF is likely scanned/unsearchable. Perform OCR.
    print(f"  -> Performing OCR on Page 1...")

    output_pdf_path = f"{os.path.basename(input_pdf_path).replace('.pdf', '')}_OCR_Layer.pdf"
    
    try:
        pytesseract.pytesseract.tesseract_cmd = 'tesseract'
        
        doc = fitz.open(input_pdf_path)
        page = doc[0]
        
        # Define the rendering matrix (300 DPI) for a high-quality image
        matrix = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("ppm")
        image = Image.open(io.BytesIO(img_data))
        
        # Run Tesseract on the image and output a PDF with the hidden text layer
        pdf_data = pytesseract.image_to_pdf_or_hocr(image, lang='eng', extension='pdf')
        
        with open(output_pdf_path, 'wb') as f:
            f.write(pdf_data)

        print(f"  -> SUCCESS! Searchable PDF saved as: {output_pdf_path}")
        doc.close()
        return output_pdf_path

    except pytesseract.TesseractNotFoundError:
        print("🛑 Tesseract is not installed or not in your PATH. Please check Tesseract installation.")
        return None
    except Exception as e:
        print(f"🛑 Error during OCR processing for {filename}: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # --- MODE 1: Single File via Command Line Argument ---
        pdf_path = sys.argv[1]
        print(f"--- Running OCR in Single File Mode ---")
        convert_to_searchable_pdf(pdf_path)
    else:
        # --- MODE 2: Batch Process All PDFs in Folder ---
        # Find all files ending in .pdf that do *not* already contain "_OCR_Layer"
        pdf_files = [f for f in glob.glob("*.pdf") if "_OCR_Layer" not in f]
        
        if not pdf_files:
            print("--- Running OCR in Batch Mode ---")
            print("🛑 No source PDF files found in the current directory (or all have been processed).")
            sys.exit(1)
            
        print(f"--- Running OCR in Batch Mode: Found {len(pdf_files)} files ---")
        
        processed_count = 0
        for pdf_path in pdf_files:
            print(f"\nProcessing: {os.path.basename(pdf_path)}")
            if convert_to_searchable_pdf(pdf_path):
                processed_count += 1
                
        print(f"\n--- Batch OCR Process Complete ---")
        print(f"Total PDFs processed/checked successfully: {processed_count} out of {len(pdf_files)}")
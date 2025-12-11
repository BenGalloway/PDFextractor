import pdfplumber
import pandas as pd
import re
import os
import sys
import glob
from typing import Optional # <--- THE FIX: This line was missing

# Universal Stream Settings for Strategy A (Table Detection)
GENERIC_STREAM_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 7 
}

# Generic search area for Strategy A (Table Detection)
GENERIC_CROP_AREA = (20, 250, 590, 780) 

# --- REGEX STRATEGY B: The Fallback ---
# This regex looks for: (Description Text) (Space/Junk) ($Price)
PRICE_REGEX = re.compile(
    # Group 1: Description text (at least 10 chars, non-greedy)
    r"(.{10,}?)\s+" 
    # Optional: Junk words/numbers between description and price (up to 5 occurrences)
    r"(?:\S+\s+){0,5}"
    # Group 2: Price ($ followed by numbers with commas and two decimals)
    r"\$(\d{1,3}(?:,\d{3})*\.\d{2})\s*$", 
    re.MULTILINE | re.IGNORECASE
)

def get_vendor_info(filename: str) -> str:
    """Simple function to extract vendor name for the output report."""
    if 'Haskins Inc' in filename or 'Rinker' in filename:
        return 'Rinker'
    elif 'Foley' in filename:
        return 'Foley'
    else:
        # Fallback for unknown vendor name
        return os.path.basename(filename).split('_')[0].split('.')[0]

def extract_with_regex(page_text: str, filename: str) -> Optional[pd.DataFrame]:
    """Strategy B: Uses regex to find text lines ending in a price."""
    print("  -> Strategy B: Falling back to RegEx text search.")
    
    # Clean the text: split into lines and remove empty ones to improve regex matching
    lines = page_text.split('\n')
    cleaned_text = '\n'.join([line.strip() for line in lines if line.strip()])
    
    matches = PRICE_REGEX.findall(cleaned_text)

    if not matches:
        return None

    data = []
    for description_raw, price_numbers in matches:
        # Clean the description (remove numbers/junk at the very end of the description)
        description = re.sub(r'(\s+[\d,\.]{1,10}\s*)$', '', description_raw, flags=re.MULTILINE).strip()
        
        # Reconstruct the price string
        total_price = f"${price_numbers}"
        
        # Only keep records where the description is substantial
        if len(description) > 5:
             data.append({
                'Description': description,
                'Total Price': total_price
            })

    if data:
        print(f"  -> SUCCESS with RegEx! Found {len(data)} items.")
        return pd.DataFrame(data)
    else:
        return None


def extract_line_items_from_pdf(pdf_path: str):
    """
    Attempts Strategy A (Table Detection) and falls back to Strategy B (Regex Search).
    """
    filename = os.path.basename(pdf_path)
    vendor = get_vendor_info(filename)
    output_file = f"{filename.replace('.pdf', '')}_extracted.md"
    
    print(f"  -> Vendor: {vendor}. Starting extraction attempt.")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            output_df = None # Initialize output_df

            # --- STRATEGY A: TABLE DETECTION (Previous Universal Logic) ---
            print("  -> Strategy A: Attempting table detection (pdfplumber)...")
            
            use_generic_crop = (vendor == 'Rinker' or vendor == 'Foley')
            cropped_page = page.crop(GENERIC_CROP_AREA) if use_generic_crop else page
                
            table_data = cropped_page.extract_table(table_settings=GENERIC_STREAM_SETTINGS)
            
            if table_data and len(table_data) > 1:
                # Process the table data if it was found
                print("  -> Strategy A successful. Processing structured table.")
                df = pd.DataFrame(table_data)
                df = df.iloc[1:].copy() 
                df.reset_index(drop=True, inplace=True)
                
                # Column Identification Logic
                price_col_index = -1
                for i in range(df.shape[1] - 1, -1, -1):
                    col_data = df[i].astype(str)
                    currency_count = col_data.str.contains(r'(\d|\$)', na=False).sum()
                    if currency_count / len(df) > 0.5: 
                        price_col_index = i
                        break

                if price_col_index != -1:
                    desc_col_index = max(0, price_col_index - 1)
                    
                    df_filtered = df[df[price_col_index].astype(str).str.contains(r'(\d|\$)', na=False)].copy()
                    df_filtered['Description'] = df_filtered[desc_col_index].astype(str).str.replace('\n', ' ', regex=False).str.strip()
                    output_df = df_filtered[['Description', price_col_index]].copy()
                    output_df.columns = ['Description', 'Total Price']


            # --- STRATEGY B: REGEX FALLBACK ---
            if output_df is None or output_df.empty:
                page_text = page.extract_text()
                output_df = extract_with_regex(page_text, filename)
                
            
            # --- Final Output ---
            if output_df is not None and not output_df.empty:
                markdown_output = output_df.to_markdown(index=False)
                
                with open(output_file, 'w') as f:
                    f.write(markdown_output)
                
                print(f"  -> FINAL SUCCESS: Extracted {len(output_df)} items. Output saved to: {output_file}")
                return True
            else:
                print("  -> ERROR: Both Table Detection and RegEx strategies failed to find structured data.")
                return False

    except Exception as e:
        print(f"  -> An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # --- MODE 1: Single File via Command Line Argument ---
        pdf_path = sys.argv[1]
        print(f"--- Running in Single File Mode ---")
        extract_line_items_from_pdf(pdf_path)
    else:
        # --- MODE 2: Batch Process All PDFs in Folder ---
        pdf_files = glob.glob("*.pdf")
        
        if not pdf_files:
            print("--- Running in Batch Mode ---")
            print("🛑 No PDF files found in the current directory.")
            sys.exit(1)
            
        print(f"--- Running in Batch Mode: Found {len(pdf_files)} files ---")
        
        processed_count = 0
        for pdf_path in pdf_files:
            print(f"\nProcessing: {os.path.basename(pdf_path)}")
            if extract_line_items_from_pdf(pdf_path):
                processed_count += 1
                
        print(f"\n--- Batch Process Complete ---")
        print(f"Total PDFs processed successfully: {processed_count} out of {len(pdf_files)}")
import os
import glob
import sys
import fitz  # PyMuPDF
from PIL import Image
import io
import pytesseract

# Set Tesseract path if it's installed via winget (default location)
tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_cmd):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# Set tessdata prefix to our local downloaded data folder
tessdata_dir_config = f'--tessdata-dir "{os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tessdata")}"'

def ocr_pdf(pdf_path, output_md_path):
    print(f"Processing {pdf_path}...")
    try:
        # Convert PDF to list of images using PyMuPDF
        print("  Converting PDF pages to images...")
        doc = fitz.open(pdf_path)
        images = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            # Render page to an image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
    except Exception as e:
        print(f"  Error converting PDF to images: {e}")
        return

    text_content = ""
    for i, image in enumerate(images):
        print(f"  OCR page {i + 1}/{len(images)}...")
        # Use Vietnamese if installed, else fallback to eng
        try:
            text = pytesseract.image_to_string(image, lang='vie', config=tessdata_dir_config)
        except pytesseract.TesseractError:
            print("  Vietnamese lang pack not found, falling back to english.")
            text = pytesseract.image_to_string(image, lang='eng', config=tessdata_dir_config)
            
        text_content += f"\n\n<!-- Page {i + 1} -->\n\n"
        text_content += text

    # Write to Markdown file
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(text_content.strip())
    
    print(f"  Saved to {output_md_path}")

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    pdf_files = glob.glob(os.path.join(data_dir, '*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return
        
    for pdf in pdf_files:
        basename = os.path.splitext(os.path.basename(pdf))[0]
        out_md = os.path.join(data_dir, f"{basename}.md")
        ocr_pdf(pdf, out_md)
        
if __name__ == "__main__":
    main()

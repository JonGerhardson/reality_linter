import os
import subprocess
import sys

# Add scripts dir to path to allow importing check_pdf_readability
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from check_pdf_readability import check_pdf_readability

def ocr_unreadable_files(directory):
    print(f"Scanning {directory} for unreadable PDFs...")
    # This invokes the existing logic to find files with <50 chars of text
    unreadable_files = check_pdf_readability(directory)
    print(f"Found {len(unreadable_files)} files to OCR.")

    for i, file_entry in enumerate(unreadable_files, 1):
        # Clean up the filename if it has error status appended
        file_path = file_entry
        if " (" in file_path:
            file_path = file_path.split(" (")[0]
        
        if not os.path.exists(file_path):
            print(f"Skipping {file_path} (not found)")
            continue
            
        print(f"[{i}/{len(unreadable_files)}] Running OCR on: {file_path}")
        
        # Construct output path (temp file)
        output_path = file_path + ".ocr.pdf"
        
        try:
             # Run ocrmypdf with --force-ocr to fix the image-only PDF
             # --jobs 4 for parallel processing if supported/needed, though subprocess calls are serial here
            cmd = ['ocrmypdf', '--force-ocr', '--jobs', '4', file_path, output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  [SUCCESS] OCR complete.")
                os.replace(output_path, file_path)
            else:
                print(f"  [FAILED] OCR failed for {file_path}")
                print(f"  Error: {result.stderr.strip()}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                    
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OCR only unreadable PDFs found in a directory.")
    parser.add_argument("--directory", required=True, help="Directory to scan")
    args = parser.parse_args()
    
    ocr_unreadable_files(args.directory)

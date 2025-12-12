import os
import subprocess
import argparse
import sys

def run_ocr(input_path):
    files_to_process = []
    
    if os.path.isfile(input_path):
        files_to_process.append(input_path)
    elif os.path.isdir(input_path):
        for root, dirs, files in os.walk(input_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    files_to_process.append(os.path.join(root, file))
    else:
        print(f"Error: {input_path} is not a valid file or directory.")
        return

    print(f"Starting OCR on {len(files_to_process)} files...")
    
    for full_path in files_to_process:
        print(f"[PROCESSING] {full_path}...")
        
        output_path = full_path + ".ocr.pdf"
        
        try:
            # Run ocrmypdf
            # --force-ocr: Rasterize all vector content and run OCR on it.
            cmd = ['ocrmypdf', '--force-ocr', full_path, output_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[SUCCESS] OCR complete for {os.path.basename(full_path)}")
                # Replace original file
                os.replace(output_path, full_path)
                print(f"[UPDATED] Replaced original file with OCR version.")
            else:
                print(f"[FAILED] {os.path.basename(full_path)}")
                print(f"  Error: {result.stderr.strip()}")
                
        except Exception as e:
            print(f"[ERROR] Exception processing {full_path}: {str(e)}")

    print("\nOCR Batch Processing Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OCR on PDF files.")
    parser.add_argument("--input", required=True, help="Input PDF file or directory containing PDFs")
    
    args = parser.parse_args()
    
    run_ocr(args.input)

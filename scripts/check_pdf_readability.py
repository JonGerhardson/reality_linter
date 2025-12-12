import os
import subprocess
import argparse
import sys

def check_pdf_readability(directory):
    unreadable_files = []
    readable_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(root, file)
                try:
                    # Try to extract text using pdftotext
                    result = subprocess.run(['pdftotext', file_path, '-'], capture_output=True, text=True, timeout=10)
                    text = result.stdout.strip()
                    
                    # If text is empty or very short, it might be an image scan
                    if len(text) < 50:
                        unreadable_files.append(file_path)
                    else:
                        readable_files.append(file_path)
                except subprocess.TimeoutExpired:
                     unreadable_files.append(f"{file_path} (Timeout)")
                except Exception as e:
                    unreadable_files.append(f"{file_path} (Error: {str(e)})")

    return unreadable_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for unreadable PDFs.")
    parser.add_argument("--directory", required=True, help="Directory to check")
    
    args = parser.parse_args()
    
    print(f"Checking PDFs in {args.directory}...")
    unreadable = check_pdf_readability(args.directory)
    
    print("\n--- Unreadable PDFs (Likely Scanned Images) ---")
    for f in unreadable:
        print(f)
        
    print(f"\nTotal Unreadable: {len(unreadable)}")

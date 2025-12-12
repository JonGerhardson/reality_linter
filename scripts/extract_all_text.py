import os
import subprocess
import argparse
import sys

def extract_all_text(source_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    outfile.write(f"\n{'='*50}\nSTART OF FILE: {file}\nPATH: {file_path}\n{'='*50}\n")
                    
                    try:
                        # Run pdftotext and capture output
                        result = subprocess.run(['pdftotext', file_path, '-'], capture_output=True, text=True)
                        if result.returncode == 0:
                            outfile.write(result.stdout)
                        else:
                            outfile.write(f"[ERROR extracting text: {result.stderr}]")
                    except Exception as e:
                        outfile.write(f"[EXCEPTION: {str(e)}]")
                    
                    outfile.write(f"\n{'='*50}\nEND OF FILE: {file}\n{'='*50}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from all PDFs in a directory.")
    parser.add_argument("--source", required=True, help="Source directory containing PDFs")
    parser.add_argument("--output", required=True, help="Output text file path")
    
    args = parser.parse_args()
    
    print(f"Extracting text from {args.source} to {args.output}...")
    extract_all_text(args.source, args.output)
    print("Done.")

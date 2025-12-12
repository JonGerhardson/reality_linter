import os
import subprocess
import argparse
import sys

def search_pdfs(directory, keywords):
    print(f"Searching in {directory} for {keywords}")
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                path = os.path.join(root, file)
                try:
                    # Extract text using pdftotext
                    result = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True)
                    content = result.stdout.lower()
                    
                    found = []
                    for kw in keywords:
                        if kw.lower() in content:
                            found.append(kw)
                    
                    if found:
                        print(f"MATCH: {file} contains {found}")
                        # Print context for the match
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            for kw in keywords:
                                if kw.lower() in line:
                                    print(f"  Context: {line.strip()[:100]}...")
                except Exception as e:
                    print(f"Error reading {file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search for keywords in PDFs.")
    parser.add_argument("--directory", required=True, help="Directory to search")
    parser.add_argument("--keywords", nargs="+", required=True, help="Keywords to search for")
    
    args = parser.parse_args()
    
    search_pdfs(args.directory, args.keywords)

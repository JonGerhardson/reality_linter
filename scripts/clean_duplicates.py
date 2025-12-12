import re
import argparse
from difflib import SequenceMatcher
import sys

def is_similar(a, b, threshold=0.8):
    return SequenceMatcher(None, a, b).ratio() > threshold

def clean_extract(input_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return

    # Split into two main parts: Original PDF extract and Additional Findings
    separator = "==================================================\n ADDITIONAL FINDINGS \n=================================================="
    if separator not in content:
         # Try the deduplicated separator just in case it's already run
        separator = "==================================================\n ADDITIONAL FINDINGS (Deduplicated) \n=================================================="
        
    parts = content.split(separator)
    
    if len(parts) < 2:
        print("Could not split file into original and additional parts properly. Separator not found.")
        return

    original_part = parts[0]
    additional_part = parts[1]

    # 1. Get all text from original part chunks
    original_chunks = re.split(r'--- Page \d+ ---', original_part)
    original_chunks = [c.strip() for c in original_chunks if c.strip()]
    
    # 2. Parse additional part into source blocks
    additional_blocks = re.split(r'(xxx Source: .*? xxx)', additional_part)
    
    new_additional_content = []
    
    skip_count = 0
    keep_count = 0
    
    i = 1 
    while i < len(additional_blocks):
        header = additional_blocks[i]
        block_content = additional_blocks[i+1] if i+1 < len(additional_blocks) else ""
        
        is_duplicate = False
        
        # Check if this block is from full_project_text.txt or ServistarDataCenter.pdf
        if "full_project_text.txt" in header or "ServistarDataCenter.pdf" in header:
            clean_block = block_content.strip()
            
            for orig in original_chunks:
                if is_similar(clean_block, orig):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                if clean_block in original_part:
                     is_duplicate = True

        if is_duplicate:
            skip_count += 1
        else:
            keep_count += 1
            new_additional_content.append(header + block_content)
            
        i += 2

    print(f"Removed {skip_count} duplicate blocks.")
    print(f"Kept {keep_count} additional blocks.")

    # Reconstruct the file
    new_content = original_part + "==================================================\n ADDITIONAL FINDINGS (Deduplicated) \n==================================================\n" + "".join(new_additional_content)
    
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate extract file.")
    parser.add_argument("input_file", help="Path to the extract file to clean")
    args = parser.parse_args()
    
    clean_extract(args.input_file)

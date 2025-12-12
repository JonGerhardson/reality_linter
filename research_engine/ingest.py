
import os
import hashlib
import json
from pathlib import Path

DEFAULT_CANONICAL_DIR = "data/canonical"
METADATA_FILE = "data/document_metadata.json"

def compute_block_hashes(lines, block_size=10):
    hashes = []
    for i in range(0, len(lines), block_size):
        block = "".join(lines[i:i+block_size])
        block_hash = hashlib.md5(block.encode('utf-8')).hexdigest()
        hashes.append(block_hash)
    return hashes

def bake_file(input_path: Path, output_dir: Path):
    """Reads a file, adds [Lxxxx] tags, and writes to output_dir."""
    try:
        with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.readlines()
    except Exception as e:
        print(f"Error reading {input_path}: {e}")
        return None

    baked_lines = []
    # 1-based indexing for line tags to match human expectation? 
    # Spec says [L{i:04d}]. Usually 1-based is better for citations.
    for i, line in enumerate(content, start=1):
        # Ensure line ends with newline only if it's not the very last one without it, 
        # but readlines() keeps \n. We just prepend.
        baked_line = f"[L{i:04d}] {line}"
        baked_lines.append(baked_line)
    
    output_filename = input_path.stem + "_baked.txt"
    output_path = output_dir / output_filename
    
    baked_content_str = "".join(baked_lines)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(baked_content_str)
        
    # Metadata
    block_hashes = compute_block_hashes(baked_lines)
    
    # V4: Insert into Database for FTS
    # Raw content (no tags) for cleaner semantic search (optional, but good for keyword match without [L])
    raw_content = "".join(content) 
    
    from research_engine.database import insert_document_content
    insert_document_content(output_filename, raw_content, baked_content_str)
    
    return {
        "original_filename": input_path.name,
        "baked_filename": output_filename,
        "line_count": len(baked_lines),
        "block_hashes": block_hashes,
        "source_path": str(input_path.absolute())
    }

def process_directory(input_dir, canonical_dir=DEFAULT_CANONICAL_DIR):
    input_path = Path(input_dir)
    output_path = Path(canonical_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    metadata = {}
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
        except:
            pass

    # Initialize ingestion modules
    from research_engine.ingest_audio import AudioIngestor
    from research_engine.ingest_ocr import OCRIngestor
    
    audio_ingestor = AudioIngestor()
    ocr_ingestor = OCRIngestor()

    for file_path in input_path.glob("**/*"):
        if not file_path.is_file():
            continue
            
        # Skip baked/processed files
        if "_baked" in file_path.name or ".ocr.pdf" in file_path.name:
            continue
            
        suffix = file_path.suffix.lower()
        file_meta = None
        
        # Text/Markdown
        if suffix in ['.txt', '.md']:
            expected_baked = f"{file_path.stem}_baked.txt"
            if (output_path / expected_baked).exists():
                print(f"Skipping {file_path.name} (Already processed)")
                continue

            print(f"Baking Text: {file_path.name}...")
            file_meta = bake_file(file_path, output_path)

        # Audio
        elif suffix in ['.wav', '.mp3', '.m4a'] and audio_ingestor.enabled:
            print(f"Transcribing Audio: {file_path.name}...")
            transcript = audio_ingestor.transcribe(str(file_path))
            if transcript:
                # Save transcript first so we have a record
                transcript_path = file_path.with_suffix('.txt')
                # write to raw_documents? Or direct to bake?
                # Let's save a temp transcript file in the output dir to "bake" it.
                temp_txt_path = output_path / (file_path.stem + "_transcript.txt")
                with open(temp_txt_path, 'w') as f:
                    f.write(transcript)
                
                # Now bake the transcript
                file_meta = bake_file(temp_txt_path, output_path)
                # Cleanup temp? Maybe keep for debug.

        # PDF
        elif suffix == '.pdf':
            expected_baked = f"{file_path.stem}_extracted_baked.txt"
            if (output_path / expected_baked).exists():
                print(f"Skipping {file_path.name} (Already processed)")
                continue

            print(f"Processing PDF: {file_path.name}...")
            # V4 Refactor: OCRIngestor with Gemini returns text directly via process_pdf
            # The old extract_text method is merged.
            
            pdf_text = ocr_ingestor.process_pdf(str(file_path))
            
            if pdf_text:
                temp_txt_path = output_path / (file_path.stem + "_extracted.txt")
                with open(temp_txt_path, 'w') as f:
                    f.write(pdf_text)
                
                # Bake
                file_meta = bake_file(temp_txt_path, output_path)

        # Spreadsheet
        elif suffix in ['.xlsx', '.xls', '.csv']:
            expected_baked = f"{file_path.stem}_spreadsheet_baked.txt"
            if (output_path / expected_baked).exists():
                print(f"Skipping {file_path.name} (Already processed)")
                continue

            print(f"Processing Spreadsheet: {file_path.name}...")
            try:
                import pandas as pd
                if suffix == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                # Convert to markdown string
                # Check if to_markdown is available (requires tabulate usually), fallback to to_string or to_csv
                try:
                    text_content = df.to_markdown(index=False)
                except ImportError:
                    text_content = df.to_csv(index=False, sep='\t')
                
                if text_content:
                    temp_txt_path = output_path / (file_path.stem + "_spreadsheet.txt")
                    with open(temp_txt_path, 'w') as f:
                        f.write(text_content)
                    
                    file_meta = bake_file(temp_txt_path, output_path)
            except Exception as e:
                print(f"Error processing spreadsheet {file_path.name}: {e}")

        if file_meta:
            metadata[file_meta['baked_filename']] = file_meta

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Ingestion complete. Metadata saved to {METADATA_FILE}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        process_directory(sys.argv[1])
    else:
        print("Usage: python ingest.py <input_directory>")

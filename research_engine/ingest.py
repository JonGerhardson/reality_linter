
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


def generate_unique_filename(source_path: Path, content: str, suffix: str = "_baked.txt") -> str:
    """
    Generate a unique filename with parent directory and content hash.
    Format: parentdir_basename_abc123_baked.txt
    """
    # Get parent directory name (for provenance)
    parent_name = source_path.parent.name if source_path.parent.name else ""
    
    # Compute short content hash (first 6 chars of MD5)
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:6]
    
    # Build filename
    base = source_path.stem
    if parent_name and parent_name not in (".", "raw_documents"):
        return f"{parent_name}_{base}_{content_hash}{suffix}"
    else:
        return f"{base}_{content_hash}{suffix}"

def bake_file(input_path: Path, output_dir: Path, source_path: Path = None):
    """
    Reads a file, adds [Lxxxx] tags, and writes to output_dir.
    source_path: Original source file path (for filename generation with parent dir).
    """
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
    
    # Generate unique filename with parent dir + content hash
    effective_source = source_path if source_path else input_path
    output_filename = generate_unique_filename(effective_source, baked_content_str)
    output_path = output_dir / output_filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(baked_content_str)
    
    # Make read-only
    try:
        os.chmod(output_path, 0o444)
    except Exception as e:
        print(f"Warning: Could not set read-only permission on {output_filename}: {e}")
    # Metadata
    block_hashes = compute_block_hashes(baked_lines)
    
    # V4: Insert into Database for FTS
    # Raw content (no tags) for cleaner semantic search (optional, but good for keyword match without [L])
    raw_content = "".join(content) 
    
    from research_engine.database import insert_document_content, delete_embeddings_for_file, insert_chunk_embedding
    insert_document_content(output_filename, raw_content, baked_content_str)
    
    # V5: Generate chunk embeddings for semantic search
    try:
        from research_engine.embeddings import get_embedding_model, create_chunks, encode_text
        import numpy as np
        
        # Clear any existing embeddings for this file (for re-ingestion)
        delete_embeddings_for_file(output_filename)
        
        # Create chunks from baked lines
        chunks = create_chunks(baked_lines, chunk_size=50, overlap=10)
        
        if chunks:
            print(f"    [*] Generating {len(chunks)} chunk embeddings...")
            for chunk in chunks:
                embedding = encode_text(chunk['text'])
                embedding_blob = embedding.astype(np.float32).tobytes()
                
                insert_chunk_embedding(
                    filename=output_filename,
                    start_line=chunk['start_line'],
                    end_line=chunk['end_line'],
                    chunk_text=chunk['text'],
                    embedding_blob=embedding_blob
                )
            print(f"    [*] Embeddings stored for {output_filename}")
    except ImportError as e:
        print(f"    [!] Skipping embeddings (sentence-transformers not installed): {e}")
    except Exception as e:
        print(f"    [!] Error generating embeddings: {e}")
    
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

    if input_path.is_file():
        # Single file mode
        file_iterator = [input_path]
    else:
        # Directory mode
        file_iterator = input_path.glob("**/*")

    for file_path in file_iterator:
        if not file_path.is_file():
            continue
            
        # Skip baked/processed files
        if "_baked" in file_path.name or ".ocr.pdf" in file_path.name:
            continue
            
        suffix = file_path.suffix.lower()
        file_meta = None
        
        # Text/Markdown
        if suffix in ['.txt', '.md']:
            # Check for any baked file containing this stem
            existing = list(output_path.glob(f"*{file_path.stem}*_baked.txt"))
            if existing:
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
                file_meta = bake_file(temp_txt_path, output_path, file_path)
                # Cleanup temp? Maybe keep for debug.

        # PDF
        elif suffix == '.pdf':
            # Check for any baked file containing this stem
            existing = list(output_path.glob(f"*{file_path.stem}*_baked.txt"))
            if existing:
                print(f"Skipping {file_path.name} (Already processed)")
                continue

            print(f"Processing PDF: {file_path.name}...")
            # V4 Refactor: OCRIngestor with Gemini returns text directly via process_pdf
            # The old extract_text method is merged.
            
            pdf_text = ocr_ingestor.process_pdf(str(file_path))
            
            if pdf_text:
                temp_txt_path = output_path / (file_path.stem + "_extracted.txt")
                with open(temp_txt_path, 'w', encoding='utf-8') as f:
                    f.write(pdf_text)
                
                # Bake
                file_meta = bake_file(temp_txt_path, output_path, file_path)

        # Spreadsheet
        elif suffix in ['.xlsx', '.xls', '.csv']:
            # Check for any baked file containing this stem
            existing = list(output_path.glob(f"*{file_path.stem}*_baked.txt"))
            if existing:
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
                    
                    file_meta = bake_file(temp_txt_path, output_path, file_path)
            except Exception as e:
                print(f"Error processing spreadsheet {file_path.name}: {e}")

        # Word Documents
        elif suffix in ['.docx', '.doc']:
            # Check for any baked file containing this stem
            existing = list(output_path.glob(f"*{file_path.stem}*_baked.txt"))
            if existing:
                print(f"Skipping {file_path.name} (Already processed)")
                continue

            print(f"Processing Word Document: {file_path.name}...")
            try:
                from docx import Document
                doc = Document(file_path)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text_content = "\n".join(paragraphs)
                
                if text_content:
                    temp_txt_path = output_path / (file_path.stem + "_docx.txt")
                    with open(temp_txt_path, 'w') as f:
                        f.write(text_content)
                    
                    file_meta = bake_file(temp_txt_path, output_path, file_path)
            except Exception as e:
                print(f"Error processing Word document {file_path.name}: {e}")

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

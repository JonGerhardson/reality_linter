"""
Embedding module for semantic search.
Uses singleton pattern to load model once and reuse.
"""

import re
import numpy as np
from typing import List, Dict, Optional

# Lazy import to avoid loading model at module import time
_model_instance = None

def get_embedding_model():
    """Singleton pattern: returns cached model instance."""
    global _model_instance
    if _model_instance is None:
        import torch
        from sentence_transformers import SentenceTransformer
        print("[*] Loading embedding model (Qwen/Qwen3-Embedding-0.6B)...")
        
        # Try CUDA, fall back to CPU
        try:
            if torch.cuda.is_available():
                # Check for compatible capability or catch error
                device = 'cuda:1' if torch.cuda.device_count() > 1 else 'cuda:0'
                print(f"[*] Attempting to load on {device}...")
                model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', device=device)
                
                # Verify it actually works (some cards report available but fail kernels)
                try:
                    model.encode("test", convert_to_numpy=True)
                    # Use FP16 if possible
                    try:
                        model.half()
                        model.encode("test", convert_to_numpy=True)
                        print(f"[*] Embedding model verified on {device} (FP16).")
                    except:
                        model.float() # revert to fp32
                        print(f"[*] FP16 failed, using FP32 on {device}.")
                    
                    _model_instance = model
                    return _model_instance
                except Exception as e:
                    print(f"[!] CUDA runtime verification failed: {e}. Switching to CPU.")
            else:
                print("[!] CUDA not available.")
                
        except Exception as e:
            print(f"[!] CUDA initialization failed: {e}. Falling back to CPU.")
            
        print("[*] Loading on CPU (fallback)...")
        _model_instance = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', device='cpu')
        print("[*] Embedding model loaded on CPU.")
    return _model_instance


def encode_text(text: str) -> np.ndarray:
    """Encode text to embedding vector."""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.astype(np.float32)


def create_chunks(lines: List[str], chunk_size: int = 50, overlap: int = 10) -> List[Dict]:
    """
    Split lines into overlapping chunks for embedding.
    
    Args:
        lines: List of text lines (with or without [Lxxxx] tags)
        chunk_size: Number of lines per chunk
        overlap: Number of overlapping lines between chunks
    
    Returns:
        List of dicts with 'text', 'start_line', 'end_line'
    """
    chunks = []
    step = chunk_size - overlap
    
    for i in range(0, len(lines), step):
        chunk_lines = lines[i:i + chunk_size]
        if not chunk_lines:
            continue
            
        # Join lines and strip [Lxxxx] tags for cleaner embedding
        raw_text = "\n".join(chunk_lines)
        clean_text = re.sub(r'\[L\d{4}\]\s*', '', raw_text)
        
        chunks.append({
            'text': clean_text.strip(),
            'start_line': i + 1,  # 1-indexed
            'end_line': min(i + chunk_size, len(lines))
        })
    
    return chunks


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def vector_search(query_embedding: np.ndarray, embeddings: List[Dict], top_k: int = 20) -> List[Dict]:
    """
    Brute-force cosine similarity search.
    
    Args:
        query_embedding: Query vector (np.float32)
        embeddings: List of dicts from get_all_embeddings(), each with 'embedding' blob
        top_k: Number of top results to return
    
    Returns:
        List of dicts with chunk info + similarity score, sorted by score descending
    """
    results = []
    
    for row in embeddings:
        # Deserialize embedding from blob
        chunk_embedding = np.frombuffer(row['embedding'], dtype=np.float32)
        
        score = cosine_similarity(query_embedding, chunk_embedding)
        
        results.append({
            'id': row['id'],
            'filename': row['filename'],
            'start_line': row['start_line'],
            'end_line': row['end_line'],
            'chunk_text': row['chunk_text'],
            'score': score
        })
    
    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:top_k]


# English stop words for query term extraction
STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this',
    'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
    'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'about', 'into', 'over', 'after'
}


def extract_key_terms(query: str) -> List[str]:
    """
    Extract key terms from query, filtering stop words.
    Returns substantive nouns/verbs for line matching.
    """
    # Simple tokenization: split on non-alphanumeric
    tokens = re.findall(r'\b\w+\b', query.lower())
    
    # Filter stop words and short tokens
    terms = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
    
    return terms


if __name__ == "__main__":
    # Quick test
    model = get_embedding_model()
    test_embedding = encode_text("This is a test sentence about data centers.")
    print(f"Embedding shape: {test_embedding.shape}")
    print(f"Embedding dtype: {test_embedding.dtype}")


import os
import re
import base64
import io
from pdf2image import convert_from_path
from openai import OpenAI
import pytesseract
from tqdm import tqdm

from research_engine import config

# LM Studio Configuration
LM_STUDIO_URL = config.LOCAL_LLM_BASE_URL
MODEL_NAME = "qwen3-vl-2b"

OCR_PROMPT = """Extract all text from this image into markdown format. 
Preserve headers, tables, and lists. Do not describe the image, just transcribe text precisely."""


def _needs_vlm(tesseract_text: str) -> bool:
    """
    Heuristic to detect if Tesseract output looks like it mangled tables/forms.
    Returns True if VLM should be used instead.
    """
    if not tesseract_text or len(tesseract_text) < 50:
        return True
    
    lines = tesseract_text.split('\n')
    non_empty = [l for l in lines if l.strip()]
    
    if len(non_empty) < 3:
        return True
    
    # Table indicators:
    # 1. Many short lines (fragmented columns)
    short_lines = sum(1 for l in non_empty if len(l.strip()) < 15)
    if short_lines / len(non_empty) > 0.5:
        return True
    
    # 2. Lots of pipe/bar characters (table borders)
    if tesseract_text.count('|') > 10:
        return True
    
    # 3. Multiple columns of numbers (financial tables)
    number_pattern = re.compile(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?')
    number_matches = number_pattern.findall(tesseract_text)
    if len(number_matches) > 20:
        return True
    
    # 4. Excessive whitespace gaps (column separators mangled)
    big_gaps = len(re.findall(r'\s{4,}', tesseract_text))
    if big_gaps > 15:
        return True
    
    return False


class OCRIngestor:
    def __init__(self):
        self.enabled = False
        self.client = None
        
        try:
            print(f"[*] Connecting to LM Studio at {LM_STUDIO_URL}...")
            self.client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio")
            self.enabled = True
            print(f"[*] OCR ready (Tesseract + Qwen3-VL-2B fallback)")
        except Exception as e:
            print(f"[!] Failed to connect to LM Studio: {e}")
            print("[*] OCR will use Tesseract only.")

    def _extract_text_native(self, pdf_path) -> str:
        """Attempts to extract text using pdftotext (native)."""
        import subprocess
        try:
            result = subprocess.run(['pdftotext', pdf_path, '-'], capture_output=True, text=True, check=True)
            text = result.stdout.strip()
            if len(text) > 100: 
                print(f"    Native text extraction ({len(text)} chars). Skipping OCR.")
                return text
        except Exception:
            pass
        return ""

    def _image_to_base64_url(self, image, max_width=1600):
        """Convert image to base64, downscaling if needed."""
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size)
        
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"

    def _ocr_tesseract(self, image) -> str:
        """Fast Tesseract OCR."""
        return pytesseract.image_to_string(image)

    def _ocr_vlm(self, image, page_num: int, total_pages: int) -> str:
        """Slow but accurate VLM OCR for tables/forms."""
        print(f"    -> VLM fallback for page {page_num}/{total_pages}...")
        
        image_url = self._image_to_base64_url(image)
        
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": OCR_PROMPT}
                ]
            }],
            max_tokens=2048,
            temperature=0.1
        )
        
        return response.choices[0].message.content

    def _process_pdf_ocr(self, pdf_path) -> str:
        """Hybrid OCR: Tesseract first, VLM fallback for complex pages."""
        print(f"Converting PDF to images: {os.path.basename(pdf_path)}...")
        try:
            images = convert_from_path(pdf_path)
        except Exception as e:
            print(f"[!] PDF conversion failed: {e}")
            return ""
            
        full_text = []
        
        for i, image in enumerate(tqdm(images, desc="  OCR Pages", unit="pg")):
            page_num = i + 1
            try:
                # Try Tesseract first (fast)
                tess_text = self._ocr_tesseract(image)
                
                # Check if output looks good or needs VLM
                if self.enabled and _needs_vlm(tess_text):
                    tqdm.write(f"    Page {page_num}: VLM fallback")
                    output_text = self._ocr_vlm(image, page_num, len(images))
                else:
                    output_text = tess_text
                
                full_text.append(f"\n--- Page {page_num} ---\n{output_text}")
                
            except Exception as e:
                print(f"\n  [!] Failed to OCR page {page_num}: {e}")
                import traceback
                traceback.print_exc()
                
        return "\n".join(full_text)

    def process_pdf(self, pdf_path) -> str:
        """Uses native extraction, then hybrid OCR."""
        # 1. Try native text extraction first
        if config.PREFER_NATIVE_TEXT:
            native = self._extract_text_native(pdf_path)
            if native:
                return native

        # 2. Hybrid OCR
        return self._process_pdf_ocr(pdf_path)

    def extract_text(self, pdf_path):
        return self.process_pdf(pdf_path)


if __name__ == "__main__":
    import sys
    ocr = OCRIngestor()
    if len(sys.argv) > 1:
        print(ocr.process_pdf(sys.argv[1]))

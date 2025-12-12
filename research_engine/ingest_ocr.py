
import os
import time
import typing
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from research_engine import config

class OCRIngestor:
    def __init__(self):
        self.api_key = config.GOOGLE_API_KEY
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not found. Gemini OCR disabled.")
            self.enabled = False
        else:
            if genai:
                genai.configure(api_key=self.api_key)
                self.enabled = True
            else:
                print("Warning: google-generativeai package not installed.")
                self.enabled = False
                
    def _wait_for_file_active(self, file_obj):
        """Waits for a file to be processed by Gemini."""
        print(f"Waiting for {file_obj.name} to process...")
        while file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = genai.get_file(file_obj.name)
        
        if file_obj.state.name != "ACTIVE":
            raise Exception(f"File {file_obj.name} failed to process. State: {file_obj.state.name}")
        return file_obj

    def _extract_text_native(self, pdf_path) -> str:
        """Attempts to extract text using pdftotext (native). Returns empty string if failed or empty."""
        import subprocess
        try:
            # Check if pdf has text using pdftotext
            result = subprocess.run(['pdftotext', pdf_path, '-'], capture_output=True, text=True, check=True)
            text = result.stdout.strip()
            # Heuristic: If we get decent amount of text, assume it's good.
            # If it's very short, it might be a scanned PDF or just a title.
            if len(text) > 100: 
                print(f"Native text extraction successful ({len(text)} chars). Skipping OCR.")
                return text
        except Exception as e:
            print(f"Native extraction failed: {e}")
        return ""


    def process_pdf(self, pdf_path) -> str:
        """
        Uses native extraction or Gemini 2.0 to 'read' the PDF.
        """
        # 1. Try native extraction (if enabled)
        if config.PREFER_NATIVE_TEXT:
            native_text = self._extract_text_native(pdf_path)
            if native_text:
                return native_text

        if not self.enabled:
            return ""

        print(f"Uploading PDF to Gemini: {os.path.basename(pdf_path)}...")
        try:
            # Upload the PDF
            pdf_file = genai.upload_file(path=pdf_path, mime_type="application/pdf")
            pdf_file = self._wait_for_file_active(pdf_file)
        
        except Exception as e:
            print(f"Upload Error: {e}")
            return ""
            
        # Prompt for layout-aware extraction
        prompt = """
            You are "The Seer", an advanced document analysis engine.
            Your task: Extract ALL text from this PDF document into a clean, markdown-formatted representation.
            
            Guidelines:
            1. **Preserve Structure**: Keep headers, lists, and tables as Markdown.
            2. **Visual context**: If there are images/charts, briefly describe them in [brackets].
            3. **Completeness**: Do not summarize. Extract verbatim content.
            4. **Pagination**: If possible, mark page boundaries with `--- Page X ---`.
            """
            
        # User Feedback: Available models include gemini-2.5-flash-lite (10 RPM).
        model_name = "gemini-2.5-flash-lite"
            
        max_retries = 3
        current_retry = 0
            
        while current_retry < max_retries:
            try:
                print(f"Generating OCR with {model_name} (Attempt {current_retry+1})...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([pdf_file, prompt])
                    
                # Cleanup
                genai.delete_file(pdf_file.name)
                    
                # RATE LIMIT PROTECTION: Sleep 10s to respect ~6 RPM
                print("Rate limit cooldown (10s)...")
                time.sleep(10)
                    
                return response.text
                    
            except Exception as e:
                print(f"Gemini OCR Failed: {e}")
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    wait_time = 30 * (current_retry + 1)
                    print(f"Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    current_retry += 1
                else:
                    break
            
        return ""

    def extract_text(self, pdf_path):
        # Compatibility wrapper for ingest.py
        # Since process_pdf now returns text directly (via Gemini), we just return it.
        # But ingest.py expects process_pdf to return a path, then calls extract_text.
        # We need to refactor ingest.py or hack this.
        # Let's keep this method but make it return the text from the previous step if possible?
        # No, ingest.py structure is: 
        #   processed_pdf = ocr.process_pdf(path) -> returns path
        #   text = ocr.extract_text(processed_pdf) -> returns text
        #
        # We should update this class to return the *original* path in process_pdf (as a dummy)
        # and do the actual work in extract_text?
        # OR better: The "process_pdf" step in ingest.py was meant for file conversion.
        # Let's verify ingest.py logic.
        return self.process_pdf(pdf_path)

if __name__ == "__main__":
    import sys
    ocr = OCRIngestor()
    if len(sys.argv) > 1:
        print(ocr.process_pdf(sys.argv[1]))

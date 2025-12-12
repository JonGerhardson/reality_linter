
import os
import time
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from research_engine import config

class AudioIngestor:
    def __init__(self):
        self.api_key = config.GOOGLE_API_KEY
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not found. Audio ingestion disabled.")
            self.enabled = False
        else:
            if genai:
                genai.configure(api_key=self.api_key)
                self.enabled = True
            else:
                print("Warning: google-generativeai package not installed.")
                self.enabled = False

    def transcribe(self, audio_path):
        if not self.enabled:
            return None

        print(f"Uploading {os.path.basename(audio_path)}...")
        try:
            audio_file = genai.upload_file(path=audio_path)
            
            # Wait for processing
            print("Processing audio file...")
            while audio_file.state.name == "PROCESSING":
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)

            if audio_file.state.name == "FAILED":
                print("Audio processing failed.")
                return None
                
        except Exception as e:
            print(f"Upload/Processing Error: {e}")
            return None

        prompt = """
        You are "The Listener". Transcribe this audio recording (City Council Meeting).
        
        Guidelines:
        1.  **High-Fidelity Diarization**: There are many distinct speakers (Council Members, Mayor, Public).
            -   **Do NOT merge voices**. Use Speaker A, B, C, D, E, F... as needed.
            -   **Names**: If a speaker is named (e.g., during Roll Call or "Councilor Smith"), USE THE NAME.
        2.  **Verbatim**: Capture every word, including stutters/corrections.
        3.  **Timestamps**: Mark `[T00:mm:ss]` at EVERY speaker turn.
        4.  **Formatting**: Markdown.
        """

        # Retry logic
        max_retries = 3
        current_retry = 0
            
        # User Feedback: Available models include gemini-2.5-flash-lite (10 RPM).
        # We use it for higher throughput.
        model_name = 'gemini-2.5-flash-lite'
            
        while current_retry < max_retries:
            try:
                print(f"Transcribing with {model_name} (Attempt {current_retry+1})...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([prompt, audio_file])
                transcript = response.text
                
                # Cleanup
                genai.delete_file(audio_file.name)
                    
                # RATE LIMIT PROTECTION: Sleep 10s to respect ~6 RPM (conservative for 10 limit)
                print("Rate limit cooldown (10s)...")
                time.sleep(10)
                    
                return transcript
                    
            except Exception as e:
                print(f"Transcription Error: {e}")
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    wait_time = 30 * (current_retry + 1)
                    print(f"Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    current_retry += 1
                else:
                    print("Non-retriable error.")
                    break
            
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    
    ai = AudioIngestor()
    print(ai.transcribe(args.file))

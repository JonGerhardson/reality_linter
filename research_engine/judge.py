
import os
import json
import re
from pathlib import Path
from difflib import SequenceMatcher

# Placeholder for LLM client. In a real scenario, use openai or anthropic SDK.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from research_engine import config

DEFAULT_CANONICAL_DIR = "data/canonical"

class Judge:
    def __init__(self, canonical_dir=DEFAULT_CANONICAL_DIR):
        self.canonical_dir = Path(canonical_dir)
        
        # Primary: OpenAI
        self.openai_client = None
        if OpenAI and config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            
        # Falback: Google Gemini
        self.gemini_enabled = False
        if genai and config.GOOGLE_API_KEY:
            try:
                genai.configure(api_key=config.GOOGLE_API_KEY)
                self.gemini_enabled = True
            except Exception as e:
                # Silently fail or log?
                pass
        
        # Local LLM (OpenAI Compatible)
        self.local_client = None
        if OpenAI and config.LOCAL_LLM_BASE_URL:
             # We use a dummy key because local servers (Ollama/LMStudio) often ignore it or requires "lm-studio"
            self.local_client = OpenAI(base_url=config.LOCAL_LLM_BASE_URL, api_key="lm-studio")

    def _read_lines(self, filename: str, start_line: int, end_line: int):
        """Step 1: Existence Check (File I/O)"""
        file_path = self.canonical_dir / filename
        if not file_path.exists():
            return None, "File not found"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return None, f"Error reading file: {e}"
        
        # Adjust 1-based start_line to 0-based index
        # And end_line is inclusive
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return None, f"Lines {start_line}-{end_line} out of bounds (file has {len(lines)} lines)"
            
        # Slicing: start-1 to end
        snippet_lines = lines[start_line-1 : end_line]
        snippet_text = "".join(snippet_lines)
        return snippet_text, None

    def _normalize_text(self, text: str) -> str:
        """Removes [Lxxxx] tags and newlines for fuzzy matching"""
        # Remove tags like [L0012]
        text_no_tags = re.sub(r'\[L\d{4}\]\s*', '', text)
        # Collapse whitespace/newlines into single spaces
        return " ".join(text_no_tags.split())

    def _check_quote_match(self, text: str, quote: str, threshold: float = 0.8):
        """Step 2: Quote Match (Fuzzy & Smart Ellipsis)"""
        if not quote:
            return False, 0.0

        # Normalize both the evidence (text) and the agent's quote
        # We strip tags to ensure [Lxxxx] doesn't break sentences.
        clean_text = self._normalize_text(text).lower()
        clean_quote = self._normalize_text(quote).lower()

        # Check 1: Smart Ellipsis (Deterministic)
        # If quote contains '...', verify segments appear in order
        if "..." in clean_quote:
            segments = [s.strip() for s in clean_quote.split("...") if s.strip()]
            current_pos = 0
            all_found = True
            for seg in segments:
                # Find seg starting from current_pos
                found_at = clean_text.find(seg, current_pos)
                if found_at == -1:
                    all_found = False
                    break
                # Advance position
                current_pos = found_at + len(seg)
            
            if all_found:
                return True, 1.0

        # Check 2: Exact substring match on cleaned text
        if clean_quote in clean_text:
            return True, 1.0
        
        # Check 3: Fuzzy match on cleaned text
        matcher = SequenceMatcher(None, clean_text, clean_quote)
        match = matcher.find_longest_match(0, len(clean_text), 0, len(clean_quote))
        
        # Calculate score based on how much of the QUOTE was found
        if len(clean_quote) == 0:
            return False, 0.0
            
        score = match.size / len(clean_quote)
        return score >= threshold, score

    def _call_openai(self, prompt_text):
        if not self.openai_client: return None
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"}
            )
            return self._parse_json_response(response.choices[0].message.content)
        except Exception as e:
            return {"supported": False, "reason": f"OpenAI Error: {e}", "confidence": 0.0}, 0.0

    def _call_gemini(self, prompt_text):
        if not self.gemini_enabled: return None
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            response = model.generate_content(prompt_text + "\nReturn RAW JSON.")
            return self._parse_json_response(response.text)
        except Exception as e:
             return {"supported": False, "reason": f"Gemini Error: {e}", "confidence": 0.0}, 0.0

    def _call_local_llm(self, prompt_text):
        if not self.local_client: return None
        try:
             # Local models might not support JSON mode perfectly, but we ask for it.
             # Using a generic model name 'local-model' as most servers map it to the loaded model.
            response = self.local_client.chat.completions.create(
                model="local-model",
                messages=[{"role": "user", "content": prompt_text + "\nRespond strictly in JSON."}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return self._parse_json_response(response.choices[0].message.content)
        except Exception as e:
            return {"supported": False, "reason": f"Local LLM Error: {e}", "confidence": 0.0}, 0.0

    def _check_semantic_support(self, claim: str, text: str):
        """Step 3: Semantic Check (Consensus)"""
        
        prompt_text = f"""
        You are an impartial Judge. Verify if the provided text supports the claim.
        Text: "{text}"
        Claim: "{claim}"
        
        Respond strictly in JSON:
        {{
          "supported": boolean,
          "reason": "short explanation",
          "confidence": float (0.0-1.0)
        }}
        """
        
        # Parallel Execution (simulated here)
        result_gemini = self._call_gemini(prompt_text)
        result_local = self._call_local_llm(prompt_text)
        
        # Priority: Local > OpenAI > Gemini (Cost/Privacy preference)
        # Or Consensus? The roadmap implied cost savings, so let's prefer Local if available, 
        # but the prompt implies "Verification", so we might want consensus if multiple are enabled.
        # For V2, let's treat Local as a primary provider if enabled.
        
        results = [r for r in [result_local, result_openai, result_gemini] if r is not None]
        
        if not results:
            return {"supported": "unknown", "reason": "No LLM configured (Local/OpenAI/Gemini)"}, 0.0
            
        # If we have only one result, return it
        if len(results) == 1:
            return results[0]

        # Consensus Logic (The Jury)
        # Simple Majority Vote
        votes_supported = 0
        votes_rejected = 0
        reasons = []
        total_confidence = 0
        
        for res, conf in results:
            if res.get("supported", False):
                votes_supported += 1
            else:
                votes_rejected += 1
            reasons.append(f"{res.get('reason')} ({conf:.2f})")
            total_confidence += conf
            
        avg_confidence = total_confidence / len(results)
        combined_reason = " | ".join(reasons)
        
        if votes_supported > votes_rejected:
             return {"supported": True, "reason": f"Consensus Approved: {combined_reason}", "confidence": avg_confidence}, avg_confidence
        elif votes_rejected > votes_supported:
             return {"supported": False, "reason": f"Consensus Rejected: {combined_reason}", "confidence": avg_confidence}, avg_confidence
        else:
             # Tie (Hung Jury)
             return {"supported": False, "reason": f"HUNG JURY: {combined_reason}", "confidence": 0.5}, 0.5

        # 2. Consensus Logic (The Jury)
        # Both verified?
        openai_res, openai_conf = result_openai
        gemini_res, gemini_conf = result_gemini
        
        openai_sup = openai_res.get("supported", False)
        gemini_sup = gemini_res.get("supported", False)
        
        if openai_sup and gemini_sup:
            # UNANIMOUS SUPPORT
            avg_conf = (openai_conf + gemini_conf) / 2
            combined_reason = f"Consensus Reached. OpenAI: {openai_res.get('reason')} | Gemini: {gemini_res.get('reason')}"
            return {"supported": True, "reason": combined_reason, "confidence": avg_conf}, avg_conf
            
        elif not openai_sup and not gemini_sup:
            # UNANIMOUS REJECTION
            combined_reason = f"Consensus Rejection. OpenAI: {openai_res.get('reason')} | Gemini: {gemini_res.get('reason')}"
            return {"supported": False, "reason": combined_reason, "confidence": 1.0}, 1.0
            
        else:
            # HUNG JURY (Disagreement)
            # Conservative approach: If one says FALSE, we treat it as suspiciously FALSE or review needed.
            # For "Trust-But-Verify", we default to False if there is doubt.
            combined_reason = f"HUNG JURY (Disagreement). OpenAI({openai_sup}): {openai_res.get('reason')} | Gemini({gemini_sup}): {gemini_res.get('reason')}"
            return {"supported": False, "reason": combined_reason, "confidence": 0.5}, 0.5

    def _parse_json_response(self, content):
        try:
            # Clean Markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content.strip())
            return result, result.get("confidence", 0.0)
        except Exception:
            return {"supported": "error", "reason": "JSON Parse Error"}, 0.0

    def verify_claim(self, claim: str, quote: str, filename: str, lines: list):
        """
        Orchestrates the 3-step verification.
        lines: [start_int, end_int]
        """
        start, end = lines
        
        # Step 1: Existence
        text, error = self._read_lines(filename, start, end)
        if error:
            return {
                "step_1_existence": False, 
                "error": error,
                "verified": False
            }
        
        # Step 2: Quote Match
        # We search for the quote in the extracted text (which includes [Lxxxx] tags usually, 
        # so we might want to strip tags for quote matching if the quote doesn't have them.
        # But the user might provide a quote with or without tags. 
        # For robustness, let's try matching against text with and without tags if possible?
        # The prompt says "Returns raw text with [Lxxxx] tags".
        # Let's assume quote matching is against the raw text with tags for now, or lenient.
        # Actually, let's strip tags for comparison if fuzzy match fails.
        # But for now, simple fuzzy.
        
        quote_match, score = self._check_quote_match(text, quote)
        
        # Step 3: Semantic
        # Only proceed if quote match is reasonable? Or always check?
        # "Judge --> 1. Existence Check --> 2. Quote Match --> 3. Semantic Check"
        # Implies sequential.
        
        if not quote_match:
             return {
                "step_1_existence": True,
                "step_2_quote_match": False,
                "quote_score": score,
                "verified": False,
                "text_found": text
            }
            
        semantic_result, confidence = self._check_semantic_support(claim, text)
        
        return {
            "step_1_existence": True,
            "step_2_quote_match": True,
            "step_3_semantic": semantic_result,
            "verified": semantic_result.get("supported", False),
            "text_found": text
        }

if __name__ == "__main__":
    import sys
    # Usage: python -m research_engine.judge <CLAIM> <QUOTE> <FILENAME> <START_LINE> <END_LINE>
    if len(sys.argv) < 6:
        print("Usage: python -m research_engine.judge <CLAIM> <QUOTE> <FILENAME> <START_LINE> <END_LINE>")
        # Example: python -m research_engine.judge "Budget up 15%" "budget increase of 15%" "dummy_baked.txt" 2 2
        sys.exit(1)
        
    claim = sys.argv[1]
    quote = sys.argv[2]
    filename = sys.argv[3]
    start = int(sys.argv[4])
    end = int(sys.argv[5])
    
    judge = Judge()
    result = judge.verify_claim(claim, quote, filename, [start, end])
    print(json.dumps(result, indent=2))

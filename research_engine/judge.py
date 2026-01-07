
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
LLM_LOG_DIR = "debug_output/llm_logs"

class Judge:
    def __init__(self, canonical_dir=DEFAULT_CANONICAL_DIR, report_name: str = "default"):
        self.canonical_dir = Path(canonical_dir)
        
        # OpenRouter (OpenAI-compatible API with model routing)
        self.openrouter_client = None
        if OpenAI and config.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url=config.OPENROUTER_BASE_URL,
                api_key=config.OPENROUTER_API_KEY
            )
        
        # OpenAI Direct
        self.openai_client = None
        if OpenAI and config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            
        # Google Gemini
        self.gemini_enabled = False
        if genai and config.GOOGLE_API_KEY:
            try:
                genai.configure(api_key=config.GOOGLE_API_KEY)
                self.gemini_enabled = True
            except Exception:
                pass
        
        # Local LLM (OpenAI Compatible)
        self.local_client = None
        if OpenAI and config.LOCAL_LLM_BASE_URL:
            self.local_client = OpenAI(base_url=config.LOCAL_LLM_BASE_URL, api_key="lm-studio")
        
        # Ensure log directory exists (organized by report name)
        self._log_dir = Path(LLM_LOG_DIR) / report_name
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_citation_index = 0

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

    def _read_lines_with_context(self, filename: str, start_line: int, end_line: int, context_lines: int = 5):
        """Read cited lines plus surrounding context for semantic analysis."""
        file_path = self.canonical_dir / filename
        if not file_path.exists():
            return None, None, None, "File not found"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return None, None, None, f"Error reading file: {e}"
        
        total_lines = len(lines)
        
        # Cap end_line at file length (don't error if citation is near end of file)
        if start_line < 1 or start_line > total_lines:
            return None, None, None, f"Start line {start_line} out of bounds (file has {total_lines} lines)"
        end_line = min(end_line, total_lines)
        
        # Cited text
        cited_text = "".join(lines[start_line-1 : end_line])
        
        # Context before (up to context_lines)
        ctx_start = max(0, start_line - 1 - context_lines)
        context_before = "".join(lines[ctx_start : start_line-1])
        
        # Context after (up to context_lines)
        ctx_end = min(total_lines, end_line + context_lines)
        context_after = "".join(lines[end_line : ctx_end])
        
        return cited_text, context_before, context_after, None

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

    def _log_llm_output(self, provider: str, prompt: str, response: str):
        """Log LLM prompts and responses to debug files, indexed by citation."""
        log_file = self._log_dir / f"{provider}_{self._current_citation_index:04d}.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== PROMPT ===\n{prompt}\n\n=== RESPONSE ===\n{response}\n")

    def _call_openrouter(self, prompt_text: str, model: str = None):
        """Call OpenRouter API with specified model."""
        if not self.openrouter_client:
            return None
        
        if model is None:
            model = config.MODELS.get("verification", config.VERIFICATION_MODELS[0])
        
        try:
            response = self.openrouter_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_text + "\nRespond strictly in JSON."}],
                temperature=0.0,
                extra_headers={
                    "HTTP-Referer": "https://research-engine.local",
                    "X-Title": "Research Engine Verification"
                }
            )
            content = response.choices[0].message.content
            self._log_llm_output(f"openrouter_{model.replace('/', '_').replace(':', '_')}", prompt_text, content)
            return self._parse_json_response(content)
        except Exception as e:
            self._log_llm_output(f"openrouter_{model.replace('/', '_').replace(':', '_')}", prompt_text, f"ERROR: {e}")
            return {"verdict": "ERROR", "reason": f"OpenRouter Error ({model}): {e}"}, 0.0

    def _call_openai(self, prompt_text):
        """Call OpenAI API directly."""
        if not self.openai_client:
            return None
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            self._log_llm_output("openai", prompt_text, content)
            return self._parse_json_response(content)
        except Exception as e:
            self._log_llm_output("openai", prompt_text, f"ERROR: {e}")
            return {"verdict": "ERROR", "reason": f"OpenAI Error: {e}"}, 0.0

    def _call_gemini(self, prompt_text):
        """Call Google Gemini API."""
        if not self.gemini_enabled:
            return None
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt_text + "\nReturn RAW JSON.")
            content = response.text
            self._log_llm_output("gemini", prompt_text, content)
            return self._parse_json_response(content)
        except Exception as e:
            self._log_llm_output("gemini", prompt_text, f"ERROR: {e}")
            return {"verdict": "ERROR", "reason": f"Gemini Error: {e}"}, 0.0

    def _call_local_llm(self, prompt_text):
        """Call local LLM (Ollama/LM Studio)."""
        if not self.local_client:
            return None
        try:
            response = self.local_client.chat.completions.create(
                model="local-model",
                messages=[{"role": "user", "content": prompt_text + "\nRespond strictly in JSON."}],
                temperature=0.0
            )
            content = response.choices[0].message.content
            self._log_llm_output("local", prompt_text, content)
            return self._parse_json_response(content)
        except Exception as e:
            self._log_llm_output("local", prompt_text, f"ERROR: {e}")
            return {"verdict": "ERROR", "reason": f"Local LLM Error: {e}"}, 0.0

    def _check_semantic_support(self, claim: str, quote: str, cited_text: str, 
                                  context_before: str, context_after: str, filename: str,
                                  start_line: int, end_line: int,
                                  section_header: str = None, prior_context: str = None,
                                  table_headers: str = None):
        """Step 3: Enhanced Semantic Check with context and verdict categories."""
        
        # Build optional context blocks
        section_block = f"SECTION: {section_header}\n" if section_header else ""
        prior_block = f"PRIOR CONTEXT (from before previous citation): {prior_context}\n" if prior_context else ""
        table_block = f"TABLE HEADERS: {table_headers}\n" if table_headers else ""
        
        prompt_text = f"""You are verifying a citation in an investigative report.

{section_block}{table_block}{prior_block}
SOURCE FILE: {filename}
CITED LINES: L{start_line}-L{end_line}

CONTEXT BEFORE (from source file):
{context_before if context_before else "(start of file)"}

CITED TEXT (from source file):
{cited_text}

CONTEXT AFTER (from source file):
{context_after if context_after else "(end of file)"}

CLAIM BEING VERIFIED:
{claim}

INSTRUCTIONS:
1. The PRIOR CONTEXT provides grammatical context from the report (e.g., the subject of a sentence that continues in the CLAIM)
2. Consider the CLAIM together with PRIOR CONTEXT when determining what is being asserted
3. If TABLE HEADERS are provided, the claim is a table row and should be verified against those column meanings
4. Verify whether the SOURCE (CITED TEXT with its context) contains information that supports the claim

VERDICT CRITERIA:
- VALID: The source text directly supports the factual assertions in the claim
- MISLEADING: The source exists but the claim misrepresents or takes it out of context
- INSUFFICIENT: The source text is too limited to verify the claim (e.g., wrong line cited)
- UNSUPPORTED: The source text does not contain the claimed information

Respond strictly in JSON:
{{
  "supports_claim": boolean,
  "verdict": "VALID" | "MISLEADING" | "INSUFFICIENT" | "UNSUPPORTED",
  "reason": "brief explanation"
}}"""
        
        # Call all 3 OpenRouter verification models for consensus
        results = []
        for model in config.VERIFICATION_MODELS:
            result = self._call_openrouter(prompt_text, model=model)
            if result is not None:
                results.append(result)
        
        # Also call other providers if configured
        result_openai = self._call_openai(prompt_text)
        result_gemini = self._call_gemini(prompt_text)
        result_local = self._call_local_llm(prompt_text)
        
        for r in [result_openai, result_gemini, result_local]:
            if r is not None:
                results.append(r)
        
        if not results:
            return {"verdict": "ERROR", "reason": "No LLM configured (set OPENROUTER_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, or LOCAL_LLM_BASE_URL)"}, 0.0
        
        # Filter out error responses - only keep valid verdicts
        valid_results = []
        error_reasons = []
        for res, conf in results:
            if res.get("verdict") == "ERROR" or "Error" in res.get("reason", ""):
                error_reasons.append(res.get("reason", "unknown error"))
            else:
                valid_results.append((res, conf))
        
        # If all LLMs failed, return error
        if not valid_results:
            return {"verdict": "LLM_ERROR", "reason": "; ".join(error_reasons)}, 0.0
            
        # If only one valid result, return it
        if len(valid_results) == 1:
            return valid_results[0]

        # Consensus Logic (The Jury) - Vote based on verdict
        verdict_counts = {}
        reasons = []
        
        for res, conf in valid_results:
            verdict = res.get("verdict", "UNKNOWN")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            reasons.append(f"{verdict}: {res.get('reason', 'no reason')}")
        
        combined_reason = " | ".join(reasons)
        
        # Determine winning verdict by count
        if verdict_counts:
            winning_verdict = max(verdict_counts, key=verdict_counts.get)
            winning_count = verdict_counts[winning_verdict]
            
            # Check for tie
            ties = [v for v, c in verdict_counts.items() if c == winning_count]
            if len(ties) > 1:
                return {"verdict": "HUNG_JURY", "reason": f"Tie: {combined_reason}"}, 0.5
            
            return {
                "verdict": winning_verdict,
                "substantive_quote": any(r[0].get("substantive_quote", False) for r in valid_results),
                "quote_in_context": any(r[0].get("quote_in_context", False) for r in valid_results),
                "supports_claim": any(r[0].get("supports_claim", False) for r in valid_results),
                "reason": f"Consensus ({winning_count}/{len(valid_results)}): {combined_reason}"
            }, 1.0 if winning_verdict == "VALID" else 0.0
        
        return {"verdict": "UNKNOWN", "reason": "No results"}, 0.0

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

    def verify_claim(self, claim: str, quote: str, filename: str, lines: list, 
                     citation_index: int = 0, section_header: str = None,
                     prior_context: str = None, table_headers: str = None):
        """
        Orchestrates the 3-step verification.
        
        Args:
            claim: The claim text to verify
            quote: The quote/text to match in the source
            filename: The source file name
            lines: [start_int, end_int] - line range to check
            citation_index: Used for logging filenames
            section_header: Report section header for context
            prior_context: Rolling context from before previous citation
            table_headers: Table column headers if claim is a table row
        """
        self._current_citation_index = citation_index
        start, end = lines
        
        # Step 1: Existence (also get context) - expanded to 10 lines
        cited_text, context_before, context_after, error = self._read_lines_with_context(
            filename, start, end, context_lines=10
        )
        if error:
            return {
                "step_1_existence": False, 
                "error": error,
                "verified": False
            }
        
        # Step 2: Quote Match - informational only (we're sending full claims now)
        full_search_text = (context_before or "") + cited_text
        quote_match, score = self._check_quote_match(full_search_text, quote)
        
        # Step 3: Semantic check is the primary verification method
        semantic_result, confidence = self._check_semantic_support(
            claim, quote, cited_text, context_before, context_after, 
            filename, start, end,
            section_header=section_header,
            prior_context=prior_context,
            table_headers=table_headers
        )
        
        # Use semantic verdict directly (quote match is no longer a gate)
        verdict = semantic_result.get("verdict", "UNKNOWN")
        verified = verdict == "VALID"
        
        return {
            "step_1_existence": True,
            "step_2_quote_match": quote_match,
            "quote_score": score,
            "step_3_semantic": semantic_result,
            "verdict": verdict,
            "verified": verified,
            "text_found": cited_text
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

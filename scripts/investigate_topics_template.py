import re
import os
import argparse
import sys

def investigate_topics(corpus_path):
    # Define your topics here
    topics = {
        "example_topic_1.md": {
            "keywords": ["keyword1", "keyword2", "phrase match"],
            "title": "Topic 1: Example Topic"
        },
        "example_topic_2.md": {
            "regex": r"202[4-5]",
            "title": "Topic 2: Regex Match (Years 2024-2025)"
        }
    }

    results = {k: [] for k in topics.keys()}
    current_file = "Unknown"
    
    try:
        with open(corpus_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Corpus file '{corpus_path}' not found.")
        return

    for i, line in enumerate(lines):
        # Track current file (assumes standard 'baked' format boundaries)
        if line.startswith("START OF FILE:"):
            current_file = line.replace("START OF FILE:", "").strip()
            continue
        if line.startswith("PATH:") or line.startswith("END OF FILE:") or line.startswith("====="):
            continue

        # Search for topics
        for filename, criteria in topics.items():
            hit = False
            
             # Check Filename Regex if present
            if "filename_regex" in criteria:
                if not re.search(criteria["filename_regex"], current_file):
                    continue

            # Keyword Search
            if "keywords" in criteria:
                for kw in criteria["keywords"]:
                    if kw.lower() in line.lower():
                        hit = True
                        break
            
            # Regex Search
            if "regex" in criteria:
                if re.search(criteria["regex"], line):
                    hit = True

            if hit:
                # Extract context (10 lines before and after = ~paragraph)
                start = max(0, i - 10)
                end = min(len(lines), i + 11)
                context = "".join(lines[start:end]).strip()
                
                # Deduplicate based on context
                if not any(r['context'] == context for r in results[filename]):
                    results[filename].append({
                        "file": current_file,
                        "line_num": i + 1,
                        "context": context
                    })

    # Write results
    output_dir = os.path.dirname(corpus_path)
    for filename, hits in results.items():
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {topics[filename]['title']}\n\n")
            if not hits:
                f.write("No relevant mentions found in the corpus.\n")
            else:
                for hit in hits:
                    f.write(f"### Source: `{hit['file']}` (Line {hit['line_num']})\n")
                    f.write("```text\n")
                    f.write(hit['context'])
                    f.write("\n```\n\n")
        print(f"Generated {output_path} with {len(hits)} hits.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Investigate topics in a corpus.")
    parser.add_argument("corpus_path", help="Path to the full text corpus file")
    
    args = parser.parse_args()
    
    investigate_topics(args.corpus_path)

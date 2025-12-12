import os
import glob

def create_corpus(input_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Sort for determinism
        files = sorted(glob.glob(os.path.join(input_dir, "*_baked.txt")))
        for filepath in files:
            filename = os.path.basename(filepath)
            abspath = os.path.abspath(filepath)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    
                outfile.write("\n==================================================\n")
                outfile.write(f"START OF FILE: {filename}\n")
                outfile.write(f"PATH: {abspath}\n")
                outfile.write("==================================================\n")
                outfile.write(content)
                outfile.write("\n\n==================================================\n")
                outfile.write(f"END OF FILE: {filename}\n")
                outfile.write("==================================================\n\n")
                print(f"Added {filename}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    create_corpus("data/canonical", "baked_corpus.txt")

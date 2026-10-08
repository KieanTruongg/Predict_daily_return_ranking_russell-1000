import os
import glob
import re

files_to_check = glob.glob("docs/**/*", recursive=True) + ["README.md"]

for file_path in files_to_check:
    if not os.path.isfile(file_path):
        continue
    if file_path.endswith(('.png', '.pdf', '.zip', '.parquet')):
        continue
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        script_refs = re.findall(r'scripts/[a-zA-Z0-9_]+\.py', content)
        if script_refs:
            print(f"{file_path}: {set(script_refs)}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

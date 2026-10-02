import os
import glob
import re

print("=== SEARCHING FOR QUANTCONNECT SCRIPTS ===")
files = glob.glob("**/*.py", recursive=True) + glob.glob("**/*.txt", recursive=True) + glob.glob("**/*.ipynb", recursive=True)

for f in files:
    if "venv" in f or ".git" in f or "__pycache__" in f:
        continue
    try:
        with open(f, "r", encoding="utf-8", errors="ignore") as file:
            content = file.read()
        if "QuantBook" in content or "get_zip_download_html" in content or "IPython.display" in content or "TẢI FILE ZIP" in content:
            print(f"FOUND: {f} (size: {len(content)} bytes)")
    except Exception as e:
        pass

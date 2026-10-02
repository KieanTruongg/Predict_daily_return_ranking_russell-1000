import os
import glob

print("=== SEARCHING ALL FILES INCLUDING CLEAR FOR QUANTCONNECT ===")
files = glob.glob("**/*", recursive=True)

for f in files:
    if os.path.isfile(f) and not f.endswith(('.pdf', '.png', '.zip', '.parquet', '.csv')):
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                content = file.read()
            if "QuantBook" in content or "download" in content.lower() or "zip" in content.lower() or "quantconnect" in content.lower():
                print(f"File: {f} (lines: {len(content.splitlines())})")
        except Exception:
            pass

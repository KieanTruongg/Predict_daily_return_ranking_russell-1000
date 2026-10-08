import os
import glob
import re

scripts = glob.glob("scripts/**/*.py", recursive=True)
for s in scripts:
    with open(s, "r", encoding="utf-8") as f:
        content = f.read()
    matches = re.findall(r'["\'](data/[^"\']+)["\']', content)
    if matches:
        print(f"{s}: {set(matches)}")

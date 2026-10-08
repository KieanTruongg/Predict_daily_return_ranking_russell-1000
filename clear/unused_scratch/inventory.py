import os

ignore_dirs = {".git", ".gemini", "__pycache__", "clear", ".venv", "venv", ".idea"}

print("=== PROJECT COMPLETE INVENTORY ===")
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    rel_path = os.path.relpath(root, ".")
    if rel_path == ".":
        print("\n[ROOT FILES]")
        for f in files:
            print(f"  - {f}")
    else:
        print(f"\n[{rel_path}]")
        for f in files:
            if not f.endswith(('.pyc', '.git')):
                print(f"  - {f}")

import json
import sys
import os
from pathlib import Path

# Define required files and their expected types
REQUIRED_FILES = {
    "glyphs.json": dict,
    "modes.json": dict,
    "phrases.json": dict,
    "rules.json": list,
}

def validate_json(filename, data):
    """ Validate JSON structure based on filename """
    if filename == "rules.json":
        for i, rule in enumerate(data):
            if not isinstance(rule, dict):
                raise ValueError(f"Rule at index {i} is not a dictionary.")
            for key in ["name", "regex", "replacement"]:
                if key not in rule:
                    raise ValueError(f"Rule {i} missing key: {key}")

def main(folder):
    folder_path = Path(folder)

    # Check that all required files exist
    missing = [f for f in REQUIRED_FILES if not (folder_path / f).is_file()]
    if missing:
        print(f"❌ Missing required files: {', '.join(missing)}")
        sys.exit(1)

    # Validate each file
    for filename, expected_type in REQUIRED_FILES.items():
        file_path = folder_path / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, expected_type):
                raise TypeError(f"{filename} should be a {expected_type.__name__}.")

            validate_json(filename, data)
            print(f"✅ {filename} is valid.")

        except Exception as e:
            print(f"❌ {filename} validation failed: {e}")
            sys.exit(1)

    print("🎉 All JSON files are valid!")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    main(folder)

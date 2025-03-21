#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime

gist_url = os.environ["GIST_URL"]
target_dir = os.environ["TARGET_DIR"]
your_name = os.environ["YOUR_NAME"]
system_description = os.environ["SYSTEM_DESCRIPTION"]

if gist_url.endswith("/"):
    gist_url = gist_url[:-1]
gist_id = gist_url.split("/")[-1]

api_url = f"https://api.github.com/gists/{gist_id}"
print(f"Fetching Gist metadata from {api_url}...")

r = requests.get(api_url)
if r.status_code != 200:
    raise Exception(f"Failed to fetch Gist metadata: {r.status_code} {r.text}")

data = r.json()
files = data.get("files", {})

required = ["glyphs.json", "modes.json", "rules.json", "phrases.json"]
missing = [name for name in required if name not in files]
if missing:
    raise Exception(f"Missing required files in Gist: {missing}")

os.makedirs(target_dir, exist_ok=True)

for name in required:
    raw_url = files[name]["raw_url"]
    print(f"Downloading {name} from {raw_url}")
    file_resp = requests.get(raw_url)
    if not file_resp.ok:
        raise Exception(f"Failed to download {name}: {file_resp.status_code}")
    with open(os.path.join(target_dir, name), "w", encoding="utf-8") as f:
        f.write(file_resp.text)
    print(f"✅ Saved {name} to {target_dir}")

metadata = {
    "uploader": your_name,
    "description": system_description,
    "source_gist": gist_url,
    "gist_id": gist_id,
    "upload_date": datetime.utcnow().isoformat() + "Z"
}
with open(os.path.join(target_dir, "meta.json"), "w", encoding="utf-8") as meta_file:
    json.dump(metadata, meta_file, indent=2)
    print(f"✅ Created meta.json in {target_dir}")

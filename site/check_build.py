# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parent
image = Image.open(root / "img" / "pushkin.jpg")
height = int(image.width * 640 / 1920)
crop = image.crop((0, 380, image.width, 380 + height))
crop.resize((1920, 640), Image.Resampling.LANCZOS).save(root.parent / "social" / "cover.jpg", quality=90)

missing = []
for html in root.glob("*.html"):
    text = html.read_text(encoding="utf-8")
    for src in re.findall(r'src="([^"]+)"', text):
        if not (root / src).exists():
            missing.append(f"{html.name}: {src}")
    match = re.search(r'data-points="([^"]+)"', text)
    if match:
        raw = match.group(1).replace("&quot;", '"').replace("&amp;", "&")
        points = json.loads(raw)
        print("pins", [(round(item["lat"], 5), round(item["lon"], 5)) for item in points])

print("missing", missing or "none")

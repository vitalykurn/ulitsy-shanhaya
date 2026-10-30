# -*- coding: utf-8 -*-
"""Download openly licensed Wikimedia photos and look up map coordinates."""

import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMG = ROOT / "img"
IMG.mkdir(exist_ok=True)

UA = "UlitsyShanhayaSchoolMap/1.0 (school history map; family project)"
OK_LICENSES = {
    "CC BY 2.0",
    "CC BY 2.5",
    "CC BY 3.0",
    "CC BY 4.0",
    "CC BY-SA 2.0",
    "CC BY-SA 2.5",
    "CC BY-SA 3.0",
    "CC BY-SA 4.0",
    "CC0",
    "CC0 1.0",
    "Public domain",
    "PDM",
}

CANDIDATES = {
    "pushkin": [
        "File:Памятник Пушкину в Шанхае (1).jpg",
        "File:Памятник Пушкину в Шанхае (2).jpg",
        "File:Shanghai0612 001.JPG",
        "File:Shanghai Pushkin Statue 1937.jpg",
    ],
    "sobor": [
        "File:Храм в честь Пресвятой Богородицы в Шанхае.jpg",
        "File:Храм в честь Пресвятой Богородицы и Архиерейский дом в Шанхае.jpg",
        "File:Russian Orthodox Church, Old Shanghai.jpg",
        "File:1936 cathedral shanghai.jpg",
    ],
    "nikolsky": [
        "File:Saint Nicholas' Church in Shanghai.jpg",
        "File:Saint Nicholas' Church, Shanghai 20210131.jpg",
        "File:Храм святителя Николая в Шанхае.jpg",
        "File:2025 St Nicholas ROC 5th WMgf0.jpg",
    ],
    "huaihai": [
        "File:L'avenue Huaihai, ancienne avenue Joffre (Shanghai, Chine) (25188411507).jpg",
        "File:Middle Huaihai Rd..JPG",
        "File:Huaihai Road (M).JPG",
        "File:Avenue Joffre in the 1930s.jpg",
        "File:Huaihai Road 2010.jpg",
    ],
    "vystavka": [
        "File:Shanghai Exhibition Center.jpg",
        "File:Shanghai Exhibition Center, December 2015 - 04.JPG",
    ],
}

PLACES = {
    "pushkin": "Pushkin monument, Fenyang Road, Shanghai",
    "sobor": "55 Xinle Road, Shanghai",
    "nikolsky": "16 Gaolan Road, Shanghai",
    "huaihai": "Middle Huaihai Road and South Shaanxi Road, Shanghai",
    "vystavka": "Shanghai Exhibition Center, 1000 Yan'an Middle Road",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def image_info(title):
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime",
        "iiurlwidth": "1600",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = json.loads(get(url).decode("utf-8"))
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        return None
    info = page["imageinfo"][0]
    meta = info.get("extmetadata") or {}

    def field(name):
        return strip_html((meta.get(name) or {}).get("value"))

    return {
        "title": title,
        "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="/:()'%"),
        "license": field("LicenseShortName"),
        "artist": field("Artist"),
        "credit": field("Credit"),
        "license_url": field("LicenseUrl"),
        "mime": info.get("mime"),
        "width": info.get("thumbwidth") or info.get("width"),
        "height": info.get("thumbheight") or info.get("height"),
        "download": info.get("thumburl") or info.get("url"),
        "original": info.get("url"),
    }


def geocode(query):
    params = {"q": query, "format": "json", "limit": "1"}
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    rows = json.loads(get(url).decode("utf-8"))
    if not rows:
        return None
    row = rows[0]
    return {
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "name": row.get("display_name", ""),
    }


def main():
    chosen = {}
    rejected = []
    for key, titles in CANDIDATES.items():
        picked = None
        for title in titles:
            try:
                info = image_info(title)
            except Exception as exc:
                rejected.append({"key": key, "title": title, "error": str(exc)})
                continue
            if not info:
                rejected.append({"key": key, "title": title, "error": "no imageinfo"})
                continue
            license_name = info["license"]
            allowed = license_name in OK_LICENSES or license_name.startswith("CC BY") or "Public domain" in license_name or license_name in {"CC0", "PDM"}
            blocked = any(flag in license_name.upper() for flag in ("NC", "NONCOMMERCIAL", "FAIR USE"))
            if not allowed or blocked or not license_name:
                rejected.append({"key": key, "title": title, "license": license_name})
                continue
            ext = ".jpg"
            if info["mime"] == "image/png":
                ext = ".png"
            elif info["mime"] == "image/webp":
                ext = ".webp"
            dest = IMG / f"{key}{ext}"
            dest.write_bytes(get(info["download"]))
            info["file"] = f"img/{dest.name}"
            picked = info
            break
        chosen[key] = picked

    coords = {}
    for key, query in PLACES.items():
        time.sleep(1.2)
        try:
            coords[key] = geocode(query)
        except Exception as exc:
            coords[key] = {"error": str(exc)}

    report = {"photos": chosen, "coords": coords, "rejected": rejected}
    (ROOT / "credits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (v or {}).get("license") if isinstance(v, dict) else v for k, v in chosen.items()}, ensure_ascii=False, indent=2))
    print("--- coords ---")
    print(json.dumps(coords, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

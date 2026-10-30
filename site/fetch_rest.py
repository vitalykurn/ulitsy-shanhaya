# -*- coding: utf-8 -*-
"""Finish photo downloads with a short timeout and write credits.json."""

import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMG = ROOT / "img"
UA = "UlitsyShanhayaSchoolMap/1.0 (school history map; family project)"

WANTED = {
    "pushkin": [
        "File:Памятник Пушкину в Шанхае (1).jpg",
        "File:Памятник Пушкину в Шанхае (2).jpg",
        "File:Shanghai0612 001.JPG",
    ],
    "sobor": [
        "File:Храм в честь Пресвятой Богородицы в Шанхае.jpg",
        "File:Храм в честь Пресвятой Богородицы и Архиерейский дом в Шанхае.jpg",
        "File:Russian Orthodox Church, Old Shanghai.jpg",
    ],
    "nikolsky": [
        "File:Saint Nicholas' Church in Shanghai.jpg",
        "File:Saint Nicholas' Church, Shanghai 20210131.jpg",
        "File:Храм святителя Николая в Шанхае.jpg",
    ],
    "huaihai": [
        "File:L'avenue Huaihai, ancienne avenue Joffre (Shanghai, Chine) (25188411507).jpg",
        "File:Middle Huaihai Rd..JPG",
        "File:Huaihai Road (M).JPG",
        "File:Huaihai Road 2010.jpg",
    ],
    "vystavka": [
        "File:Shanghai Exhibition Center.jpg",
    ],
}

QUERIES = {
    "pushkin": "Pushkin monument Fenyang Road Shanghai",
    "sobor": "55 Xinle Road Shanghai",
    "nikolsky": "16 Gaolan Road Shanghai",
    "huaihai": "Middle Huaihai Road and South Shaanxi Road Shanghai",
    "vystavka": "Shanghai Exhibition Center Yan'an Road",
}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def image_info(title):
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime",
        "iiurlwidth": "900",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = json.loads(get(url).decode("utf-8"))
    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]
    meta = info.get("extmetadata") or {}

    def field(name):
        return strip_html((meta.get(name) or {}).get("value"))

    return {
        "title": title,
        "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="/%()'!._-"),
        "license": field("LicenseShortName"),
        "artist": field("Artist"),
        "license_url": field("LicenseUrl"),
        "download": info.get("thumburl") or info.get("url"),
    }


def allowed(license_name):
    if not license_name:
        return False
    upper = license_name.upper()
    if "NC" in upper or "FAIR USE" in upper or "NONCOMMERCIAL" in upper:
        return False
    return upper.startswith("CC BY") or upper.startswith("CC0") or "PUBLIC DOMAIN" in upper or upper in {"PDM", "CC0"}


def geocode(query):
    params = {"q": query, "format": "json", "limit": "1"}
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    rows = json.loads(get(url, timeout=20).decode("utf-8"))
    if not rows:
        return None
    return {"lat": float(rows[0]["lat"]), "lon": float(rows[0]["lon"]), "name": rows[0].get("display_name", "")}


def say(*parts):
    text = " ".join(str(part) for part in parts)
    print(text.encode("ascii", "backslashreplace").decode(), flush=True)


def main():
    photos = {}
    for key, titles in WANTED.items():
        picked = None
        for title in titles:
            try:
                info = image_info(title)
            except Exception as exc:
                say(key, "ERR", title, exc)
                continue
            say(key, info["license"], title)
            if not allowed(info["license"]):
                continue
            dest = IMG / f"{key}.jpg"
            try:
                dest.write_bytes(get(info["download"], timeout=70))
                say(" saved", dest.name, dest.stat().st_size)
            except Exception as exc:
                say(" download failed", key, exc)
                same_as_saved = title == titles[0] and dest.exists() and dest.stat().st_size >= 20000
                if not same_as_saved:
                    continue
                say(" keep existing", dest.name, dest.stat().st_size)
            info["file"] = f"img/{dest.name}"
            picked = info
            break
        photos[key] = picked

    coords = {}
    for key, query in QUERIES.items():
        time.sleep(1.1)
        try:
            coords[key] = geocode(query)
            say("geo", key, coords[key])
        except Exception as exc:
            coords[key] = {"error": str(exc)}
            say("geo ERR", key, exc)

    report = {"photos": photos, "coords": coords}
    (ROOT / "credits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    say("credits written")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


req = urllib.request.Request("https://app.netlify.com/drop", headers=UA)
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
scripts = re.findall(r'src="([^"]+)"', html)
print("scripts", len(scripts))
for src in scripts:
    if src.startswith("/"):
        src = "https://app.netlify.com" + src
    print("SCRIPT", src[:160])
    try:
        body = urllib.request.urlopen(urllib.request.Request(src, headers=UA), timeout=30).read().decode("utf-8", "replace")
    except Exception as exc:
        print("  ERR", type(exc).__name__)
        continue
    found = set(re.findall(r"https://api\.netlify\.com[^\"'\s]{0,80}", body))
    found |= set(re.findall(r"/api/v1/[^\"'\s]{0,60}", body))
    for item in list(found)[:20]:
        print(" ", item)

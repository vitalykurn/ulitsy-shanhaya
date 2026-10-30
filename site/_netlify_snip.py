# -*- coding: utf-8 -*-
import urllib.request
from pathlib import Path

url = "https://app.netlify.com/assets/js/app.9ddaec4799bfd48ecd8e.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
key = "uploadBuildFromZip=(()=>{var e=this;return function(t)"
index = text.find(key)
out = Path(__file__).with_name("_netlify_snip.txt")
out.write_text(text[index:index + 2200] if index >= 0 else "NOT FOUND", encoding="utf-8")
print("index", index, "len", len(text))

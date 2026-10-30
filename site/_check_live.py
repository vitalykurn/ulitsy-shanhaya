# -*- coding: utf-8 -*-
import urllib.request

url = "https://calm-caramel-d4778c.netlify.app/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    response = urllib.request.urlopen(req, timeout=30)
    body = response.read(500).decode("utf-8", "replace")
    print(response.status, response.geturl())
    print(body[:400])
except Exception as exc:
    if hasattr(exc, "code"):
        print("HTTP", exc.code)
        print(exc.read(400).decode("utf-8", "replace"))
    else:
        print(type(exc).__name__, exc)

# -*- coding: utf-8 -*-
"""Start GitHub device login. Prints only the user code, not the device secret."""

import json
import urllib.parse
import urllib.request
from pathlib import Path

CLIENT = "178c6fc778ccc68e1d6a"
body = urllib.parse.urlencode(
    {"client_id": CLIENT, "scope": "repo"}
).encode()
req = urllib.request.Request(
    "https://github.com/login/device/code",
    data=body,
    headers={"Accept": "application/json", "User-Agent": "ulitsy-shanhaya"},
)
data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
out = Path(__file__).with_name("_gh_device.json")
out.write_text(json.dumps({k: data[k] for k in ("device_code", "interval", "expires_in")}), encoding="utf-8")
print("USER_CODE", data["user_code"])
print("URI", data["verification_uri"])
print("INTERVAL", data.get("interval"))

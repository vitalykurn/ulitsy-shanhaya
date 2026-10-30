# -*- coding: utf-8 -*-
"""Poll GitHub device login, push the static site, enable Pages. Never prints the token."""

import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEVICE = ROOT / "_gh_device.json"
CLIENT = "178c6fc778ccc68e1d6a"
REPO = "vitalykurno/ulitsy-shanhaya"


def poll():
    data = json.loads(DEVICE.read_text(encoding="utf-8"))
    deadline = time.time() + min(int(data.get("expires_in", 900)), 240)
    interval = int(data.get("interval", 5))
    body = urllib.parse.urlencode(
        {
            "client_id": CLIENT,
            "device_code": data["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
    ).encode()
    while time.time() < deadline:
        req = urllib.request.Request(
            "https://github.com/login/oauth/access_token",
            data=body,
            headers={"Accept": "application/json", "User-Agent": "ulitsy-shanhaya"},
        )
        result = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        if "access_token" in result:
            return result["access_token"]
        if result.get("error") not in ("authorization_pending", "slow_down"):
            print("AUTH", result.get("error"))
            return None
        time.sleep(interval + (2 if result.get("error") == "slow_down" else 0))
    print("AUTH timeout")
    return None


def git(args, token=None):
    env = None
    if token:
        env = dict(**subprocess.os.environ)
        env["GIT_ASKPASS"] = "echo"
    subprocess.run(args, cwd=ROOT, check=True, env=env)


def push(token):
    subprocess.run(["git", "init", "-b", "main"], cwd=ROOT, check=True)
    names = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() == ".py" or path.name.startswith("_") or path.suffix == ".json":
            continue
        if rel.startswith(".git/"):
            continue
        names.append(rel)
    subprocess.run(["git", "add", "--"] + names, cwd=ROOT, check=True)
    subprocess.run(
        ["git", "-c", "user.name=vitalykurno", "-c", "user.email=vitalykurno@users.noreply.github.com", "commit", "-m", "Publish the Shanghai history map"],
        cwd=ROOT,
        check=True,
    )
    remote = f"https://x-access-token:{token}@github.com/{REPO}.git"
    subprocess.run(["git", "remote", "remove", "origin"], cwd=ROOT, check=False)
    subprocess.run(["git", "remote", "add", "origin", remote], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=ROOT, check=True)
    subprocess.run(["git", "remote", "set-url", "origin", f"https://github.com/{REPO}.git"], cwd=ROOT, check=True)


def enable_pages(token):
    body = json.dumps({"build_type": "legacy", "source": {"branch": "main", "path": "/"}}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/pages",
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "ulitsy-shanhaya",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as exc:
        print("PAGES", getattr(exc, "code", type(exc).__name__))
        return
    print("PAGES ok")


def main():
    token = poll()
    if not token:
        return
    try:
        push(token)
        enable_pages(token)
        print("LIVE https://vitalykurno.github.io/ulitsy-shanhaya/")
    finally:
        DEVICE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

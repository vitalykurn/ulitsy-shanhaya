# -*- coding: utf-8 -*-
"""Push text site files to GitHub (needs gh auth or GITHUB_TOKEN)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "vitalykurn/ulitsy-shanhaya"
BRANCH = "main"
TEXT_SUFFIX = {".html", ".css", ".js", ".py", ".json", ".xml", ".txt", ".md", ".mdc", ".yaml", ".yml"}


def token() -> str:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(key):
            return os.environ[key]
    try:
        out = subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL)
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def collect() -> list[dict]:
    paths: set[str] = set()
    for base in (ROOT / ".github" / "workflows", ROOT / "prompts", ROOT / ".cursor" / "rules", ROOT / "site"):
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix == ".pyc" or path.name.startswith("_"):
                continue
            if path.suffix.lower() in TEXT_SUFFIX:
                paths.add(path.relative_to(ROOT).as_posix())
    if (ROOT / ".gitignore").is_file():
        paths.add(".gitignore")
    return [
        {"path": rel, "content": (ROOT / rel.replace("/", os.sep)).read_text(encoding="utf-8")}
        for rel in sorted(paths)
    ]


def push(files: list[dict], message: str, tok: str) -> None:
    body = json.dumps({"message": message, "content": None, "branch": BRANCH, "files": files}).encode("utf-8")
    # GitHub contents API has no multi-file; use git clone approach via gh api graphql or sequential updates.
    # Use gh api repos/.../contents for each file in one commit via Git Data API.
    base = subprocess.check_output(
        ["gh", "api", f"repos/{REPO}/git/ref/heads/{BRANCH}", "--jq", ".object.sha"],
        text=True,
        env={**os.environ, "GH_TOKEN": tok},
    ).strip()
    tree_items = []
    for item in files:
        blob = subprocess.check_output(
            [
                "gh",
                "api",
                f"repos/{REPO}/git/blobs",
                "-f",
                f"content={item['content']}",
                "-f",
                "encoding=utf-8",
                "--jq",
                ".sha",
            ],
            text=True,
            env={**os.environ, "GH_TOKEN": tok},
        ).strip()
        tree_items.append({"path": item["path"], "mode": "100644", "type": "blob", "sha": blob})
    tree_sha = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/{REPO}/git/trees",
            "-f",
            f"base_tree={base}",
            "-f",
            f"tree={json.dumps(tree_items)}",
            "--jq",
            ".sha",
        ],
        text=True,
        env={**os.environ, "GH_TOKEN": tok},
    ).strip()
    commit_sha = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/{REPO}/git/commits",
            "-f",
            f"message={message}",
            "-f",
            f"tree={tree_sha}",
            "-f",
            f"parents[]={base}",
            "--jq",
            ".sha",
        ],
        text=True,
        env={**os.environ, "GH_TOKEN": tok},
    ).strip()
    subprocess.check_call(
        [
            "gh",
            "api",
            f"repos/{REPO}/git/refs/heads/{BRANCH}",
            "-X",
            "PATCH",
            "-f",
            f"sha={commit_sha}",
        ],
        env={**os.environ, "GH_TOKEN": tok},
    )


def main() -> int:
    tok = token()
    if not tok:
        print("Need gh auth login or GITHUB_TOKEN", file=sys.stderr)
        return 1
    os.environ["GH_TOKEN"] = tok
    files = collect()
    print(f"files: {len(files)}")
    push(files, "Update site: rebuild and publish", tok)
    print("pushed", REPO, BRANCH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

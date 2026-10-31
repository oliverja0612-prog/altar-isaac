"""Altar mod safety check.

Downloads a mod from its GitHub repo, pinned to one exact commit, and checks it before
it can be listed on the Altar site. Run by .github/workflows/mod-submission.yml for every
submission, and by hand:

    python registry/safety_check.py owner/repo <tag|branch|commit> [--path sub/folder] [--json report.json]

Fails (exit 1) on:
  - no metadata.xml or main.lua in the mod folder
  - paths that escape the mod folder (../, absolute paths)
  - executables or scripts other than Lua (by extension, and any file that is really a
    Windows program whatever it's called)
  - Lua that can run programs or load native code: os.execute, io.popen,
    package.loadlib, ffi, sockets / C modules
  - more than 150 MB or 5000 files
Warns on (an admin looks at these): file access (io.open, os.remove ...), dynamic code
(load, loadstring, dofile), the debug library, and unknown file types.

Standard library only, so it runs anywhere Python 3.9+ does.
"""
import argparse
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

MAX_BYTES = 150 * 1024 * 1024
MAX_FILES = 5000

ALLOWED_EXT = {
    ".lua", ".xml", ".anm2", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ogg", ".wav", ".mp3", ".fnt",
    ".stb", ".txt", ".md", ".json", ".pal", ".fs", ".vs", ".shader", ".ttf", ".otf", ".csv", ".ini",
    ".gitignore", ".gitattributes", ".gitkeep", ".editorconfig", ".luarc", ".luacheckrc", ".yml", ".yaml",
}
BLOCKED_EXT = {
    ".exe", ".dll", ".com", ".scr", ".msi", ".msp", ".bat", ".cmd", ".ps1", ".psm1", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".hta", ".jar", ".sh", ".py", ".pyw", ".pyc", ".lnk", ".reg", ".cpl",
    ".so", ".dylib", ".sys", ".drv", ".ocx", ".application", ".appx", ".msix", ".iso", ".img", ".vhd",
    ".zip", ".7z", ".rar", ".gz", ".tar",
}

# Lua that can reach outside the game (only possible when Isaac runs with --luadebug,
# which is exactly when a malicious mod could do damage)
LUA_BLOCK = [
    (r"\bos\s*\.\s*execute\b", "runs a program (os.execute)"),
    (r"\bio\s*\.\s*popen\b", "runs a program (io.popen)"),
    (r"\bpackage\s*\.\s*loadlib\b", "loads native code (package.loadlib)"),
    (r"\bffi\b", "uses the FFI (native code)"),
    (r"require\s*\(?\s*['\"](socket|ffi|lfs|luasocket|ltn12|mime|ssl|winapi|alien)['\"]", "loads a native module"),
    (r"\bpackage\s*\.\s*cpath\b", "changes where native modules load from"),
]
LUA_WARN = [
    (r"\bio\s*\.\s*(open|lines|write|read|output|input)\b", "reads or writes files"),
    (r"\bos\s*\.\s*(remove|rename|getenv|tmpname|exit)\b", "touches the system (os.*)"),
    (r"\b(loadstring|dofile|loadfile)\s*\(", "runs code it builds or loads itself"),
    (r"(?<![\w.:])load\s*\(", "runs code it builds itself (load)"),
    (r"\bdebug\s*\.\s*\w+", "uses the debug library"),
    (r"\brequire\s*\(?\s*['\"]os['\"]", "requires os"),
]


def strip_lua_comments(src):
    src = re.sub(r"--\[(=*)\[.*?\]\1\]", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return re.sub(r"--[^\n]*", "", src)


def http_get(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Altar-Safety-Check",
                                               **({"Accept": accept} if accept else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def resolve_commit(repo, ref):
    """Pin a tag/branch to its commit so what was checked is exactly what gets installed."""
    data = json.loads(http_get(f"https://api.github.com/repos/{repo}/commits/{ref}", "application/vnd.github+json"))
    return data["sha"]


def parse_metadata(raw):
    try:
        root = ET.fromstring(raw.decode("utf-8", "replace").lstrip("﻿"))
    except ET.ParseError:
        return {}
    get = lambda tag: (root.findtext(tag) or "").strip()
    return {"name": get("name"), "version": get("version"), "description": " ".join(get("description").split()),
            "workshop_id": get("id"), "directory": get("directory")}


def check_zip(data, path=""):
    """Returns a report dict for a GitHub source zip (all files under one top folder)."""
    findings, stats = [], {"files": 0, "bytes": 0}

    def add(level, msg, file=None, line=None):
        findings.append({"level": level, "message": msg, "file": file, "line": line})

    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        add("fail", "the download is not a valid zip")
        return {"result": "fail", "findings": findings, "stats": stats, "metadata": {}}
    names = [n for n in z.namelist() if not n.endswith("/")]
    top = names[0].split("/")[0] + "/" if names else ""
    root = top + (path.strip("/") + "/" if path.strip("/") else "")
    files = [n for n in names if n.startswith(root)]
    if not files:
        add("fail", f"folder '{path}' was not found in the repo" if path else "the repo is empty")
    metadata = {}
    has_main = False
    for name in files:
        rel = name[len(root):]
        info = z.getinfo(name)
        stats["files"] += 1
        stats["bytes"] += info.file_size
        parts = rel.replace("\\", "/").split("/")
        if ".." in parts or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
            add("fail", "path escapes the mod folder", rel)
            continue
        low = rel.lower()
        ext = "." + low.rsplit(".", 1)[-1] if "." in parts[-1] else ""
        if parts[-1].startswith(".") and "." not in parts[-1][1:]:
            ext = parts[-1].lower()
        head = z.read(name)[:4] if info.file_size else b""
        if head[:2] == b"MZ" or head == b"\x7fELF" or head in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
            add("fail", "contains a program (executable file)", rel)
        elif ext in BLOCKED_EXT:
            add("fail", f"file type {ext} is not allowed in a mod", rel)
        elif ext and ext not in ALLOWED_EXT:
            add("warn", f"unusual file type {ext}", rel)
        if low == "metadata.xml":
            metadata = parse_metadata(z.read(name))
        if low == "main.lua":
            has_main = True
        if ext == ".lua":
            code = strip_lua_comments(z.read(name).decode("utf-8", "replace"))
            for pattern, why in LUA_BLOCK:
                for m in re.finditer(pattern, code):
                    add("fail", why, rel, code.count("\n", 0, m.start()) + 1)
            for pattern, why in LUA_WARN:
                for m in re.finditer(pattern, code):
                    add("warn", why, rel, code.count("\n", 0, m.start()) + 1)
    if files and not (metadata or has_main):
        add("fail", "no metadata.xml or main.lua: this doesn't look like an Isaac mod")
    if stats["bytes"] > MAX_BYTES:
        add("fail", f"mod is {stats['bytes'] / 1e6:.0f} MB (limit {MAX_BYTES / 1e6:.0f} MB)")
    if stats["files"] > MAX_FILES:
        add("fail", f"mod has {stats['files']} files (limit {MAX_FILES})")
    result = "fail" if any(f["level"] == "fail" for f in findings) else "pass"
    return {"result": result, "findings": findings, "stats": stats, "metadata": metadata, "zip_root": root}


def check_repo(repo, ref, path=""):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return {"result": "fail", "findings": [{"level": "fail", "message": f"'{repo}' is not a GitHub owner/repo"}]}
    try:
        commit = resolve_commit(repo, ref)
        data = http_get(f"https://codeload.github.com/{repo}/zip/{commit}")
    except urllib.error.HTTPError as e:
        return {"result": "fail", "findings": [{"level": "fail",
                                                "message": f"couldn't download {repo}@{ref} (HTTP {e.code}); is the repo public?"}]}
    report = check_zip(data, path)
    report.update({"repo": repo, "ref": ref, "commit": commit, "path": path,
                   "download": f"https://codeload.github.com/{repo}/zip/{commit}",
                   "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    return report


def markdown(report):
    ok = report["result"] == "pass"
    lines = [f"### {'✅ Safety check passed' if ok else '❌ Safety check failed'}", ""]
    if report.get("commit"):
        lines.append(f"Checked `{report['repo']}` at commit `{report['commit'][:10]}`"
                     + (f", folder `{report['path']}`" if report.get("path") else "")
                     + f" — {report['stats']['files']} files, {report['stats']['bytes'] / 1e6:.1f} MB.")
        lines.append("")
    for level, title in (("fail", "Problems (must be fixed)"), ("warn", "For the admins to look at")):
        items = [f for f in report["findings"] if f["level"] == level]
        if items:
            lines.append(f"**{title}**")
            for f in items[:40]:
                where = f" — `{f['file']}" + (f":{f['line']}" if f.get("line") else "") + "`" if f.get("file") else ""
                lines.append(f"- {f['message']}{where}")
            if len(items) > 40:
                lines.append(f"- ...and {len(items) - 40} more")
            lines.append("")
    if ok and not report["findings"]:
        lines.append("Nothing to flag.")
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("ref")
    ap.add_argument("--path", default="")
    ap.add_argument("--json")
    a = ap.parse_args()
    report = check_repo(a.repo, a.ref, a.path)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    print(markdown(report))
    sys.exit(0 if report["result"] == "pass" else 1)


if __name__ == "__main__":
    main()

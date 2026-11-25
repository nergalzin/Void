#!/usr/bin/env python3
"""Launcher file search helper (type "/" followed by a path or a name).

Commands:
  search <query>   print a JSON list of {path, name, is_dir} (max 12 entries)
  open <path>      open a file/folder with its default app
  reveal <path>    show a file in the file manager (folders: open them)

Local only: lists directories and runs `fd` inside $HOME. No network, no history.
"""
import json
import os
import shutil
import subprocess
import sys

HOME = os.path.expanduser("~")
LIMIT = 12


def spawn(cmd):
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def entry(path):
    if not os.path.exists(path):
        return None
    return {"path": path, "name": os.path.basename(path) or path, "is_dir": os.path.isdir(path)}


def search(raw):
    q = raw.strip()
    if not q:
        return []
    if q.startswith("~"):
        q = HOME + q[1:]
    results, seen = [], set()

    def add(p):
        p = os.path.normpath(p)
        if p in seen or len(results) >= LIMIT:
            return
        e = entry(p)
        if e:
            seen.add(p)
            results.append(e)

    stripped = q.strip("/")
    if stripped == "":
        for d in (HOME, "/tmp", "/mnt", "/home"):
            add(d)
        return results

    # "/Documents" can mean /Documents or ~/Documents: try both, absolute first.
    candidates = [q]
    if not q.startswith(HOME):
        candidates.append(HOME + q)

    for cand in candidates:
        if os.path.isdir(cand):
            add(cand)
            try:
                kids = sorted(os.listdir(cand), key=lambda n: (not os.path.isdir(os.path.join(cand, n)), n.lower()))
            except OSError:
                kids = []
            for k in kids:
                if not k.startswith("."):
                    add(os.path.join(cand, k))
        elif os.path.exists(cand):
            add(cand)

    # Partial last segment: "/Docu" -> entries of the parent that contain "docu".
    for cand in candidates:
        parent, partial = os.path.split(cand)
        partial = partial.lower()
        if not partial or not os.path.isdir(parent):
            continue
        try:
            kids = os.listdir(parent)
        except OSError:
            continue
        kids.sort(key=lambda n: (not n.lower().startswith(partial), not os.path.isdir(os.path.join(parent, n)), n.lower()))
        for k in kids:
            if k.startswith(".") and not partial.startswith("."):
                continue
            if partial in k.lower():
                add(os.path.join(parent, k))

    # Plain name ("/report"): look for it under $HOME with fd.
    if len(results) < LIMIT - 2 and "/" not in stripped and len(stripped) >= 2 and shutil.which("fd"):
        try:
            out = subprocess.check_output(
                ["fd", "--follow", "--max-depth", "5", "--max-results", "30", "--color", "never", "-i", stripped, HOME],
                text=True, stderr=subprocess.DEVNULL, timeout=1.5,
            )
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            lines.sort(key=lambda p: (not os.path.isdir(p), len(p)))
            for l in lines:
                add(l)
        except (subprocess.SubprocessError, OSError):
            pass

    return results


def open_path(path):
    if os.path.exists(path):
        spawn(["xdg-open", path])


def reveal(path):
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        spawn(["xdg-open", path])
    elif shutil.which("dolphin"):
        spawn(["dolphin", "--select", path])
    else:
        spawn(["xdg-open", os.path.dirname(path) or HOME])


def main():
    if len(sys.argv) < 3:
        print("[]")
        return
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "search":
        print(json.dumps(search(arg), ensure_ascii=False))
    elif cmd == "open":
        open_path(arg)
    elif cmd == "reveal":
        reveal(arg)


if __name__ == "__main__":
    main()

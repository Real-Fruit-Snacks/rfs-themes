#!/usr/bin/env python3
"""Verify rfs-themes integrity, PrivacyNotes pn1: compliance, and Cyclorama Dawn invariants.

Exit codes (RFS CLI standard):
    0  all checks passed
    1  one or more checks failed
"""
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Load PrivacyNotes contrast engine from build-privacynotes.py
spec = importlib.util.spec_from_file_location("build_pn", os.path.join(HERE, "build-privacynotes.py"))
build_pn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_pn)


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main() -> int:
    errors = []

    def ok(msg):
        print(f"[ok] {msg}")

    def fail(msg):
        print(f"[x]  {msg}")
        errors.append(msg)

    # 1. Brand token sync
    b_tok = os.path.join(ROOT, "brand", "rfs.tokens.json")
    d_tok = os.path.join(ROOT, "docs", "assets", "rfs.tokens.json")
    if not os.path.exists(b_tok) or not os.path.exists(d_tok):
        fail("missing brand/rfs.tokens.json or docs/assets/rfs.tokens.json")
    elif sha256(b_tok) != sha256(d_tok):
        fail("brand/rfs.tokens.json != docs/assets/rfs.tokens.json")
    else:
        v = json.load(open(b_tok, encoding="utf-8"))["meta"]["version"]
        ok(f"rfs.tokens.json synced (v{v})")

    # 2. App manifest validation
    manifest_path = os.path.join(ROOT, "apps", "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    for app in manifest["apps"]:
        for rel in (app["path"], app["data"]):
            if not os.path.exists(os.path.join(ROOT, rel)):
                fail(f"manifest path missing: {rel}")
        for var in app["variants"]:
            if not os.path.exists(os.path.join(ROOT, var["preview"])):
                fail(f"variant preview missing: {var['preview']}")
    ok(f"apps/manifest.json valid ({len(manifest['apps'])} app(s))")

    # 3. PrivacyNotes pn1: grammar, canonical serialization, length, and 17/17 contrast checks
    pn_data = json.load(open(build_pn.THEMES_JSON, encoding="utf-8"))
    author = pn_data.get("author", "Real-Fruit-Snacks")
    codes_body = open(build_pn.CODES_TXT, encoding="utf-8").read() if os.path.exists(build_pn.CODES_TXT) else ""
    for t in pn_data["themes"]:
        name = t["name"]
        if len(name) > 20 or ":" in name or "," in name:
            fail(f"PrivacyNotes theme name invalid: {name!r}")
        canonical = build_pn.serialize_pn1(t, author)
        if len(canonical) > 512:
            fail(f"{t['id']}: pn1 code exceeds 512 chars ({len(canonical)})")
        if t["code"] != canonical:
            fail(f"{t['id']}: themes.json code does not match canonical serializer")
        if canonical not in codes_body:
            fail(f"{t['id']}: missing from apps/privacynotes/codes.txt")
        checks = build_pn.check_theme(t)
        bad = [ch for ch in checks if not ch[3]]
        if bad:
            fail(f"{t['id']}: failed PrivacyNotes contrast check(s): {bad}")
        p1 = os.path.join(build_pn.PREVIEW_DIR, f"{t['id']}.svg")
        p2 = os.path.join(build_pn.DOCS_PREVIEW_DIR, f"{t['id']}.svg")
        if not os.path.exists(p1) or not os.path.exists(p2) or sha256(p1) != sha256(p2):
            fail(f"{t['id']}: preview SVG missing or out of sync with docs/assets/")
    ok(f"PrivacyNotes themes verified ({len(pn_data['themes'])} variants, all 17/17 checks passing)")

    # 4. Brand code invariants (zero oklch gradients, zero native modals, zero private leaks)
    rx_oklch = re.compile(r"gradient\([^)]*in oklch")
    rx_modal = re.compile(r"\b(?:window\.)?(?:alert|confirm|prompt)\s*\(")
    rx_private = re.compile(r"\b(?:pn-selfhost|Eddy)\b")
    for r, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for fn in files:
            if fn == "verify-themes.py":
                continue
            fp = os.path.join(r, fn)
            rel = os.path.relpath(fp, ROOT)
            if fn.endswith((".css", ".html", ".js")):
                txt = open(fp, encoding="utf-8", errors="ignore").read()
                if rx_oklch.search(txt):
                    fail(f"in oklch gradient in {rel}")
                if fn.endswith(".js") and rx_modal.search(txt):
                    fail(f"native modal call in {rel}")
            if fn.endswith((".html", ".js", ".json", ".toml", ".md", ".py", ".txt")):
                txt = open(fp, encoding="utf-8", errors="ignore").read()
                if rx_private.search(txt):
                    fail(f"private repo reference in {rel}")
    if not errors:
        ok("zero oklch gradients, native modals, or private-repo references")
        ok("all rfs-themes checks passed")
        return 0
    print(f"[x]  verification failed with {len(errors)} error(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

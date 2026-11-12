#!/usr/bin/env python3
"""Give every game in the Megason store its gameplay screenshots and a flat
disc / cartridge image, taken from the LaunchBox Games Database.

Usage
  python3 launchbox_media.py                 -> updates megason.html in place
  python3 launchbox_media.py --html other.html --metadata Metadata.zip

It reads the titles already in the store (the built-in catalogue plus the
LaunchBox covers baked in by launchbox_covers.py), looks each one up in
LaunchBox's public metadata file, and builds the image links into the page
(window.PV_MEDIA). Run it again after launchbox_covers.py picks new games.
Only links are stored; no image files are downloaded.
Python 3.8+, standard library only.
"""
import argparse, json, os, re, sys, time, urllib.request, zipfile
import xml.etree.ElementTree as ET

META_URL = "https://gamesdb.launchbox-app.com/Metadata.zip"
IMG_BASE = "https://images.launchbox-app.com/"
UA = {"User-Agent": "MegasonMedia/1.0 (personal use)"}
PLATFORMS = {
    "md": "Sega Genesis", "saturn": "Sega Saturn", "snes": "Super Nintendo Entertainment System",
    "n64": "Nintendo 64", "ps1": "Sony Playstation", "gc": "Nintendo GameCube",
    "dc": "Sega Dreamcast", "gg": "Sega Game Gear", "gb": "Nintendo Game Boy",
    "ps2": "Sony Playstation 2", "x360": "Microsoft Xbox 360", "psp": "Sony PSP",
    "gba": "Nintendo Game Boy Advance", "wii": "Nintendo Wii", "nds": "Nintendo DS",
}
DISC = {"saturn", "ps1", "gc", "dc", "ps2", "x360", "psp", "wii"}  # everything else is a cartridge
MEDIA_TYPES = {True: ["Disc", "Fanart - Disc"], False: ["Cart - Front", "Fanart - Cart - Front", "Cart - 3D"]}
SHOT_TYPES = ["Screenshot - Gameplay", "Screenshot - Game Select", "Screenshot - Game Title"]
REGIONS = ["World", "North America", "United States", "Europe", "United Kingdom", "Japan", None, ""]
MARK = "<!--PV_MEDIA-->"


def norm(t):
    t = t.lower().replace("&", "and").replace("é", "e")
    t = re.sub(r"^the\s+", "", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def store_titles(html):
    """{platform key: set(titles)} from the built-in catalogue and the baked LaunchBox covers."""
    out = {k: set() for k in PLATFORMS}
    for m in re.finditer(r"\n  (\w+):\{name:'[^']*'.*?\n    titles:(\[.*?\])\}", html, re.S):
        k, arr = m.group(1), m.group(2)
        if k not in out:
            continue
        if arr.startswith('["'):
            out[k].update(json.loads(arr))
        else:
            out[k].update(s.replace("\\'", "'") for s in re.findall(r"'((?:\\'|[^'])*)'", arr))
    m = re.search(r"window\.PV_LAUNCHBOX=(\{.*?\});</script>", html, re.S)
    if m:
        for k, lst in json.loads(m.group(1)).get("systems", {}).items():
            if k in out:
                out[k].update(e["title"] for e in lst if e.get("title"))
    return out


def pick(options, n):
    """Up to n file names, preferred regions first, no duplicates."""
    ranked = sorted(options, key=lambda o: REGIONS.index(o[0]) if o[0] in REGIONS else len(REGIONS))
    seen, res = set(), []
    for _, fn in ranked:
        if fn not in seen:
            seen.add(fn)
            res.append(fn)
        if len(res) == n:
            break
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", default="megason.html")
    ap.add_argument("--metadata", default=None, help="an already downloaded Metadata.zip")
    a = ap.parse_args()
    with open(a.html, encoding="utf-8") as f:
        html = f.read()
    wanted = store_titles(html)
    want_norm = {k: {norm(t): t for t in ts} for k, ts in wanted.items()}

    zip_path = a.metadata or "Metadata.zip"
    if not os.path.exists(zip_path):
        print("Downloading the LaunchBox metadata file (large)...")
        req = urllib.request.Request(META_URL, headers=UA)
        with urllib.request.urlopen(req, timeout=300) as r, open(zip_path, "wb") as f:
            f.write(r.read())

    plat_key = {v: k for k, v in PLATFORMS.items()}
    games, imgs = {}, {}
    print("Reading metadata...")
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith("metadata.xml"))
        with z.open(name) as f:
            depth = 0
            for ev, el in ET.iterparse(f, events=("start", "end")):
                if ev == "start":
                    depth += 1
                    continue
                depth -= 1
                if depth != 1:
                    continue
                if el.tag == "Game":
                    k = plat_key.get(el.findtext("Platform"))
                    title = el.findtext("Name") or ""
                    if k and norm(title) in want_norm[k]:
                        games.setdefault((k, norm(title)), el.findtext("DatabaseID"))
                elif el.tag == "GameImage":
                    t = el.findtext("Type")
                    if t in SHOT_TYPES or t in MEDIA_TYPES[True] or t in MEDIA_TYPES[False]:
                        imgs.setdefault(el.findtext("DatabaseID"), []).append((t, el.findtext("Region"), el.findtext("FileName")))
                el.clear()

    media, found, total = {}, 0, sum(len(v) for v in want_norm.values())
    for (k, nt), gid in games.items():
        lst = imgs.get(gid, [])
        shots = []
        for st in SHOT_TYPES:
            shots += [fn for fn in pick([(r, fn) for t, r, fn in lst if t == st], 4) if fn not in shots]
            if len(shots) >= 4:
                break
        md = None
        for mt in MEDIA_TYPES[k in DISC]:
            got = pick([(r, fn) for t, r, fn in lst if t == mt], 1)
            if got:
                md = got[0]
                break
        if shots or md:
            media[f"{k}|{nt}"] = {"s": shots[:4], "m": md}
            found += 1
    data = {"base": IMG_BASE, "games": media}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tag = f"{MARK}<script>window.PV_MEDIA={payload};</script>{MARK}"
    if MARK in html:
        html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK), lambda m: tag, html, flags=re.S)
    else:
        html = html.replace('<script type="importmap">', tag + '\n<script type="importmap">', 1)
    with open(a.html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Media for {found} of {total} titles built into {a.html} ({len(payload)//1024} KB).")


if __name__ == "__main__":
    main()

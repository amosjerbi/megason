#!/usr/bin/env python3
"""Pick random games per system from the LaunchBox Games Database and give the
Pixel Vault store direct links to their front box art (no image files are saved).

Usage
  python3 launchbox_covers.py
      -> launchbox-links.json  (144 random games per system, title + cover link)
         Load it in the store: COVERS -> LOAD LAUNCHBOX LINKS.

  python3 launchbox_covers.py --embed pixel-vault.html
      -> also writes pixel-vault-launchbox.html with the links built in,
         so the store opens already stocked. Open that file in your browser.

  Options: --systems megadrive saturn   --per-system 30   --region Europe
           --seed 7 (repeat the same pick)   --files (old mode: download images)

LaunchBox has no web API. This reads its public daily metadata file
(Metadata.zip), which lists every game and the file name of each image; a cover
link is https://images.launchbox-app.com/ + that file name.
Python 3.8+, standard library only.
"""
import argparse, json, os, random, re, sys, time, urllib.request, zipfile
import xml.etree.ElementTree as ET

META_URL = "https://gamesdb.launchbox-app.com/Metadata.zip"
IMG_BASE = "https://images.launchbox-app.com/"
UA = {"User-Agent": "PixelVaultCovers/1.1 (personal use)"}
# store key -> (folder name for --files, LaunchBox platform name)
SYSTEMS = {
    "md":     ("megadrive", "Sega Genesis"),
    "saturn": ("saturn",    "Sega Saturn"),
    "snes":   ("snes",      "Super Nintendo Entertainment System"),
    "n64":    ("n64",       "Nintendo 64"),
    "ps1":    ("psx",       "Sony Playstation"),
    "gc":     ("gc",        "Nintendo GameCube"),
    "dc":     ("dreamcast", "Sega Dreamcast"),
    "gg":     ("gamegear",  "Sega Game Gear"),
    "gb":     ("gb",        "Nintendo Game Boy"),
}
ALIASES = {v[0]: k for k, v in SYSTEMS.items()} | {k: k for k in SYSTEMS} | {"genesis": "md", "playstation": "ps1", "gamecube": "gc", "gameboy": "gb", "game gear": "gg"}
REGION_ORDER = ["World", "North America", "United States", "Europe", "United Kingdom", "Japan", None, ""]
MARK = "<!--PV_LAUNCHBOX-->"


def fetch(url, dest, label=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as f:
        total, done = int(r.headers.get("Content-Length") or 0), 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if label and total:
                print(f"\r{label}: {done * 100 // total}%", end="", flush=True)
    if label:
        print()
    os.replace(dest + ".part", dest)


def load_metadata(zip_path, platforms):
    """Return ({db_id: (title, platform)}, {db_id: [(region, file_name)]}) for front box art."""
    games, images = {}, {}
    with zipfile.ZipFile(zip_path) as z:
        name = next((n for n in z.namelist() if n.lower().endswith("metadata.xml")), None)
        if not name:
            sys.exit("Metadata.xml was not found inside the zip; LaunchBox may have changed the format.")
        with z.open(name) as f:
            depth = 0
            for ev, el in ET.iterparse(f, events=("start", "end")):
                if ev == "start":
                    depth += 1
                    continue
                depth -= 1
                if depth != 1:  # only top-level records
                    continue
                if el.tag == "Game":
                    plat = el.findtext("Platform")
                    if plat in platforms:
                        gid, title = el.findtext("DatabaseID"), el.findtext("Name")
                        if gid and title:
                            games[gid] = (title, plat)
                elif el.tag == "GameImage" and el.findtext("Type") == "Box - Front":
                    gid, fn = el.findtext("DatabaseID"), el.findtext("FileName")
                    if gid and fn:
                        images.setdefault(gid, []).append((el.findtext("Region"), fn))
                el.clear()
    return games, images


def best_image(options, prefer):
    for region in ([prefer] if prefer else []) + REGION_ORDER:
        for r, fn in options:
            if r == region:
                return r, fn
    return options[0]


def safe_name(title):
    return re.sub(r'[\\/:*?"<>|]+', " ", title).strip().rstrip(".")[:120] or "game"


def embed(html_path, data, out_path):
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tag = f'{MARK}<script>window.PV_LAUNCHBOX={payload};</script>{MARK}'
    if MARK in html:  # replace links from an earlier run
        html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK), lambda m: tag, html, flags=re.S)
    elif '<script type="importmap">' in html:
        html = html.replace('<script type="importmap">', tag + '\n<script type="importmap">', 1)
    else:
        sys.exit("Could not find where to add the links in that HTML file. Is it the Pixel Vault store?")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS), help="md saturn snes n64 ps1 gc dc gg gb (folder names work too)")
    ap.add_argument("--per-system", type=int, default=144, help="covers per system (the store holds up to 144)")
    ap.add_argument("--region", default=None, help='preferred cover region, e.g. "Europe" or "Japan"')
    ap.add_argument("--seed", type=int, default=None, help="repeat the same random pick")
    ap.add_argument("--out", default="launchbox-links.json", help="links file to write")
    ap.add_argument("--embed", metavar="STORE_HTML", help="also write a copy of the store with the links built in")
    ap.add_argument("--metadata", default=None, help="use an already downloaded Metadata.zip")
    ap.add_argument("--files", metavar="FOLDER", nargs="?", const="covers", help="old mode: download the images into FOLDER instead")
    a = ap.parse_args()

    keys = []
    for s in a.systems:
        k = ALIASES.get(s.lower())
        if not k:
            sys.exit(f"Unknown system '{s}'. Use: {' '.join(SYSTEMS)}")
        keys.append(k)
    per = max(1, min(144, a.per_system))

    zip_path = a.metadata or "Metadata.zip"
    if not a.metadata and not (os.path.exists(zip_path) and time.time() - os.path.getmtime(zip_path) < 7 * 86400):
        print("Downloading the LaunchBox metadata file (large; reused for a week)...")
        fetch(META_URL, zip_path, "Metadata.zip")

    wanted = {SYSTEMS[k][1]: k for k in keys}
    print("Reading metadata...")
    games, images = load_metadata(zip_path, set(wanted))
    rnd = random.Random(a.seed)
    out = {"source": "LaunchBox Games Database", "created": time.strftime("%Y-%m-%d"), "systems": {}}
    for plat, k in wanted.items():
        pool = [(gid, t) for gid, (t, p) in games.items() if p == plat and gid in images]
        rnd.shuffle(pool)
        seen, picked = set(), []
        for gid, title in pool:
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            region, fn = best_image(images[gid], a.region)
            picked.append({"title": title, "url": IMG_BASE + fn, "region": region or ""})
            if len(picked) >= per:
                break
        picked.sort(key=lambda e: e["title"].lower())
        out["systems"][k] = picked
        print(f"  {plat}: {len(pool)} games with front box art, took {len(picked)}")
        if not pool:
            print(f"    (no matches: LaunchBox may name this platform differently than '{plat}')")

    if a.files:
        ok = failed = 0
        for k, entries in out["systems"].items():
            folder = os.path.join(a.files, SYSTEMS[k][0])
            os.makedirs(folder, exist_ok=True)
            for e in entries:
                dest = os.path.join(folder, safe_name(e["title"]) + (os.path.splitext(e["url"])[1] or ".jpg"))
                if os.path.exists(dest):
                    ok += 1
                    continue
                try:
                    fetch(e["url"], dest)
                    ok += 1
                    time.sleep(0.15)
                except Exception as ex:
                    failed += 1
                    print("   FAILED", e["title"], "-", ex)
        print(f"\nDownloaded {ok} images into '{a.files}' ({failed} failed). In the store: COVERS -> PICK A MEDIA FOLDER.")
        return

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    total = sum(len(v) for v in out["systems"].values())
    print(f"\nWrote {total} cover links to {a.out}. In the store: COVERS -> LOAD LAUNCHBOX LINKS.")
    if a.embed:
        base, ext = os.path.splitext(a.embed)
        dest = base.replace("-launchbox", "") + "-launchbox" + (ext or ".html")
        embed(a.embed, out, dest)
        print(f"Wrote {dest} with the links built in. Open it in your browser.")


if __name__ == "__main__":
    main()

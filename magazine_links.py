#!/usr/bin/env python3
"""Fill the Megason store's magazine table with the old Israeli games magazines
Wiz (וויז) and Freak (פריק), as catalogued by the abandonware magazine archive
(https://github.com/abandonware-magazines/abandonware-magazines.github.io,
its _data/magazines.json, the same list behind magazines/wiz.html and freak.html).

Usage
  python3 magazine_links.py                -> updates megason.html in place
  python3 magazine_links.py --html other.html

Only links are stored (window.PV_MAGS): each issue's cover image on the archive
site and its scan on Google Drive, which the store opens in Drive's own viewer.
Nothing is downloaded. Run it again to pick up issues the archive adds later.
Python 3.8+, standard library only.
"""
import argparse, json, re, urllib.request

SITE = "https://abandonware-magazines.github.io"
MAGS = [("wiz", "Wiz", "וויז"), ("freak", "Freak", "פריק")]
MARK = "<!--PV_MAGS-->"
UA = {"User-Agent": "MegasonMagazines/1.0 (personal use)"}


RAW = "https://raw.githubusercontent.com/abandonware-magazines/abandonware-magazines.github.io/master"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8")


def issues(key, data):
    mag = next(m for m in data if m["id"] == key)
    front = re.search(r"^description:\s*(.+)$", get(f"{RAW}/magazines/{key}.md"), re.M)
    out = []
    for it in mag["issues"]:
        fid = re.search(r"(?:/d/|id=)([\w-]+)", it.get("link", ""))
        if fid:
            out.append({"n": str(it["issue"]), "cover": f"{SITE}/images/magazines/{key}/{key}{it['issue']}.jpg",
                        "id": fid.group(1), "credit": it.get("scanned_by", "")})
    return f"{SITE}/magazines/{key}.html", (front.group(1).strip() if front else ""), out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", default="megason.html")
    a = ap.parse_args()
    data = json.loads(get(f"{RAW}/_data/magazines.json"))
    mags = []
    for key, name, he in MAGS:
        url, blurb, lst = issues(key, data)
        mags.append({"key": key, "name": name, "he": he, "source": url, "blurb": blurb, "issues": lst})
        print(f"{name}: {len(lst)} issues")
    payload = json.dumps({"mags": mags}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tag = f"{MARK}<script>window.PV_MAGS={payload};</script>{MARK}"
    with open(a.html, encoding="utf-8") as f:
        html = f.read()
    if MARK in html:
        html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK), lambda m: tag, html, flags=re.S)
    else:
        html = html.replace('<script type="importmap">', tag + '\n<script type="importmap">', 1)
    with open(a.html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Magazine links built into {a.html} ({len(payload) // 1024} KB).")


if __name__ == "__main__":
    main()

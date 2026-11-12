# Megason

A walk-through 3D retro game store in the browser (three.js), with real box art and gameplay from the LaunchBox Games Database and the Israeli games magazines Wiz and Freak on the magazine table.

**Play:** https://amosjerbi.github.io/megason/

## Updating the data

- `python3 launchbox_covers.py --metadata Metadata.zip` – picks cover art links per system (download `Metadata.zip` from LaunchBox first; it isn't stored in this repo).
- `python3 launchbox_media.py` – adds gameplay screenshots and disc/cartridge images for each title.
- `python3 magazine_links.py` – refreshes the Wiz and Freak issue links from the [abandonware magazine archive](https://github.com/abandonware-magazines/abandonware-magazines.github.io).

All three only store links in `megason.html`; no images are downloaded.

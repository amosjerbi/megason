# Megason

A walk-through 3D retro game store in the browser (three.js), with real box art and gameplay from the LaunchBox Games Database and the Israeli games magazines Wiz and Freak on the magazine table.

**Play:** https://amosjerbi.github.io/megason/

![The storefront at night](screenshots/storefront.jpg)

| | |
|---|---|
| ![Inside the store](screenshots/inside.jpg) | ![Consoles and controllers in the glass cases](screenshots/cases.jpg) |
| Walk the aisles: shelves per system, glass counters, wall CRTs | Consoles with matching controllers in the glass cases |
| ![A game pop-up with box art, cartridge and gameplay](screenshots/game.jpg) | ![The magazine table](screenshots/magtable.jpg) |
| Click any game for its box art, disc/cartridge and gameplay shots | The magazine table with real Wiz and Freak issues |

![Reading an issue of Freak](screenshots/magazine.jpg)

## Updating the data

- `python3 launchbox_covers.py --metadata Metadata.zip` – picks cover art links per system (download `Metadata.zip` from LaunchBox first; it isn't stored in this repo).
- `python3 launchbox_media.py` – adds gameplay screenshots and disc/cartridge images for each title.
- `python3 magazine_links.py` – refreshes the Wiz and Freak issue links from the [abandonware magazine archive](https://github.com/abandonware-magazines/abandonware-magazines.github.io).

All three only store links in `megason.html`; no images are downloaded.

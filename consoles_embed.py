#!/usr/bin/env python3
"""Embed the console box photos in consoles/ into megason.html as small data: URIs.

Browsers won't let WebGL use image files when the page is opened straight from disk (file://),
so megason.html uses these embedded copies there; on a web server it loads consoles/<name> as usual.
Run again after adding, replacing or removing photos in consoles/.
"""
import base64, io, json, pathlib, re
from PIL import Image

ROOT = pathlib.Path(__file__).parent
HTML = ROOT / 'megason.html'
MAX = 640  # longest side, plenty for a box on the back wall

data = {}
for f in sorted((ROOT / 'consoles').iterdir()):
    if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        continue
    im = Image.open(f).convert('RGB')
    im.thumbnail((MAX, MAX))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82, optimize=True)
    data['consoles/' + f.name] = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

line = '<!--CONSOLE_LOCAL--><script>window.CONSOLE_LOCAL=' + json.dumps(data, separators=(',', ':')) + ';</script>'
s = HTML.read_text()
if '<!--CONSOLE_LOCAL-->' in s:
    s = re.sub(r'<!--CONSOLE_LOCAL--><script>.*?</script>', lambda m: line, s, count=1, flags=re.S)
else:
    s = s.replace('<!--PV_LAUNCHBOX-->', line + '\n<!--PV_LAUNCHBOX-->', 1)
HTML.write_text(s)
print(f'embedded {len(data)} photos, {len(line) // 1024} KB')

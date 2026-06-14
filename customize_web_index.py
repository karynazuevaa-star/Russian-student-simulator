from pathlib import Path
import sys
from urllib.request import urlopen


index_path = Path(sys.argv[1])
html = index_path.read_text(encoding="utf-8")
pygbag_cdn = "https://pygame-web.github.io/cdn/0.9.3/"

with urlopen(pygbag_cdn + "pythons.js", timeout=30) as response:
    index_path.with_name("pythons.js").write_bytes(response.read())

html = html.replace(
    f'src="{pygbag_cdn}pythons.js"',
    'src="pythons.js"',
    1,
)
html = html.replace(
    'data-os="vtx,snd,gui"',
    'data-os="snd,gui"',
    1,
)
html = html.replace(
    'xtermjs : "1"',
    'xtermjs : "0"',
    1,
)

html = html.replace(
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '<meta name="viewport" content="width=device-width, height=device-height, '
    'initial-scale=1, maximum-scale=1, user-scalable=no">',
    1,
)
html = html.replace(
    '<meta name="viewport" content="height=device-height, initial-scale=1.0">',
    "",
    1,
)
html = html.replace(
    "    <style>",
    """    <style>
        html, body {
            margin: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            overscroll-behavior: none;
            touch-action: none;
            background: #7f7f7f;
        }
        canvas {
            touch-action: none;
            user-select: none;
            -webkit-user-select: none;
            -webkit-touch-callout: none;
        }""",
    1,
)

index_path.write_text(html, encoding="utf-8")

from pathlib import Path
import sys

from PIL import Image


def optimize_png(path):
    with Image.open(path) as image:
        has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
        source = image.convert("RGBA" if has_alpha else "RGB")
        method = 2 if has_alpha else 0
        optimized = source.quantize(colors=256, method=method, dither=0)
        optimized.save(path, optimize=True, compress_level=9)


asset_dir = Path(sys.argv[1])
for png_path in asset_dir.rglob("*.png"):
    optimize_png(png_path)

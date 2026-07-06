"""Agentic OS branding — the crescent-moon logo.

Provides the moon as a raster image (system-tray icon, .ico for the exe) and
as an SVG string (browser favicon / titlebar). PIL is only needed for the
raster helpers, so server.py can import MOON_SVG without pulling in Pillow.
"""

MOON_COLOR = (217, 119, 87, 255)  # brand accent (#d97757)

# Crescent geometry (fraction of the box): a disc with an offset disc carved
# out, tuned to a thin, sharp-tipped crescent. Shared by the SVG and raster so
# the browser favicon, titlebar, tray, and exe icon all match exactly.
_DISC_C, _DISC_R = (0.50, 0.50), 0.42
_CUT_C, _CUT_R = (0.72, 0.50), 0.44

# Thin crescent via an SVG mask (disc minus offset disc), warm gradient.
# viewBox 24 → multiply fractions by 24.
MOON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<defs><linearGradient id="moonG" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#f2b79f"/><stop offset="1" stop-color="#d97757"/>'
    '</linearGradient>'
    '<mask id="moonM"><rect width="24" height="24" fill="#000"/>'
    '<circle cx="12" cy="12" r="10.08" fill="#fff"/>'
    '<circle cx="17.28" cy="12" r="10.56" fill="#000"/></mask></defs>'
    '<rect width="24" height="24" fill="url(#moonG)" mask="url(#moonM)"/>'
    '</svg>'
)


def moon_image(size: int = 256, color=MOON_COLOR):
    """A thin crescent-moon RGBA image, carved from two overlapping discs."""
    from PIL import Image, ImageChops, ImageDraw
    ss = 4  # supersample for smooth edges
    s = size * ss

    def _disc(center, radius):
        m = Image.new("L", (s, s), 0)
        cx, cy, r = center[0] * s, center[1] * s, radius * s
        ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        return m

    crescent = ImageChops.subtract(_disc(_DISC_C, _DISC_R), _disc(_CUT_C, _CUT_R))
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out = Image.composite(Image.new("RGBA", (s, s), color), out, crescent)
    return out.resize((size, size), Image.LANCZOS)


def write_ico(path: str = "AgenticOS.ico"):
    img = moon_image(256)
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return path


if __name__ == "__main__":
    import sys
    write_ico()
    if "--png" in sys.argv:
        moon_image(256).save("moon-preview.png")
    print("wrote AgenticOS.ico")

"""Grainy colour glows on off-white, in the style of the Collective studio session prints.

Usage: python3 make_background.py OUT.jpg WIDTH HEIGHT
"""
import sys
import numpy as np
from PIL import Image

out, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rng = np.random.default_rng(7)
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
img = np.empty((H, W, 3), np.float32)
img[:] = (251, 250, 246)

def glow(cx, cy, rx, ry, color, strength=1.0):
    # soft elliptical falloff, then dithered so the edge dissolves into grain
    d = np.sqrt(((x - cx * W) / (rx * W)) ** 2 + ((y - cy * H) / (ry * H)) ** 2)
    a = np.clip(1 - d, 0, 1) ** 1.6 * strength
    a = np.clip(a + (rng.random((H, W), dtype=np.float32) - 0.5) * 0.55 * np.sqrt(a * (1 - a) + 1e-4) * 2, 0, 1)
    img[:] = img * (1 - a[..., None]) + np.array(color, np.float32) * a[..., None]

glow(1.04, -0.08, 0.34, 0.62, (255, 222, 20), 1.0)     # yellow, top right
glow(1.06, 0.00, 0.16, 0.30, (255, 236, 90), 0.9)      # paler core
glow(-0.06, 1.08, 0.26, 0.46, (60, 120, 255), 0.85)    # blue, bottom left

img += (rng.random((H, W, 1), dtype=np.float32) - 0.5) * 9  # fine overall grain
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, quality=93)
print("background ok", W, H)

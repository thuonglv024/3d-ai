import sys
sys.stdout.reconfigure(encoding='utf-8')
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DIR = ROOT / "backend" / "scripts" / "test_renders"
TEST_DIR.mkdir(parents=True, exist_ok=True)

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    clean = hex_str.lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    try:
        return tuple(int(clean[i : i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (200, 190, 180)

def adjust_color(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return (
        min(255, max(0, int(rgb[0] * factor))),
        min(255, max(0, int(rgb[1] * factor))),
        min(255, max(0, int(rgb[2] * factor))),
    )

def create_studio_background(w: int = 800, h: int = 1067) -> Image.Image:
    # Warm Ivory / Off-white background matching MORPH brand: #FAF7F0 to #ECE7DE
    bg = Image.new("RGB", (w, h), (250, 247, 240))
    draw = ImageDraw.Draw(bg)
    
    # Subtle vertical gradient
    for y in range(h):
        t = y / h
        r = int(250 * (1 - t * 0.05) + 236 * (t * 0.05))
        g = int(247 * (1 - t * 0.06) + 231 * (t * 0.06))
        b = int(240 * (1 - t * 0.08) + 222 * (t * 0.08))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
        
    # Soft radial studio spotlight
    light = Image.new("L", (w, h), 0)
    ldraw = ImageDraw.Draw(light)
    ldraw.ellipse([w*0.1, h*0.1, w*0.9, h*0.8], fill=40)
    light = light.filter(ImageFilter.GaussianBlur(120))
    
    # Blend spotlight
    light_layer = Image.new("RGB", (w, h), (255, 253, 248))
    bg = Image.composite(light_layer, bg, light)
    return bg

print("Test generator setup ok")

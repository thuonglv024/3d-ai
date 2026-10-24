"""Render QA avatar GLBs to PNG (front + side) with a flat-shaded silhouette."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "output" / "runs" / "qa-avatars"
OUT = SRC / "renders"
OUT.mkdir(parents=True, exist_ok=True)


def render(mesh: trimesh.Trimesh, path: Path, plane: str) -> None:
    v = np.asarray(mesh.vertices)
    f = np.asarray(mesh.faces)
    w, h = 420, 640
    img = Image.new("RGB", (w, h), (250, 248, 244))
    draw = ImageDraw.Draw(img)
    a = v[:, 0] if plane == "front" else v[:, 2]
    b = v[:, 1]
    scale = min((w - 80) / max(float(np.ptp(a)), 1e-6), (h - 60) / max(float(np.ptp(b)), 1e-6))
    px = (w - float(np.ptp(a)) * scale) / 2 + (a - a.min()) * scale
    py = h - 30 - (b - b.min()) * scale
    p = [np.stack([px[f[:, i]], py[f[:, i]]], axis=1) for i in range(3)]
    normals = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    shade = np.clip(0.40 + 0.60 * np.abs(normals[:, 2] if plane == "front" else normals[:, 0]), 0, 1)
    for i in np.argsort(-v[f][:, :, 1].mean(axis=1)):
        c = int(112 + 108 * shade[i])
        draw.polygon([tuple(p[0][i]), tuple(p[1][i]), tuple(p[2][i])], fill=(c, c - 7, c - 16))
    img.save(path)


for glb in sorted(SRC.glob("*.glb")):
    mesh = trimesh.load(glb, force="mesh")
    render(mesh, OUT / f"{glb.stem}-front.png", "front")
    render(mesh, OUT / f"{glb.stem}-side.png", "side")
print("rendered", len(list(OUT.glob('*.png'))), "images ->", OUT)

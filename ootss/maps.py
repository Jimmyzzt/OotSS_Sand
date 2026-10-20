import concurrent.futures
import math
import subprocess
import urllib.request
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw

from .common import read_json, write_json

REPO = "https://github.com/joric/ootss.git"
ASSETS = "https://joric.github.io/ootss_tileset"


def layer(z):
    # Exactly the upstream ordered, inclusive heightRanges loop.
    result = "unknown"
    for name, a, b in [("overworld", -4, 10), ("sky", 10, 75), ("underworld", -57, -4)]:
        if a <= z <= b:
            result = name
    return result


def download(url, path):
    path = Path(path)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(url, timeout=40).read()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)
    return path


def import_map(
    root="cache/map", workers=6, layers=("overworld",), catalog_name="catalog.json"
):
    root = Path(root)
    upstream = root / "upstream"
    if not upstream.exists():
        root.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                REPO,
                str(upstream),
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(upstream),
                "sparse-checkout",
                "set",
                "data",
                "js/lib/imageSearch",
            ],
            check=True,
        )
    sha = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    markers = read_json(upstream / "data/markers.json")["features"]
    index = read_json(upstream / "js/lib/imageSearch/index.json")
    image_names = {Path(x["name"]).stem for x in index}
    levels = {}
    for f in markers:
        p, xyz = f["properties"], f["geometry"]["coordinates"]
        if p.get("type") != "Level_Entry" or layer(xyz[2]) not in layers:
            continue
        name = p["name"]
        row = levels.setdefault(
            name,
            {
                "level_id": name,
                "area": p.get("area"),
                "map_layer": layer(xyz[2]),
                "entries": [],
                "map_url": "https://joric.github.io/ootss/#" + quote(name),
                "reference": str((root / "images" / (name + ".webp")).resolve())
                if name in image_names
                else None,
            },
        )
        row["entries"].append({"marker_id": p["id"], "coordinates": xyz})
    errors = []

    def fetch(row):
        if row["reference"]:
            try:
                download(
                    f"{ASSETS}/images/levels/{quote(row['level_id'])}.webp",
                    row["reference"],
                )
            except (OSError, ValueError) as exc:
                return {"level_id": row["level_id"], "error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        errors = [e for e in pool.map(fetch, levels.values()) if e]
    result = {
        "source": REPO,
        "commit": sha,
        "license": "Unlicense",
        "asset_base": ASSETS,
        "levels": list(levels.values()),
        "download_errors": errors,
        "audit": {
            "index_count": len(index),
            "target_level_count": len(levels),
            "missing_images": [n for n, r in levels.items() if not r["reference"]],
            "multiple_entries": [n for n, r in levels.items() if len(r["entries"]) > 1],
            "index_without_any_marker": sorted(
                image_names - {f["properties"].get("name") for f in markers}
            ),
        },
    }
    write_json(root / catalog_name, result)
    return result


def terrain_crop(
    bounds, out, root="cache/map", zoom=4, annotate=True, map_layer="overworld"
):
    if map_layer not in {"overworld", "sky", "underworld"}:
        raise ValueError("Unknown physical map")
    """Joric CRS, bounds=(left,bottom,right,top). Only requested tiles downloaded."""
    left, bottom, right, top = bounds
    scale = 512 * 2**zoom / 190
    x0, y0 = math.floor((left + 24.5) * scale), math.floor((170.5 - top) * scale)
    x1, y1 = math.ceil((right + 24.5) * scale), math.ceil((170.5 - bottom) * scale)
    im = Image.new("RGB", (x1 - x0, y1 - y0))
    for tx in range(x0 // 512, (x1 - 1) // 512 + 1):
        for ty in range(y0 // 512, (y1 - 1) // 512 + 1):
            name = f"tiles/{map_layer}_64k/{zoom}/{ty}/{tx}.webp"
            tile = download(f"{ASSETS}/{name}", Path(root) / name)
            with Image.open(tile) as t:
                im.paste(t.convert("RGB"), (tx * 512 - x0, ty * 512 - y0))
    if annotate:
        draw = ImageDraw.Draw(im)
        for row in read_json(
            Path(root)
            / ("catalog_all.json" if map_layer != "overworld" else "catalog.json")
        )["levels"]:
            if row.get("map_layer", "overworld") != map_layer:
                continue
            for marker in row["entries"]:
                x, y, _ = marker["coordinates"]
                if left <= x <= right and bottom <= y <= top:
                    px, py = (x + 24.5) * scale - x0, (170.5 - y) * scale - y0
                    draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill="#ff2255")
                    draw.text(
                        (px + 5, py),
                        row["level_id"],
                        fill="white",
                        stroke_width=1,
                        stroke_fill="black",
                        font_size=11,
                    )
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out

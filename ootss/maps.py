import concurrent.futures
import subprocess
import urllib.request
from pathlib import Path
from urllib.parse import quote

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


def import_map(root="cache/map", workers=6):
    root = Path(root)
    upstream = root / "upstream"
    if not upstream.exists():
        root.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(upstream)], check=True)
        subprocess.run(["git", "-C", str(upstream), "sparse-checkout", "set", "data", "js/lib/imageSearch"], check=True)
    sha = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    markers = read_json(upstream / "data/markers.json")["features"]
    index = read_json(upstream / "js/lib/imageSearch/index.json")
    image_names = {Path(x["name"]).stem for x in index}
    levels = {}
    for f in markers:
        p, xyz = f["properties"], f["geometry"]["coordinates"]
        if p.get("type") != "Level_Entry" or layer(xyz[2]) != "overworld":
            continue
        name = p["name"]
        row = levels.setdefault(name, {"level_id": name, "area": p.get("area"), "map_layer": "overworld", "entries": [],
            "map_url": "https://joric.github.io/ootss/#" + quote(name), "reference": str((root / "images" / (name + ".webp")).resolve()) if name in image_names else None})
        row["entries"].append({"marker_id": p["id"], "coordinates": xyz})
    errors = []
    def fetch(row):
        if row["reference"]:
            try:
                download(f"{ASSETS}/images/levels/{quote(row['level_id'])}.webp", row["reference"])
            except Exception as exc:
                return {"level_id": row["level_id"], "error": str(exc)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        errors = [e for e in pool.map(fetch, levels.values()) if e]
    result = {"source": REPO, "commit": sha, "license": "Unlicense", "asset_base": ASSETS,
              "levels": list(levels.values()), "download_errors": errors,
              "audit": {"index_count": len(index), "target_level_count": len(levels),
                        "missing_images": [n for n, r in levels.items() if not r["reference"]],
                        "multiple_entries": [n for n, r in levels.items() if len(r["entries"]) > 1],
                        "index_without_any_marker": sorted(image_names - {f["properties"].get("name") for f in markers})}}
    write_json(root / "catalog.json", result)
    return result

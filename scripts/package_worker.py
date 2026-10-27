"""Package only public atlas assets for asset-first Cloudflare hosting."""

import argparse
import base64
import json
import re
import shutil
import tarfile
import urllib.request
from pathlib import Path

from scripts.package_site import package

WORLDS = ("overworld", "sky", "underworld")


def tile_svg(images, size):
    """Embed original pixels without resampling or another lossy encode."""
    items = []
    for x, y, content in images:
        encoded = base64.b64encode(content).decode("ascii")
        items.append(
            f'<image x="{x}" y="{y}" width="512" height="512" '
            f'href="data:image/webp;base64,{encoded}"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{size}" viewBox="0 0 {size} {size}">' + "".join(items) + "</svg>"
    )


def prepare_tiles(revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid pinned tileset revision")
    cache = Path("cache/map/packed") / revision / "v1"
    if (cache / "complete.json").exists():
        return cache / "tiles"
    archive = Path("cache/map/archives") / f"{revision}.tar.gz"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        url = f"https://codeload.github.com/joric/ootss_tileset/tar.gz/{revision}"
        partial = archive.with_suffix(".partial")
        with (
            urllib.request.urlopen(url, timeout=120) as response,
            partial.open("wb") as out,
        ):
            shutil.copyfileobj(response, out, length=1024 * 1024)
        partial.replace(archive)
    sources = cache / "sources"
    marker = cache / "sources-complete.json"
    if not marker.exists():
        count = 0
        # Never extract member paths, permissions or links from an archive.
        with tarfile.open(archive, "r|gz") as stream:
            for member in stream:
                match = re.fullmatch(
                    r"[^/]+/tiles/(overworld|sky|underworld)_64k/([457])/(\d+)/(\d+)\.webp",
                    member.name,
                )
                if not member.isfile() or not match:
                    continue
                world, z, y, x = match.groups()
                if int(y) >= 2 ** int(z) or int(x) >= 2 ** int(z):
                    raise ValueError("Invalid source tile coordinate")
                target = sources / world / z / y / f"{x}.webp"
                target.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as content, target.open("wb") as out:
                    shutil.copyfileobj(content, out)
                count += 1
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"revision": revision, "files": count}))
        print(f"Cached {count} pinned source tiles", flush=True)
    files = 0
    for world in WORLDS:
        for z in (4, 5, 6):
            for y in range(2**z):
                folder = cache / "tiles" / world / str(z) / str(y)
                folder.mkdir(parents=True, exist_ok=True)
                for x in range(2**z):
                    images = []
                    for dy in range(2 if z == 6 else 1):
                        for dx in range(2 if z == 6 else 1):
                            source_z = 7 if z == 6 else z
                            source_y = y * 2 + dy if z == 6 else y
                            source_x = x * 2 + dx if z == 6 else x
                            source = (
                                sources
                                / world
                                / str(source_z)
                                / str(source_y)
                                / f"{source_x}.webp"
                            )
                            if source.exists():
                                images.append((dx * 512, dy * 512, source.read_bytes()))
                    (folder / f"{x}.svg").write_text(
                        tile_svg(images, 1024 if z == 6 else 512), encoding="utf-8"
                    )
                    files += 1
            print(f"Packed {world} zoom {z}", flush=True)
    (cache / "complete.json").write_text(
        json.dumps({"revision": revision, "files": files})
    )
    return cache / "tiles"


def package_worker(destination="dist/worker", complete=False):
    destination = Path(destination)
    if destination.exists():
        target, build_root = destination.resolve(), Path("dist").resolve()
        if target == build_root or not target.is_relative_to(build_root):
            raise ValueError("Only a dedicated directory inside dist may be replaced")
        shutil.rmtree(target)
    package(destination=destination)
    revision = json.loads(Path("data/map_assets.json").read_text(encoding="utf-8"))[
        "tileset_revision"
    ]
    (destination / "_redirects").write_text(
        "/backup https://jimmyzzt.github.io/OotSS_Sand/ 302\n"
        f"/tiles/* https://raw.githubusercontent.com/joric/ootss_tileset/{revision}/tiles/:splat 302\n",
        encoding="utf-8",
    )
    (destination / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "/assets/*\n  Cache-Control: public, max-age=86400\n"
        "/tiles/*\n  Cache-Control: public, max-age=86400\n"
        "/map-tiles/*\n  Cache-Control: public, max-age=31536000, immutable\n",
        encoding="utf-8",
    )
    (destination / "404.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>未找到页面 · 沉星之序</title><h1>未找到页面</h1>"
        '<p><a href="/">返回攻略地图</a> · '
        '<a href="https://jimmyzzt.github.io/OotSS_Sand/">GitHub Pages 备用站</a></p>',
        encoding="utf-8",
    )
    (destination / "robots.txt").write_text(
        "User-agent: *\nDisallow: /api/\nDisallow: /feedback-admin\n", encoding="utf-8"
    )
    if complete:
        packed = prepare_tiles(revision)
        shutil.copytree(packed, destination / "map-tiles" / revision)
        html = (destination / "index.html").read_text(encoding="utf-8")
        hosting = json.dumps(
            {"packedTileBase": f"map-tiles/{revision}", "maxNativeZoom": 6}
        )
        html = html.replace(
            "<script>const DATA=",
            f"<script>globalThis.ATLAS_HOSTING={hosting};</script><script>const DATA=",
            1,
        )
        (destination / "index.html").write_text(html, encoding="utf-8")
    files = [p for p in destination.rglob("*") if p.is_file()]
    if len(files) > 20000 or any(p.stat().st_size > 25 * 1024 * 1024 for p in files):
        raise ValueError("Static assets exceed the Workers Free per-version limits")
    print(f"Worker public assets: {len(files)} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    package_worker(complete=args.complete)

"""Save portable P4 provenance and verify used cached assets against a pinned commit."""

import concurrent.futures
import hashlib
import urllib.request
from pathlib import Path

from ootss.common import read_json, write_json

ASSET_COMMIT = "4e7b655375fbc104d69d742ad42d69fd5dd7fd5c"


def main():
    out = Path("results/p4")
    review = read_json(out / "reviewed.json")
    catalog = read_json("cache/map/catalog.json")
    names = {e["level_id"] for e in review["events"]}
    used = [r for r in catalog["levels"] if r["level_id"] in names]
    assets = [
        (Path(r["reference"]), f"images/levels/{r['level_id']}.webp") for r in used
    ]
    assets.extend(
        (p, p.relative_to("cache/map").as_posix())
        for p in Path("cache/map/tiles").rglob("*.webp")
    )

    def verify(item):
        path, name = item
        url = f"https://raw.githubusercontent.com/joric/ootss_tileset/{ASSET_COMMIT}/{name}"
        data = path.read_bytes()
        remote = urllib.request.urlopen(url, timeout=40).read()
        return {
            "path": name,
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "matches_pinned_commit": remote == data,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        verified = list(pool.map(verify, assets))
    assert all(a["matches_pinned_commit"] for a in verified), (
        "Asset changed: inspect provenance before release"
    )
    write_json(
        out / "map_catalog.json",
        {
            **{k: catalog[k] for k in ("source", "commit", "license", "audit")},
            "asset_commit": ASSET_COMMIT,
            "levels": used,
            "asset_verification": verified,
        },
    )
    scan = read_json("runs/p4_check/scan.json")
    matches = read_json("runs/p4_check/matches.json")
    machine = {
        "scan_cache_key": scan["cache_key"],
        "transitions": scan["transitions"],
        "scan_seconds": scan["scan_seconds"],
        "match_seconds": matches["seconds"],
        "samples": [
            {k: s[k] for k in ("time", "status", "candidates")}
            for s in matches["samples"]
        ],
    }
    write_json(out / "machine.json", machine)
    endpoint = "https://api.bilibili.com/x/web-interface/view?bvid=BV13FH96bE4m"
    request = urllib.request.Request(
        endpoint,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"},
    )
    import json

    response = json.loads(
        urllib.request.urlopen(request, timeout=20).read().decode("utf-8")
    )
    write_json(
        out / "video_source.json",
        {
            "endpoint": endpoint,
            "code": response["code"],
            "title": response["data"]["title"],
            "bvid": response["data"]["bvid"],
            "page": response["data"]["pages"][3],
            "parameter_documentation": "https://player.bilibili.com/",
            "link_validation": "Official player documentation confirms p (1-based) and t (seconds). API confirms P4 CID/duration. Browser playback itself was not tested.",
        },
    )
    print(
        f"Verified {len(verified)} used assets; saved source, catalog and independent machine output"
    )


if __name__ == "__main__":
    main()

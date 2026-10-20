"""After an index P is inserted, match original CIDs to current anthology parts."""

import json
import urllib.request

from ootss.common import read_json, write_json


def link_map(original, pages):
    current = {p["cid"]: p["page"] for p in pages}
    missing = [p["cid"] for p in original["parts"] if p["cid"] not in current]
    if missing:
        raise ValueError(f"Original CIDs missing from new anthology: {missing}")
    return {
        "version": 1,
        "matched_by": "immutable CID, source part remains unchanged",
        "parts": {
            str(p["part_number"]): {"part": current[p["cid"]]}
            for p in original["parts"]
        },
    }


if __name__ == "__main__":
    original = read_json("results/series/manifest.json")
    request = urllib.request.Request(
        f"https://api.bilibili.com/x/web-interface/view?bvid={original['bvid']}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response = json.loads(urllib.request.urlopen(request, timeout=30).read())
    if response.get("code") != 0:
        raise ValueError("Bilibili metadata request failed")
    result = link_map(original, response["data"]["pages"])
    write_json("data/video_links.json", result)
    print("Updated CID-based link mapping. Rebuild with python -m ootss atlas.")

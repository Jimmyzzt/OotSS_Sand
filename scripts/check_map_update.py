"""Compare a fetched upstream ref without changing pinned reviews or catalogues."""

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from ootss.common import read_json, write_json


def entry_changes(before, after):
    def entries(features):
        groups = defaultdict(list)
        for feature in features:
            props = feature["properties"]
            if props.get("type") == "Level_Entry":
                groups[props["name"]].append(feature)
        return {
            name: sorted(json.dumps(f, sort_keys=True) for f in values)
            for name, values in groups.items()
        }

    old, new = entries(before), entries(after)
    old_ids = {str(f["properties"]["id"]) for f in before}
    return {
        "before_entry_count": len(old),
        "after_entry_count": len(new),
        "added_entries": sorted(new.keys() - old.keys()),
        "removed_entries": sorted(old.keys() - new.keys()),
        "changed_entries": sorted(
            k for k in old.keys() & new.keys() if old[k] != new[k]
        ),
        "added_marker_types": dict(
            Counter(
                f["properties"].get("type")
                for f in after
                if str(f["properties"]["id"]) not in old_ids
            )
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--out", default="results/upstream/map-update-2026-10-26.json")
    args = parser.parse_args()
    repo = Path("cache/map/upstream")
    old = read_json(repo / "data/markers.json")["features"]
    new = json.loads(
        subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{args.ref}:data/markers.json"]
        )
    )["features"]
    result = entry_changes(old, new)
    for key, ref in (("pinned_map_commit", "HEAD"), ("checked_map_commit", args.ref)):
        result[key] = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", ref], text=True
        ).strip()
    write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Report exact same-cell entries by physical map; never move source coordinates."""

from collections import defaultdict

from ootss.common import read_json, write_json


def audit(
    source="results/worlds/index.json", out="results/upstream/marker-overlaps.json"
):
    data = read_json(source)
    overlaps = []
    for world in data.get("maps", [data]):
        cells = defaultdict(list)
        for level in world["levels"]:
            for entry in level["entries"]:
                cells[tuple(entry["coordinates"][:2])].append(
                    {
                        "level_id": level["level_id"],
                        "marker_id": entry["marker_id"],
                        "coordinates": entry["coordinates"],
                        "visits": [
                            {k: visit[k] for k in ("part", "display_part", "ordinal")}
                            for visit in level["visits"]
                        ],
                    }
                )
        for xy, entries in cells.items():
            if len({e["level_id"] for e in entries}) > 1:
                overlaps.append(
                    {"map_id": world["map_id"], "coordinates": xy, "entries": entries}
                )
    result = {
        "scope": "Exact XY within each physical map only; nearby entries are not moved.",
        "map_commit": data["map_commit"],
        "groups": overlaps,
    }
    write_json(out, result)
    return result


if __name__ == "__main__":
    print(f"Same-cell groups: {len(audit()['groups'])}")

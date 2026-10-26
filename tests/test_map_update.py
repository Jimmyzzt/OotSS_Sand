import pytest

from ootss.maps import tile_asset_base
from scripts.check_map_update import entry_changes


def marker(name, ident, point, kind="Level_Entry"):
    return {
        "properties": {"id": ident, "name": name, "type": kind},
        "geometry": {"coordinates": point},
    }


def test_map_diff_ignores_order_but_preserves_every_entrance_and_other_marker_types():
    a = marker("same", 1, [1, 2, 15])
    b = marker("same", 2, [2, 2, 15])
    result = entry_changes([a, b], [b, marker("ice", 3, [3, 2, 15], "Freezer"), a])
    assert result["before_entry_count"] == result["after_entry_count"] == 1
    assert result["changed_entries"] == []
    assert result["added_entries"] == []
    assert result["added_marker_types"] == {"Freezer": 1}


def test_map_diff_detects_coordinate_changes_removals_and_additions():
    old = [marker("moved", 1, [1, 2, 15]), marker("gone", 2, [0, 0, 15])]
    new = [marker("moved", 1, [2, 2, 15]), marker("added", 3, [0, 0, 15])]
    result = entry_changes(old, new)
    assert result["changed_entries"] == ["moved"]
    assert result["removed_entries"] == ["gone"]
    assert result["added_entries"] == ["added"]


def test_tile_sources_are_pinned_to_a_full_commit_only():
    sha = "a" * 40
    assert (
        tile_asset_base(sha)
        == f"https://raw.githubusercontent.com/joric/ootss_tileset/{sha}"
    )
    assert tile_asset_base().endswith("joric.github.io/ootss_tileset")
    for invalid in ("main", "../main", "a" * 39, 123):
        with pytest.raises(ValueError):
            tile_asset_base(invalid)

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ootss.common import read_json, write_json
from ootss.exporting import export, validate, video_url
from ootss.maps import layer
from ootss.matching import Matcher, features
from ootss.video import black_score, frame, merge_black, scan


def test_center_icon_transition_and_noise():
    im = np.zeros((180, 320, 3), dtype=np.uint8)
    im[75:105, 145:175] = 240
    assert black_score(im) == 1
    im[:] = 90
    assert black_score(im) == 0
    samples = [(i / 8, 1 if i in (1, 4, 5, 6) else 0) for i in range(10)]
    assert merge_black(samples, 8) == [
        {"start": 0.5, "end": 0.875, "black_ratio": 1, "kind": "possible_transition"}
    ]
    assert merge_black([(1, 1), (1.125, 1)], 8)[0]["end"] == 1.25


def test_exact_upstream_layer_boundaries():
    assert layer(0) == "overworld"
    assert layer(10) == "sky"
    assert layer(-4) == "underworld"
    assert layer(100) == "unknown"


def test_hash_shared_pipeline_and_black_rejection_inputs():
    rng = np.random.default_rng(12)
    im = Image.fromarray(rng.integers(0, 255, (180, 320, 3), dtype=np.uint8))
    h, hist = features(im)
    assert h == features(im.copy())[0]
    assert np.linalg.norm(hist) == pytest.approx(1)
    assert 0 <= h < 2**64


def fixture_review():
    return {
        "duration": 10,
        "video_bvid": "BVtest",
        "part_number": 4,
        "events": [
            {
                "event_id": "1",
                "level_id": "a",
                "puzzle_start_time": 1.5,
                "puzzle_end_time": 3,
                "review_status": "confirmed",
                "evidence": ["frame@2"],
                "outcome": "unknown",
            },
            {
                "event_id": "2",
                "level_id": "a",
                "puzzle_start_time": 5,
                "puzzle_end_time": 8,
                "review_status": "confirmed",
                "evidence": ["frame@6"],
                "outcome": "unknown",
            },
        ],
    }


def test_export_preserves_repeat_visits_and_review(tmp_path):
    review = tmp_path / "review.json"
    catalog = tmp_path / "catalog.json"
    write_json(review, fixture_review())
    write_json(
        catalog,
        {
            "commit": "abc",
            "levels": [
                {
                    "level_id": "a",
                    "area": "test",
                    "map_layer": "overworld",
                    "entries": [{"marker_id": 1, "coordinates": [1, 2, 0]}],
                    "map_url": "https://example.test/#a",
                }
            ],
        },
    )
    before = review.read_bytes()
    r = export(review, tmp_path / "out", catalog)
    assert len(r["events"]) == 2
    assert review.read_bytes() == before
    assert r["events"][0]["video_url"].endswith("p=4&t=1")
    assert "&amp;t=1" in (tmp_path / "out/map.svg").read_text()
    for ext in ("json", "csv", "md"):
        assert (tmp_path / f"out/index.{ext}").exists()
    assert (tmp_path / "out/map.png").exists()
    assert video_url("BVx", 4, 61.9).endswith("p=4&t=61")


def test_invalid_identity_and_times_rejected():
    r = fixture_review()
    cat = {"levels": [{"level_id": "a"}]}
    r["events"][0]["puzzle_end_time"] = 20
    with pytest.raises(ValueError, match="time"):
        validate(r, cat)
    r = fixture_review()
    r["events"][0]["level_id"] = "sky_level"
    with pytest.raises(ValueError, match="Overworld"):
        validate(r, cat)
    r = fixture_review()
    r["events"][0]["review_status"] = "unknown"
    with pytest.raises(ValueError, match="level_id=null"):
        validate(r, cat)


def test_unknown_match_and_export(tmp_path):
    rng = np.random.default_rng(8)
    reference = tmp_path / "ref.png"
    Image.fromarray(rng.integers(0, 255, (180, 320, 3), dtype=np.uint8)).save(reference)
    query = tmp_path / "black.png"
    Image.new("RGB", (320, 180)).save(query)
    catalog = tmp_path / "cat.json"
    write_json(
        catalog,
        {
            "commit": "test",
            "levels": [{"level_id": "a", "reference": str(reference), "area": "test"}],
        },
    )
    assert Matcher(catalog).search(query)["status"] == "unknown"
    r = fixture_review()
    r["events"] = [
        {
            "event_id": "unknown",
            "level_id": None,
            "puzzle_start_time": 1,
            "puzzle_end_time": 3,
            "review_status": "unknown",
        }
    ]
    review = tmp_path / "review.json"
    write_json(review, r)
    result = export(review, tmp_path / "out", catalog)
    assert result["events"][0]["level_id"] is None
    assert "](None)" not in (tmp_path / "out/index.md").read_text(encoding="utf-8")
    r = fixture_review()
    r["events"] = [r["events"][0]]
    r["events"][0]["review_status"] = "candidate"
    write_json(review, r)
    result = export(review, tmp_path / "out", catalog)
    assert result["events"][0]["map_entries"] == []
    assert result["events"][0]["map_url"] is None


def test_ffmpeg_scan_cache_and_recovery(tmp_path):
    video = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:r=24:d=1",
            "-vf",
            "drawbox=x=150:y=80:w=20:h=20:color=white:t=fill",
            "-y",
            str(video),
        ],
        check=True,
    )
    out = tmp_path / "run"
    r = scan(video, out, interval=0.5)
    assert len(r["transitions"]) == 1
    assert r["transitions"][0]["start"] == 0
    target = out / "scan.json"
    mtime = target.stat().st_mtime_ns
    scan(video, out, interval=0.5)
    assert target.stat().st_mtime_ns == mtime
    scan(video, out, interval=0.25)
    assert len(read_json(target)["samples"]) == 4
    assert json.loads(target.read_text())["cache_key"]["interval"] == 0.25
    sample = Path(read_json(target)["samples"][0]["image"])
    sample.unlink()
    scan(video, out, interval=0.25)
    assert sample.exists()
    other = tmp_path / "other.mp4"
    other.write_bytes(video.read_bytes())
    with pytest.raises(ValueError, match="another video"):
        scan(other, out)


def test_frame_cache_is_bound_to_video_and_time(tmp_path):
    def make_video(name, color):
        p = tmp_path / name
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=160x90:r=24:d=1",
                "-y",
                str(p),
            ],
            check=True,
        )
        return p

    red, blue = make_video("red.mp4", "red"), make_video("blue.mp4", "blue")
    target = tmp_path / "same-output.jpg"
    frame(red, 0.1, target)
    with Image.open(target) as im:
        assert im.getpixel((10, 10))[0] > 200
    mtime = target.stat().st_mtime_ns
    frame(red, 0.1, target)
    assert target.stat().st_mtime_ns == mtime
    frame(blue, 0.1, target)
    with Image.open(target) as im:
        assert im.getpixel((10, 10))[2] > 200
    frame(blue, 0.5, target)
    assert read_json(target.with_suffix(".jpg.source.json"))["time"] == 0.5

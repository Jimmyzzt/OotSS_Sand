"""Download an explicitly selected Bilibili anthology and keep a resumable ledger."""

import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .common import read_json, write_json
from .video import probe

BVID = "BV13FH96bE4m"


def safe_title(title):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")[:110]


def discover(out="results/series/manifest.json"):
    import json

    request = urllib.request.Request(
        f"https://api.bilibili.com/x/web-interface/view?bvid={BVID}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"},
    )
    response = json.loads(urllib.request.urlopen(request, timeout=30).read())
    if response.get("code") != 0:
        raise ValueError(f"Bilibili metadata failure: {response.get('code')}")
    pages = response["data"]["pages"]
    second = next(p["page"] for p in pages if "二阶段开始" in p["part"])
    third = next(p["page"] for p in pages if "三阶段开始" in p["part"])
    previous = (
        {r["part_number"]: r for r in read_json(out)["parts"]}
        if Path(out).exists()
        else {}
    )
    rows = []
    for page in pages:
        part = page["page"]
        stage = 1 if part < second else 2 if part < third else 3
        file = (
            Path("inputs/series")
            / f"stage{stage}"
            / f"P{part:02d}__{safe_title(page['part'])}.mp4"
        )
        rows.append(
            {
                **previous.get(part, {}),
                "part_number": part,
                "title": page["part"],
                "cid": page["cid"],
                "duration": page["duration"],
                "stage": stage,
                "url": f"https://www.bilibili.com/video/{BVID}/?p={part}",
                "file": str(file.resolve()),
                "download_status": previous.get(part, {}).get(
                    "download_status", "pending"
                ),
            }
        )
    result = {
        "bvid": BVID,
        "title": response["data"]["title"],
        "stage_boundaries": {
            "stage1": [1, second - 1],
            "stage2": [second, third - 1],
            "stage3": [third, len(pages)],
        },
        "scope_evidence": "Author's part titles explicitly mark stage starts; stage 1 membership is later derived from observed reviewed visits, not every Overworld marker.",
        "parts": rows,
    }
    write_json(out, result)
    return result


def download_series(
    manifest="results/series/manifest.json", workers=2, only_stage=None
):
    data = read_json(manifest) if Path(manifest).exists() else discover(manifest)
    logs = Path("cache/download_logs")
    logs.mkdir(parents=True, exist_ok=True)
    rows = [r for r in data["parts"] if only_stage is None or r["stage"] == only_stage]
    # Reuse the user-supplied P4 via a hard link. Preserve its original path/caches.
    p4 = next((r for r in rows if r["part_number"] == 4), None)
    originals = list(Path("inputs").glob("p4*.mp4"))
    if p4 and originals and not Path(p4["file"]).exists():
        Path(p4["file"]).parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(originals[0], p4["file"])
            method = "hard link"
        except OSError:
            shutil.copy2(originals[0], p4["file"])
            method = "copy (hard links unavailable)"
        p4["source_note"] = f"Reused user-provided P4 via {method}; original preserved"

    def work(row):
        file = Path(row["file"])
        file.parent.mkdir(parents=True, exist_ok=True)
        log = logs / f"P{row['part_number']:02d}.log"
        if not file.exists():
            args = [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "yt_dlp",
                "--no-playlist",
                "--no-progress",
                "--continue",
                "--retries",
                "3",
                "--fragment-retries",
                "3",
                "--socket-timeout",
                "25",
                "--sleep-requests",
                "0.3",
                "--write-info-json",
                "--merge-output-format",
                "mp4",
                "-f",
                "bv[height<=480][vcodec^=avc1]+ba/bv[height<=480]+ba/b[height<=480]",
                "-o",
                str(file.with_suffix(".%(ext)s")),
                row["url"],
            ]
            with log.open("w", encoding="utf-8") as output:
                done = subprocess.run(
                    args,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    encoding="utf-8",
                    check=False,
                )
            if done.returncode:
                return row, {
                    "download_status": "failed",
                    "log": str(log.resolve()),
                    "error": f"yt-dlp exit {done.returncode}",
                }
        try:
            info = probe(file)
            duration = float(info["format"]["duration"])
            if abs(duration - row["duration"]) > 3:
                raise ValueError("Duration differs from part metadata")
            video = next(s for s in info["streams"] if s["codec_type"] == "video")
            return row, {
                "download_status": "complete",
                "bytes": file.stat().st_size,
                "actual_duration": duration,
                "width": video["width"],
                "height": video["height"],
                "log": str(log.resolve()),
            }
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            return row, {"download_status": "invalid", "error": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, r) for r in rows]
        for future in concurrent.futures.as_completed(futures):
            row, update = future.result()
            row.update(update)
            write_json(manifest, data)
            print(f"P{row['part_number']:02d}: {row['download_status']}", flush=True)
    return data


if __name__ == "__main__":
    discover()
    download_series()

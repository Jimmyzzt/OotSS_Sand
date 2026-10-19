"""Download an explicitly selected Bilibili anthology and keep a resumable ledger."""

import concurrent.futures
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from yt_dlp.utils import DownloadError

from .common import read_json, write_json
from .video import probe

BVID = "BV13FH96bE4m"


def playurl_fallback(row):
    """Use public, successful playurl data when the site extractor finds no formats.

    yt-dlp still downloads both tracks. Prefer the API's ordinary CDN backup
    over mcdn, which repeatedly stalled on a few parts in this anthology.
    """
    from yt_dlp import YoutubeDL

    request = urllib.request.Request(
        f"https://api.bilibili.com/x/player/playurl?bvid={BVID}&cid={row['cid']}&qn=32&fnval=4048&fourk=1",
        headers={"User-Agent": "Mozilla/5.0", "Referer": row["url"]},
    )
    response = json.loads(urllib.request.urlopen(request, timeout=25).read())
    if response.get("code") != 0 or not response.get("data", {}).get("dash"):
        raise ValueError("Public playurl did not authorize playable DASH streams")
    dash = response["data"]["dash"]
    videos = [v for v in dash["video"] if v.get("height", 9999) <= 480]
    if not videos or not dash.get("audio"):
        raise ValueError("Public playurl has no requested video/audio")
    video = max(
        videos,
        key=lambda v: (
            v.get("height", 0),
            str(v.get("codecs", "")).startswith("avc1"),
            v.get("bandwidth", 0),
        ),
    )
    audio = min(dash["audio"], key=lambda a: a.get("bandwidth", 10**9))
    file = Path(row["file"])
    temp = Path("cache/download_recovery") / f"P{row['part_number']:02d}"
    temp.mkdir(parents=True, exist_ok=True)
    for kind, item, ext in [("video", video, "mp4"), ("audio", audio, "m4a")]:
        urls = [
            item.get("baseUrl") or item.get("base_url"),
            *(item.get("backupUrl") or item.get("backup_url") or []),
        ]
        urls = [u for u in urls if u]
        url = next((u for u in urls if "mcdn" not in urlsplit(u).hostname), urls[0])
        target = temp / f"{kind}.{ext}"
        if target.exists():
            continue
        with YoutubeDL(
            {
                "outtmpl": str(target),
                "noprogress": True,
                "quiet": True,
                "socket_timeout": 20,
                "retries": 2,
                "http_headers": {"Referer": row["url"], "User-Agent": "Mozilla/5.0"},
            }
        ) as ydl:
            ydl.process_info(
                {
                    "id": f"{BVID}_p{row['part_number']}_{kind}",
                    "title": row["title"],
                    "url": url,
                    "ext": ext,
                    "protocol": "https",
                    "format_id": str(item.get("id", kind)),
                    "http_headers": {
                        "Referer": row["url"],
                        "User-Agent": "Mozilla/5.0",
                    },
                }
            )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(temp / "video.mp4"),
            "-i",
            str(temp / "audio.m4a"),
            "-c",
            "copy",
            "-y",
            str(file),
        ],
        check=True,
    )
    return "Public playurl format recovery; both tracks downloaded by yt-dlp; ordinary backup CDN"


def safe_title(title):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")[:110]


def write_inventory(data, out="results/series"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fields = [
        "part_number",
        "stage",
        "title",
        "duration",
        "download_status",
        "width",
        "height",
        "bytes",
        "cid",
        "url",
        "file",
    ]
    with (out / "inventory.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data["parts"])
    complete = [p for p in data["parts"] if p["download_status"] == "complete"]
    lines = [
        "# 视频系列下载清单",
        "",
        (
            f"{len(complete)}/{len(data['parts'])} 个分 P 下载完成；"
            f"共 {sum(p['duration'] for p in data['parts']) / 3600:.2f} 小时，"
            f"已完成文件 {sum(p.get('bytes', 0) for p in complete) / 1024**3:.2f} GiB。"
        ),
        "",
        "阶段按作者分 P 标题界定：P1–24 一阶段，P25–44 二阶段，P45–68 三阶段。",
        "保留音频，最高480p；P4复用用户原视频。完成状态已用ffprobe核验文件时长（与分P元数据相差不超过3秒）。",
        "",
        "| P | 阶段 | 标题 | 时长 | 状态 | 文件名 |",
        "|---|---|---|---|---|---|",
    ]
    for p in data["parts"]:
        title = p["title"].replace("|", "\\|")
        lines.append(
            f"| [{p['part_number']:02d}]({p['url']}) | {p['stage']} | {title} | "
            f"{p['duration'] // 60:02d}:{p['duration'] % 60:02d} | {p['download_status']} | "
            f"{Path(p['file']).name.replace('|', '_')} |"
        )
    (out / "inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def discover(out="results/series/manifest.json"):
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
        old = previous.get(part, {})
        # A completed recovery may have a different suffix. Keep its provenance
        # and frame caches stable when rediscovering the same immutable CID.
        if old.get("cid") == page["cid"] and Path(old.get("file", "")).is_file():
            file = Path(old["file"])
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
                )
                if file.is_file()
                else "pending",
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
                "bv[height<=480][vcodec^=avc1]+ba[abr<=75]/bv[height<=480]+ba[abr<=75]/b[height<=480]",
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
                try:
                    row["recovery_note"] = playurl_fallback(row)
                except (
                    OSError,
                    ValueError,
                    subprocess.CalledProcessError,
                    DownloadError,
                ) as exc:
                    return row, {
                        "download_status": "failed",
                        "log": str(log.resolve()),
                        "error": f"yt-dlp exit {done.returncode}; public playurl fallback: {type(exc).__name__}",
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
            if update["download_status"] == "complete":
                row.pop("error", None)
            write_json(manifest, data)
            print(f"P{row['part_number']:02d}: {row['download_status']}", flush=True)
    write_inventory(data, Path(manifest).parent)
    return data


if __name__ == "__main__":
    discover()
    download_series()

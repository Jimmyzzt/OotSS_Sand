import hashlib
import json
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .common import read_json, stamp, write_json


def probe(video):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(video),
            ],
            encoding="utf-8",
        )
    )


def fingerprint(video):
    p = Path(video).resolve()
    return hashlib.sha256(
        f"{p}|{p.stat().st_size}|{p.stat().st_mtime_ns}".encode()
    ).hexdigest()


def frame(video, time, destination, width=852):
    destination = Path(destination)
    source = destination.with_suffix(destination.suffix + ".source.json")
    key = {"video": fingerprint(video), "time": max(0, float(time)), "width": width}
    if not destination.exists() or not source.exists() or read_json(source) != key:
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                str(max(0, time)),
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-vf",
                f"scale={width}:-2",
                "-update",
                "1",
                "-y",
                str(destination),
            ],
            check=True,
        )
        write_json(source, key)
    return destination


def contact_sheet(items, out, columns=4, cell_width=320):
    """Items are (label, path). Labels are ASCII to work without font installs."""
    height = round(cell_width * 9 / 16) + 30
    sheet = Image.new(
        "RGB",
        (columns * cell_width, ((len(items) + columns - 1) // columns) * height),
        "#17212b",
    )
    draw = ImageDraw.Draw(sheet)
    for i, (label, path) in enumerate(items):
        x, y = i % columns * cell_width, i // columns * height
        with Image.open(path) as im:
            im.thumbnail((cell_width, height - 30))
            sheet.paste(im.convert("RGB"), (x, y + 26))
        draw.text((x + 4, y + 5), label, fill="white", font_size=15)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def black_score(rgb, threshold=24, center_mask=0.24):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    mask = np.ones_like(gray, dtype=bool)
    cx, cy = int(w * center_mask / 2), int(h * center_mask / 2)
    mask[h // 2 - cy : h // 2 + cy, w // 2 - cx : w // 2 + cx] = False
    return float((gray[mask] < threshold).mean())


def merge_black(samples, fps, minimum=0.25):
    events, active = [], []
    for t, score in [*samples, (float("inf"), 0)]:
        if score >= 0.94:
            active.append((t, score))
        elif active:
            start, end = active[0][0], active[-1][0] + 1 / fps
            if end - start >= minimum:
                events.append(
                    {
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "black_ratio": round(max(s for _, s in active), 4),
                        "kind": "possible_transition",
                    }
                )
            active = []
    return events


def scan(video, out, interval=15.0, fps=8.0, start=0.0, end=None, black_min=0.25):
    """One low-resolution sequential decode for samples and black events."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    key = {
        "video": fingerprint(video),
        "interval": interval,
        "fps": fps,
        "start": start,
        "end": end,
        "black_min": black_min,
        "version": 2,
    }
    target = out / "scan.json"
    if target.exists():
        previous = read_json(target)
        if previous.get("cache_key", {}).get("video") != key["video"]:
            raise ValueError(
                "This output directory belongs to another video version; use a new --out directory"
            )
        if previous.get("cache_key") == key and all(
            Path(s["image"]).exists() for s in previous["samples"]
        ):
            return previous
    begun = time.monotonic()
    meta = probe(video)
    duration = float(meta["format"]["duration"])
    stop = min(end if end is not None else duration, duration)
    if not 0 <= start < stop or fps <= 0 or interval < 1 / fps or black_min <= 0:
        raise ValueError("Invalid range, sampling interval, or fps")
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-ss",
        str(start),
        "-i",
        str(video),
        "-t",
        str(stop - start),
        "-an",
        "-vf",
        f"fps={fps},scale=320:180",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "pipe:1",
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    black, sampled = [], []
    next_sample, i = start, 0
    while True:
        data = process.stdout.read(320 * 180 * 3)
        if not data:
            break
        if len(data) != 320 * 180 * 3:
            raise RuntimeError("Truncated FFmpeg frame")
        rgb = np.frombuffer(data, np.uint8).reshape(180, 320, 3)
        t = start + i / fps
        black.append((t, black_score(rgb)))
        if t + 1e-6 >= next_sample:
            path = out / "samples" / f"{t:09.3f}.jpg"
            path.parent.mkdir(exist_ok=True)
            Image.fromarray(rgb).save(path, quality=85)
            sampled.append({"time": round(t, 3), "image": str(path.resolve())})
            next_sample += interval
        i += 1
    error = process.stderr.read().decode(errors="replace")
    if process.wait():
        raise RuntimeError(error)
    result = {
        "cache_key": key,
        "video": str(Path(video).resolve()),
        "metadata": meta,
        "duration": duration,
        "range": [start, stop],
        "samples": sampled,
        "transitions": merge_black(black, fps, black_min),
        "timing_uncertainty_seconds": 1 / fps,
        "scan_seconds": round(time.monotonic() - begun, 2),
        "note": "Black events are evidence only, not confirmed level entries. fps sampling is approximate; use frame PTS for precision.",
    }
    write_json(target, result)
    np.savez_compressed(out / "black_scores.npz", samples=np.asarray(black))
    for offset in range(0, len(sampled), 32):
        contact_sheet(
            [(stamp(x["time"]), x["image"]) for x in sampled[offset : offset + 32]],
            out / f"sheet_{offset // 32:02d}.jpg",
        )
    return result

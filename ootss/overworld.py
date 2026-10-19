"""A bounded geometric cross-check; decisions still require viewing the overlay."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .common import read_json, write_json
from .video import frame


def check(run, time, level_id, terrain, bounds, out):
    run, out = Path(run), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scan = read_json(run / "scan.json")
    query = frame(scan["video"], time, out / f"approach_{time:.3f}.jpg")
    sift = cv2.SIFT_create(nfeatures=5000)
    with Image.open(query) as im:
        q = np.asarray(im.convert("L"))
    with Image.open(terrain) as im:
        target = np.asarray(im.convert("L"))
    qk, qd = sift.detectAndCompute(q, None)
    tk, td = sift.detectAndCompute(target, None)
    result = {
        "time": time,
        "level_id": level_id,
        "terrain": str(Path(terrain).resolve()),
        "bounds": bounds,
        "approach_image": str(query.resolve()),
        "status": "unverified",
        "inliers": 0,
        "note": "Geometric alignment alone is not entrance verification. Inspect projected marker against player/entrance.",
    }
    if qd is None or td is None or len(td) < 2:
        write_json(out / "check.json", result)
        return result
    good = [
        a
        for a, b in cv2.BFMatcher().knnMatch(qd, td, k=2)
        if a.distance < 0.72 * b.distance
    ]
    if len(good) >= 8:
        src = np.float32([qk[m.queryIdx].pt for m in good])
        dst = np.float32([tk[m.trainIdx].pt for m in good])
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3)
        if H is not None and mask is not None:
            count = int(mask.sum())
            points = src[mask.ravel().astype(bool)]
            coverage = cv2.contourArea(cv2.convexHull(points)) / (
                q.shape[0] * q.shape[1]
            )
            result.update(
                inliers=count, query_coverage=round(coverage, 4), homography=H.tolist()
            )
            if count >= 12 and coverage >= 0.04 and abs(np.linalg.det(H)) > 1e-8:
                cat = read_json("cache/map/catalog.json")
                row = next(r for r in cat["levels"] if r["level_id"] == level_id)
                if len(row["entries"]) != 1:
                    result.update(
                        status="ambiguous_map_entries",
                        note="Choose an entry explicitly before projecting this level",
                    )
                    write_json(out / "check.json", result)
                    return result
                left, _bottom, right, top = bounds
                # Account for floor/ceil pixel boundaries in the crop.
                scale = target.shape[1] / (right - left)
                x, y, _ = row["entries"][0]["coordinates"]
                local = np.float32([[[(x - left) * scale, (top - y) * scale]]])
                px, py = cv2.perspectiveTransform(local, np.linalg.inv(H))[0, 0]
                if 0 <= px < q.shape[1] and 0 <= py < q.shape[0]:
                    result.update(
                        status="geometry_candidate",
                        projected_entrance=[float(px), float(py)],
                    )
                    im = Image.open(query).convert("RGB")
                    draw = ImageDraw.Draw(im)
                    draw.ellipse(
                        (px - 10, py - 10, px + 10, py + 10), outline="#ff3344", width=3
                    )
                    draw.text(
                        (12, 12),
                        f"{level_id} | {count} terrain inliers | check red circle",
                        fill="white",
                        stroke_fill="black",
                        stroke_width=1,
                        font_size=17,
                    )
                    im.save(out / "overlay.jpg")
                    result["overlay"] = str((out / "overlay.jpg").resolve())
    write_json(out / "check.json", result)
    return result

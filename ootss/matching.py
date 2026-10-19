import hashlib
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.fft import dctn

from .common import read_json, write_json


def features(image):
    """Rebuild both reference and query features; do not mix Canvas hashes."""
    rgb = np.asarray(
        image.convert("RGB").resize((32, 32), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    gray = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    low = dctn(gray, type=2, norm="ortho")[:8, :8].reshape(-1)
    median = np.median(low[1:])
    bits = low > median
    phash = sum(int(b) << (63 - i) for i, b in enumerate(bits))
    rgb = np.asarray(image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.int32)
    bins = (
        np.minimum(hsv[:, :, 0] * 16 // 180, 15) * 4
        + np.minimum(hsv[:, :, 1] * 4 // 256, 3)
    ) * 4 + np.minimum(hsv[:, :, 2] * 4 // 256, 3)
    hist = np.bincount(bins.ravel(), minlength=256).astype(np.float32)
    hist /= max(np.linalg.norm(hist), 1)
    return phash, hist


class Matcher:
    def __init__(self, catalog="cache/map/catalog.json"):
        self.catalog_path = Path(catalog)
        self.catalog = read_json(catalog)
        self.rows = [
            r
            for r in self.catalog["levels"]
            if r["reference"] and Path(r["reference"]).exists()
        ]
        if not self.rows:
            raise ValueError(
                "No local Overworld references; run import-map and inspect download errors"
            )
        self.sift = cv2.SIFT_create(nfeatures=700)
        self.local_features = {}
        key = hashlib.sha256(
            (
                self.catalog["commit"]
                + "pillow-bilinear-v1"
                + "|".join(r["level_id"] for r in self.rows)
            ).encode()
        ).hexdigest()[:16]
        cache = self.catalog_path.parent / f"features_{key}.npz"
        if cache.exists():
            data = np.load(cache)
            self.hashes, self.hists = [int(h) for h in data["hashes"]], data["hists"]
        else:
            desc = [features(Image.open(r["reference"])) for r in self.rows]
            self.hashes, self.hists = (
                [x[0] for x in desc],
                np.asarray([x[1] for x in desc]),
            )
            np.savez_compressed(
                cache, hashes=np.asarray(self.hashes, dtype=np.uint64), hists=self.hists
            )

    def keypoints(self, path):
        path = str(path)
        if path not in self.local_features:
            with Image.open(path) as im:
                im = im.convert("L")
                im.thumbnail((640, 360))
                self.local_features[path] = self.sift.detectAndCompute(
                    np.asarray(im), None
                )
        return self.local_features[path]

    def geometric(self, query, reference):
        qk, qd = self.keypoints(query)
        rk, rd = self.keypoints(reference)
        if qd is None or rd is None or len(rd) < 2:
            return 0, 0
        pairs = cv2.BFMatcher().knnMatch(qd, rd, k=2)
        good = [a for a, b in pairs if a.distance < 0.72 * b.distance]
        if len(good) < 6:
            return 0, len(good)
        src = np.float32([qk[m.queryIdx].pt for m in good])
        dst = np.float32([rk[m.trainIdx].pt for m in good])
        _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3)
        return int(mask.sum()) if mask is not None else 0, len(good)

    def search(self, path, top=5, refine=12):
        with Image.open(path) as im:
            qh, hist = features(im)
        hp = np.asarray([(qh ^ h).bit_count() for h in self.hashes])
        hd = np.linalg.norm(self.hists - hist, axis=1)
        # Upstream ranks pHash first, HSV for ties. Retain that baseline.
        order = np.lexsort((hd, hp))[: max(top, refine)]
        candidates = []
        for idx in order:
            row = self.rows[idx]
            inliers, good = self.geometric(path, row["reference"]) if refine else (0, 0)
            candidates.append(
                {
                    "level_id": row["level_id"],
                    "area": row["area"],
                    "phash_distance": int(hp[idx]),
                    "hist_distance": round(float(hd[idx]), 4),
                    "sift_inliers": inliers,
                    "sift_good": good,
                }
            )
        if refine:
            candidates.sort(
                key=lambda x: (
                    -x["sift_inliers"],
                    x["phash_distance"],
                    x["hist_distance"],
                )
            )
        best = candidates[0]
        # Experimental reject rule, not calibrated confidence. Never auto-confirm.
        status = (
            "candidate"
            if best["sift_inliers"] >= 10 or best["phash_distance"] <= 12
            else "unknown"
        )
        return {
            "status": status,
            "candidates": candidates[:top],
            "acceptance": "requires_visual_review",
        }


def match_run(run, catalog="cache/map/catalog.json"):
    run = Path(run)
    scan = read_json(run / "scan.json")
    matcher = Matcher(catalog)
    key = {
        "scan": scan["cache_key"],
        "map_commit": matcher.catalog["commit"],
        "version": 1,
    }
    target = run / "matches.json"
    if target.exists() and read_json(target).get("cache_key") == key:
        return read_json(target)
    start = time.monotonic()
    rows = []
    for i, sample in enumerate(scan["samples"]):
        rows.append({**sample, **matcher.search(sample["image"])})
        if i % 20 == 0:
            print(f"Matched {i + 1}/{len(scan['samples'])}", flush=True)
    result = {
        "cache_key": key,
        "seconds": round(time.monotonic() - start, 2),
        "samples": rows,
        "warning": "Candidate ranks and heuristic rejection are not measured confidence or final identities.",
    }
    write_json(target, result)
    return result

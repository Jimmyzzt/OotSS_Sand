import argparse
from pathlib import Path

from .atlas import build_atlas
from .common import read_json, stamp, write_json
from .exporting import export
from .maps import import_map, terrain_crop
from .matching import Matcher, match_run
from .overworld import check
from .series import discover, download_series
from .video import contact_sheet, frame, probe, scan


def main():
    parser = argparse.ArgumentParser(
        description="Agent-assisted OotSS video evidence tools (no server or API)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "import-map", help="Download pinned map metadata and Overworld references"
    )
    p.add_argument("--cache", default="cache/map")
    p.add_argument(
        "--all-worlds",
        action="store_true",
        help="Include Sky and Underworld in catalog_all.json",
    )
    p = sub.add_parser("probe")
    p.add_argument("--video", required=True)
    p = sub.add_parser(
        "scan", help="Cache low-resolution samples and possible black transitions"
    )
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--interval", type=float, default=15)
    p.add_argument("--fps", type=float, default=8)
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--end", type=float)
    p.add_argument("--black-min", type=float, default=0.25)
    p = sub.add_parser(
        "match", help="Generate candidate JSON; never touches reviewed notes"
    )
    p.add_argument("--run", required=True)
    p.add_argument("--catalog", default="cache/map/catalog.json")
    p = sub.add_parser("series", help="Discover or resume the full Bilibili anthology")
    p.add_argument("--discover-only", action="store_true")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--stage", type=int, choices=[1, 2, 3])
    p = sub.add_parser("atlas", help="Build a reviewed real-map atlas")
    p.add_argument("--out", default=None)
    p.add_argument(
        "--all-worlds", action="store_true", help="Group all stages by physical map"
    )
    p = sub.add_parser(
        "packet", help="Bounded frame and candidate contact sheets for agent judgment"
    )
    p.add_argument("--run", required=True)
    p.add_argument("--start", required=True, type=float)
    p.add_argument("--end", required=True, type=float)
    p.add_argument("--step", type=float, default=2)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--candidates", nargs="*", default=[])
    p.add_argument("--catalog", default="cache/map/catalog.json")
    p = sub.add_parser(
        "search", help="Search a single screenshot, optional regional shortlist"
    )
    p.add_argument("image")
    p.add_argument("--catalog", default="cache/map/catalog.json")
    p = sub.add_parser(
        "terrain", help="Download a local Overworld map crop (game coordinates)"
    )
    p.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        required=True,
        metavar=("LEFT", "BOTTOM", "RIGHT", "TOP"),
    )
    p.add_argument("--out", required=True)
    p.add_argument("--zoom", type=int, default=4)
    p.add_argument("--raw", action="store_true")
    p = sub.add_parser(
        "world-check",
        help="Project candidate entry onto an approach frame using terrain features",
    )
    p.add_argument("--run", required=True)
    p.add_argument("--time", type=float, required=True)
    p.add_argument("--level", required=True)
    p.add_argument("--terrain", required=True)
    p.add_argument("--bounds", nargs=4, type=float, required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("export")
    p.add_argument("--review", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--catalog", default="cache/map/catalog.json")
    args = parser.parse_args()
    if args.command == "series":
        discover()
        if not args.discover_only:
            download_series(workers=args.workers, only_stage=args.stage)
        return
    if args.command == "atlas":
        build_atlas(
            args.out or ("results/worlds" if args.all_worlds else "results/stage1"),
            parts=range(1, 69) if args.all_worlds else range(1, 25),
            catalog_path="cache/map/catalog_all.json"
            if args.all_worlds
            else "cache/map/catalog.json",
            all_worlds=args.all_worlds,
        )
        return
    if args.command == "import-map":
        r = import_map(
            args.cache,
            layers=("overworld", "sky", "underworld")
            if args.all_worlds
            else ("overworld",),
            catalog_name="catalog_all.json" if args.all_worlds else "catalog.json",
        )
        print(r["audit"])
        print("Download errors:", r["download_errors"])
    elif args.command == "probe":
        print(probe(args.video))
    elif args.command == "scan":
        r = scan(
            args.video,
            args.out,
            args.interval,
            args.fps,
            args.start,
            args.end,
            args.black_min,
        )
        print(
            f"{len(r['samples'])} samples; {len(r['transitions'])} possible transitions"
        )
    elif args.command == "match":
        r = match_run(args.run, args.catalog)
        print(f"{len(r['samples'])} candidate records")
    elif args.command == "search":
        print(Matcher(args.catalog).search(args.image))
    elif args.command == "world-check":
        print(
            check(args.run, args.time, args.level, args.terrain, args.bounds, args.out)
        )
    elif args.command == "terrain":
        left, bottom, right, top = args.bounds
        if (
            not -24.5 <= left < right <= 165.5
            or not -18.5 <= bottom < top <= 170.5
            or not 0 <= args.zoom <= 5
        ):
            parser.error("Use map bounds and zoom 0..5")
        terrain_crop(args.bounds, args.out, zoom=args.zoom, annotate=not args.raw)
    elif args.command == "packet":
        if (
            args.step <= 0
            or args.end <= args.start
            or (args.end - args.start) / args.step > 100
        ):
            parser.error("Use a positive step and a bounded window (max 100 frames)")
        run = Path(args.run)
        data = read_json(run / "scan.json")
        folder = (
            run
            / "packets"
            / f"{args.start:.3f}_{args.end:.3f}_{args.step:.3f}_{args.width}"
        )
        items, records = [], []
        t = max(0, args.start)
        while t <= min(args.end, data["duration"] - 0.1):
            path = frame(
                data["video"], round(t, 3), folder / f"{t:09.3f}.jpg", args.width
            )
            items.append((stamp(t), path))
            records.append({"time": round(t, 3), "image": str(path.resolve())})
            t += args.step
        for o in range(0, len(items), 24):
            contact_sheet(items[o : o + 24], folder / f"sheet_{o // 24:02d}.jpg")
        if args.candidates:
            levels = {r["level_id"]: r for r in read_json(args.catalog)["levels"]}
            contact_sheet(
                [(n, levels[n]["reference"]) for n in args.candidates],
                folder / "candidates.jpg",
                cell_width=426,
            )
        write_json(
            folder / "packet.json",
            {"video": data["video"], "samples": records, "candidates": args.candidates},
        )
        print(folder.resolve())
    elif args.command == "export":
        r = export(args.review, args.out, args.catalog)
        print(f"Exported {len(r['events'])} visits")

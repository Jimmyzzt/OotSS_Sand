"""Package only the public atlas, never raw videos, caches, or local paths."""

import shutil
from pathlib import Path


def package(source="results/stage1", destination="dist"):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in [
        "index.html",
        "index.json",
        "atlas.css",
        "atlas.js",
        "atlas-ui.js",
        "visits.csv",
    ]:
        shutil.copyfile(source / name, destination / name)
    shutil.copytree(source / "assets", destination / "assets", dirs_exist_ok=True)
    (destination / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Public atlas packaged: {destination.resolve()}")


if __name__ == "__main__":
    package()

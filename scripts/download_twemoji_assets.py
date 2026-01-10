from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def download_zip(version: str, destination: Path) -> None:
    url = f"https://github.com/twitter/twemoji/archive/refs/tags/v{version}.zip"
    with urllib.request.urlopen(url) as response, destination.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)


def extract_assets(zip_path: Path, output_dir: Path, version: str, clean: bool) -> int:
    prefix = f"twemoji-{version}/assets/72x72/"
    output_dir.mkdir(parents=True, exist_ok=True)

    if clean:
        for path in output_dir.glob("*.png"):
            path.unlink()

    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if not member.filename.startswith(prefix):
                continue
            if not member.filename.endswith(".png"):
                continue
            filename = Path(member.filename).name
            target = output_dir / filename
            with archive.open(member) as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="14.0.2", help="Twemoji tag version, e.g. 14.0.2")
    parser.add_argument("--output", type=Path, default=Path("app/assets/twemoji_png"))
    parser.add_argument("--clean", action="store_true", help="Remove existing PNGs before extracting")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "twemoji.zip"
        print(f"Downloading Twemoji v{args.version}...")
        download_zip(args.version, zip_path)
        print("Extracting assets...")
        count = extract_assets(zip_path, args.output, args.version, args.clean)

    print(f"Extracted {count} PNG files to {args.output}")


if __name__ == "__main__":
    main()

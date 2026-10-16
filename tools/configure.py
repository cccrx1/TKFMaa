"""Prepare the pinned OCR model; network access requires --download."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "tools/ocr_model.json").read_text(encoding="utf-8"))
DEFAULT_MODEL_DIR = ROOT / "assets/resource/model/ocr"
DEFAULT_SOURCE_DIR = ROOT / "assets/MaaCommonAssets" / MANIFEST["path"]


def validate_model_file(path: Path, spec: dict) -> None:
    if not path.is_file() or path.stat().st_size != spec["bytes"]:
        raise ValueError(f"OCR file missing or size mismatch: {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise ValueError(f"OCR SHA256 mismatch: {path}")


def configure_ocr_model(
    model_dir: Path = DEFAULT_MODEL_DIR,
    *,
    download: bool = False,
    check: bool = False,
    source_dir: Path = DEFAULT_SOURCE_DIR,
) -> None:
    model_dir = Path(model_dir)
    missing = []
    for spec in MANIFEST["files"]:
        target = model_dir / spec["name"]
        if target.exists():
            # A mismatch preserves existing files, even with --download.
            validate_model_file(target, spec)
        else:
            missing.append(spec)
    if not missing:
        print(f"OCR model verified: {model_dir}")
        return
    if check:
        raise ValueError(f"OCR files missing: {', '.join(spec['name'] for spec in missing)}")
    if not download:
        for spec in missing:
            try:
                validate_model_file(source_dir / spec["name"], spec)
            except ValueError as exc:
                raise ValueError(
                    "Pinned OCR source unavailable. Run: python tools/configure.py --download"
                ) from exc

    model_dir.parent.mkdir(parents=True, exist_ok=True)
    # Verify every missing file before copying any into the resource directory.
    with tempfile.TemporaryDirectory(prefix="ocr-", dir=model_dir.parent) as staging:
        for spec in missing:
            staged = Path(staging) / spec["name"]
            if download:
                url = (
                    f"https://raw.githubusercontent.com/{MANIFEST['repository']}/"
                    f"{MANIFEST['revision']}/{MANIFEST['path']}/{spec['name']}"
                )
                print(f"Downloading pinned OCR file: {spec['name']}", flush=True)
                with urlopen(url, timeout=60) as response:
                    # Limit received bytes and avoid holding the full model in memory.
                    remaining = spec["bytes"] + 1
                    with staged.open("wb") as target:
                        while remaining:
                            chunk = response.read(min(remaining, 512 * 1024))
                            if not chunk:
                                break
                            target.write(chunk)
                            remaining -= len(chunk)
            else:
                shutil.copyfile(source_dir / spec["name"], staged)
            validate_model_file(staged, spec)
        model_dir.mkdir(parents=True, exist_ok=True)
        for spec in missing:
            # Exclusive creation also protects files added by another process.
            with (Path(staging) / spec["name"]).open("rb") as source:
                with (model_dir / spec["name"]).open("xb") as target:
                    shutil.copyfileobj(source, target)
    print(f"OCR model configured: {model_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--download", action="store_true", help="Download missing files from the pinned revision")
    mode.add_argument("--check", action="store_true", help="Verify without writing or downloading")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()
    try:
        configure_ocr_model(args.model_dir, download=args.download, check=args.check)
    except (OSError, ValueError) as exc:
        print(f"OCR configuration failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

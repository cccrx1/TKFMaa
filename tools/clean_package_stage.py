"""Remove disposable build/cache files only from a fresh packaging tree."""

import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOTS = {"config", "logs", "debug", "cache", "temp", "backups", ".git", ".github"}
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def inspect_stage(stage: Path) -> list[Path]:
    if not stage.is_dir() or stage.is_symlink():
        raise ValueError("Package staging directory is missing or a symlink")
    paths = list(stage.rglob("*"))
    if any(path.is_symlink() and (not path.is_file() or not path.resolve().is_relative_to(stage.resolve())) for path in paths):
        raise ValueError("Package cleanup only permits internal file symlinks")
    if any((stage / name).exists() for name in PRIVATE_ROOTS):
        raise ValueError("Staging tree contains user state or source control data; refuse to clean or publish it")
    return [path for path in paths if path.name in CACHE_DIRS or (
        path.is_file() and (path.suffix.lower() in {".pyc", ".pyo", ".pdb", ".log"}
                           or path.name in {".DS_Store", "Thumbs.db"}))]


def clean(stage: Path, check: bool = False) -> list[str]:
    stage = stage.absolute()
    unwanted = inspect_stage(stage)
    names = sorted(path.relative_to(stage).as_posix() for path in unwanted)
    if check:
        if names:
            raise ValueError("Disposable files remain in package staging: " + ", ".join(names[:10]))
        return []
    resolved = stage.resolve()
    if resolved != ROOT / "install" and not resolved.is_relative_to(ROOT / "build"):
        raise ValueError("Cleanup only supports install/ or a packaging directory under build/")
    if any(parent.is_symlink() for parent in (stage, *stage.parents)):
        raise ValueError("Cleanup refuses a symlink staging ancestor")
    for path in sorted(unwanted, key=lambda item: len(item.parts), reverse=True):
        if not path.resolve().is_relative_to(resolved):
            raise ValueError("Cleanup target escapes the verified staging directory")
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    return names


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=ROOT / "install")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    removed = clean(args.stage, args.check)
    print(f"Package staging {'checked' if args.check else 'cleaned'}; disposable entries: {len(removed)}")

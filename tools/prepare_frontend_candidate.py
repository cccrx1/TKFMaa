"""Prepare pinned frontend candidate source offline, without changing the release baseline."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "tools/frontend_candidate"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(archive: Path, output: Path) -> None:
    manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    patch = BUNDLE / manifest["patch"]
    if digest(archive.read_bytes()) != manifest["source_archive_sha256"]:
        raise ValueError("Frontend source archive differs from the pinned SHA256")
    if digest(patch.read_bytes()) != manifest["patch_sha256"]:
        raise ValueError("Frontend candidate patch differs from its manifest")
    output = output.resolve()
    relative_output = output.relative_to(ROOT)
    if not relative_output.parts or relative_output.parts[0] != "build":
        raise ValueError("Candidate source must be prepared in a new directory under build/")
    if output.exists():
        raise FileExistsError(f"Refuse to overwrite candidate source: {output}")
    prefix = f"MFAAvalonia-{manifest['revision']}/"
    output.mkdir(parents=True)
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            if not entry.filename.startswith(prefix):
                raise ValueError(f"Unexpected frontend archive root: {entry.filename}")
            name = entry.filename[len(prefix):]
            if not name:
                continue
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
                raise ValueError(f"Unsafe source archive path: {name}")
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError(f"Source symlink is not supported: {name}")
            target = output.joinpath(*path.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(entry))

    def check_files(key: str) -> None:
        for name, hashes in manifest["files"].items():
            target = output / name
            expected = hashes[key]
            if expected is None:
                if target.exists():
                    raise ValueError(f"Unexpected existing candidate file: {name}")
            elif not target.is_file() or digest(target.read_text(encoding="utf-8-sig").encode()) != expected:
                raise ValueError(f"Candidate {key} mismatch: {name}")

    check_files("before_sha256")
    command = ["git", "apply", f"--directory={relative_output.as_posix()}"]
    subprocess.run([*command, "--check", str(patch)], cwd=ROOT, check=True)
    subprocess.run([*command, str(patch)], cwd=ROOT, check=True)
    check_files("after_sha256")
    (output / "tkfmaa-candidate-source.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=4) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Prepared frontend candidate: {output}")
    print(f"Patch SHA256: {manifest['patch_sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_zip, args.output)


if __name__ == "__main__":
    main()

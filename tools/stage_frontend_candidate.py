"""Stage a Windows x64 candidate frontend with verifiable, non-release provenance."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent


def stage(published: Path, output: Path, source: Path) -> dict:
    manifest = json.loads((ROOT / "tools/frontend_candidate/manifest.json").read_text(encoding="utf-8"))
    recorded = json.loads((source / "tkfmaa-candidate-source.json").read_text(encoding="utf-8"))
    if recorded != manifest:
        raise ValueError("Candidate source provenance differs from the repository manifest")
    for name, hashes in manifest["files"].items():
        if hashlib.sha256((source / name).read_text(encoding="utf-8-sig").encode()).hexdigest() != hashes["after_sha256"]:
            raise ValueError(f"Candidate source changed: {name}")
    if output.exists():
        raise FileExistsError(f"Refuse to overwrite frontend staging directory: {output}")
    for name in ("MFAAvalonia.exe", "MFAAvalonia.dll", "libs/MFAAvalonia.Core.dll"):
        if not (published / name).is_file():
            raise ValueError(f"Missing published frontend file: {name}")
    shutil.copytree(published, output)
    files = {}
    for path in sorted(output.rglob("*")):
        relative = path.relative_to(output).as_posix()
        if path.is_file() and (
            (len(path.relative_to(output).parts) == 1 and path.suffix in {".exe", ".dll"})
            or relative in {"MFAAvalonia.deps.json", "MFAAvalonia.runtimeconfig.json"}
            or (relative.startswith("libs/") and not relative.startswith("libs/MaaAgentBinary/") and path.suffix == ".dll")
        ):
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    proof = {"schema_version": 1, "platform": "win-x64", "publishable": False, "source": manifest, "files": files}
    (output / "frontend-candidate-provenance.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=4) + "\n", encoding="utf-8", newline="\n"
    )
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    stage(args.published, args.output, args.source)
    print("Candidate frontend staged; not approved for Release")

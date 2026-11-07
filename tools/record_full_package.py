"""Record a complete desktop staging tree after dependencies have been bundled."""

import argparse
from email.parser import BytesParser
import json
from pathlib import Path
import re

from package_resources import ROOT, collect_resources, digest
from release_support import baseline, source_identity, version_key, write_json


def record(stage: Path, version: str, os_name: str, arch: str, commit: str, allow_dirty: bool = False) -> dict:
    version_key(version)
    policy = baseline()
    source = source_identity(ROOT, commit, allow_dirty)
    platform = {"win": "win", "macos": "osx", "linux": "linux"}[os_name] + "-" + {"x86_64": "x64", "aarch64": "arm64"}[arch]
    paths = sorted(stage.rglob("*"))
    if stage.is_symlink() or any(path.is_symlink() and (not path.is_file() or not path.resolve().is_relative_to(stage.resolve())) for path in paths):
        raise ValueError("Only internal file symlinks can be materialized by artifact upload")
    files = {path.relative_to(stage).as_posix(): digest(path.read_bytes()) for path in paths if path.is_file()}
    if "package-provenance.json" in files:
        raise ValueError("Provenance already exists; do not overwrite")
    interface = json.loads((stage / "interface.json").read_text(encoding="utf-8"))
    update_source = interface["github"]
    repository = update_source.removeprefix("https://github.com/")
    if repository not in [policy["source_repository"], *policy["allowed_update_repositories"]]:
        raise ValueError("Unapproved update repository")
    expected = collect_resources(ROOT, version, os_name, repository)
    packaged_resources = {name: value for name, value in files.items() if name == "interface.json" or name.startswith(("resource/", "agent/"))}
    if packaged_resources != {name: digest(data) for name, data in expected.items()}:
        raise ValueError("Full package resources differ from source")
    site = stage / ("python/Lib/site-packages" if os_name == "win" else "python/lib/python3.12/site-packages")
    inventory, raw_versions = {}, {}
    for path in site.glob("*.dist-info/METADATA"):
        metadata = BytesParser().parsebytes(path.read_bytes(), headersonly=True)
        name = re.sub(r"[-_.]+", "-", metadata["Name"]).lower()
        if name in inventory:
            raise ValueError(f"Duplicate installed distribution: {name}")
        raw_versions[name] = metadata["Version"]
        # MaaFw 5.14.3 wheels declare "v5.14.3" in METADATA; preserve the raw
        # spelling while comparing the exact version without its optional v prefix.
        inventory[name] = re.sub(r"^[vV](?=\d)", "", metadata["Version"].strip())
    for name, required in policy["dependencies"].items():
        if inventory.get(name) != required:
            raise ValueError(f"Bundled dependency differs: {name}: {inventory.get(name)!r} != {required!r}")
    executable = "python/python.exe" if os_name == "win" else "python/bin/python3"
    if executable not in files or not any(name.startswith(f"runtimes/{platform}/native/") for name in files):
        raise ValueError("Missing packaged Python or native runtime")
    if not any(Path(name).name.lower() in {"mfaavalonia.exe", "mfaavalonia", "mfaavalonia.dll"} for name in files):
        raise ValueError("Missing frontend")
    frontend_build = None
    proof_path = stage / "frontend-candidate-provenance.json"
    if proof_path.exists():
        frontend_build = json.loads(proof_path.read_text(encoding="utf-8"))
        expected_frontend = json.loads((ROOT / "tools/frontend_candidate/manifest.json").read_text(encoding="utf-8"))
        required_frontend_files = {"MFAAvalonia.exe", "MFAAvalonia.dll", "libs/MFAAvalonia.Core.dll"}
        if (platform != "win-x64" or frontend_build.get("schema_version") != 1
                or frontend_build.get("platform") != platform or frontend_build.get("source") != expected_frontend
                or frontend_build.get("publishable") is not False or not frontend_build.get("files")):
            raise ValueError("Invalid candidate frontend provenance")
        if not required_frontend_files.issubset(frontend_build["files"]):
            raise ValueError("Candidate frontend provenance omits required binaries")
        for name, expected_hash in frontend_build["files"].items():
            if files.get(name) != expected_hash:
                raise ValueError(f"Candidate frontend file changed: {name}")
        # Source still must be clean above. This marks the resulting package as
        # a rehearsal, so the public Release mirror's exact source check rejects it.
        source = {**source, "rehearsal": True}
    value = {"schema_version": 1, "kind": "full", "version": version, "platform": platform,
             "source": source, "baseline": policy, "update_source": update_source,
             "installed_distributions": inventory, "distribution_metadata_versions": raw_versions, "files": files,
             "runtime_evidence": "dependency METADATA and file inventory; framework/frontend versions declared by pinned build workflow"}
    if frontend_build is not None:
        value["frontend_build"] = frontend_build
    write_json(stage / "package-provenance.json", value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=ROOT / "install")
    parser.add_argument("--version", required=True)
    parser.add_argument("--os", choices=("win", "macos", "linux"), required=True)
    parser.add_argument("--arch", choices=("x86_64", "aarch64"), required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    record(args.stage, args.version, args.os, args.arch, args.source_sha, args.allow_dirty)
    print("Full package provenance recorded; target execution not tested")


if __name__ == "__main__":
    main()

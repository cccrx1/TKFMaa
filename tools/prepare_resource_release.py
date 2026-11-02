"""Prepare six verified resource ZIPs for release, without network access or publishing."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from package_resources import ROOT, collect_resources, digest, verify_archive
from release_support import (TARGETS, baseline, check_agent_imports, check_selection, file_entry,
                             read_json, source_identity, version_key, write_json)


def prepare(input_dir: Path, output: Path, version: str, repository: str, commit: str,
            previous_version: str | None, allow_dirty: bool = False) -> dict:
    version_key(version)
    if previous_version and version_key(version) <= version_key(previous_version):
        raise ValueError("Version must increase beyond previous version")
    policy = baseline()
    if repository not in policy["allowed_update_repositories"]:
        raise ValueError("Update repository is not approved in release_baseline.json")
    source = source_identity(ROOT, commit, allow_dirty)
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    if output.resolve().is_relative_to(input_dir.resolve()):
        raise ValueError("Output must be outside input directory")
    manifests = sorted(input_dir.glob("*.zip.manifest.json"))
    if len(manifests) != len(TARGETS):
        raise ValueError("Exactly six resource manifests required")
    assets, expected, package_manifests = [], {}, []
    # Validate everything before creating the destination. Staging also freezes input bytes.
    with tempfile.TemporaryDirectory(prefix="tkfmaa-release-") as folder:
        stage = Path(folder)
        for path in manifests:
            manifest = read_json(path)
            target, name = manifest["platform"], manifest["archive"]
            if target not in TARGETS or target in expected or name != f"TKFMaa-resource-{target}-{version}.zip":
                raise ValueError("Unexpected platform, duplicate target or unsafe archive name")
            if (manifest["version"] != version or manifest["source_commit"] != commit
                    or manifest["worktree_dirty"] != source["worktree_dirty"]
                    or manifest["update_source"] != "https://github.com/" + repository
                    or manifest["requires"] != {"python": policy["python"], "maafw": policy["maafw"]}):
                raise ValueError("Package source, version, baseline or update source differs")
            if (input_dir / name).is_symlink() or path.is_symlink():
                raise ValueError("Symlink input rejected")
            shutil.copyfile(input_dir / name, stage / name)
            shutil.copyfile(path, stage / path.name)
            files = verify_archive(stage / name, manifest)
            os_name = {"win": "win", "osx": "macos", "linux": "linux"}[target.split("-")[0]]
            if files != collect_resources(ROOT, version, os_name, repository):
                raise ValueError("Archive bytes differ from current source")
            check_agent_imports(files, policy)
            subprocess.run([sys.executable, "-B", str(ROOT / "tools/check_resource_package.py"),
                            "--manifest", str(stage / path.name)], check=True)
            assets.append({**file_entry(stage / name), "platform": target})
            expected[target] = name
            package_manifests.append(manifest)
        check_selection([item["name"] for item in assets] + ["checksums.txt", "release-manifest.json"], expected)
        # Refuse source mutation while validators were running.
        if source_identity(ROOT, commit, allow_dirty) != source:
            raise ValueError("Source identity changed during preparation")
        for manifest in package_manifests:
            os_name = {"win": "win", "osx": "macos", "linux": "linux"}[manifest["platform"].split("-")[0]]
            if {name: digest(data) for name, data in collect_resources(ROOT, version, os_name, repository).items()} != manifest["files"]:
                raise ValueError("Source payload changed during preparation")
        result = {"schema_version": 1, "kind": "resource", "version": version,
                  "repository": repository, "source": source, "baseline": policy,
                  "previous_version": previous_version, "publishable": not source["worktree_dirty"] and not allow_dirty,
                  "assets": assets, "packages": package_manifests,
                  "validation": {"schema_resource_agent": True, "target_device_tests": "not_run",
                                 "dynamic_imports_and_api_compatibility": "require_review"}}
        write_json(stage / "release-manifest.json", result)
        (stage / "checksums.txt").write_text("".join(f"{item['sha256']}  {item['name']}\n" for item in sorted(assets, key=lambda item: item["name"])), encoding="utf-8", newline="\n")
        output.mkdir(parents=True, exist_ok=False)
        for name in [*expected.values(), "checksums.txt", "release-manifest.json"]:
            with (output / name).open("xb") as stream:
                stream.write((stage / name).read_bytes())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--previous-version")
    parser.add_argument("--allow-dirty", action="store_true", help="Local rehearsal only; marks output non-publishable")
    args = parser.parse_args()
    result = prepare(args.input, args.output, args.version, args.repository, args.source_sha, args.previous_version, args.allow_dirty)
    print(json.dumps({"prepared": True, "publishable": result["publishable"], "output": str(args.output)}))


if __name__ == "__main__":
    main()

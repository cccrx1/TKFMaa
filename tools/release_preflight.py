"""Read-only full release plan and downloaded artifact verification; never publishes."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from frontend_build import PLATFORMS, ROOT, read_json, release_profile, verify_proof
from clean_package_stage import clean


def checksum(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def preflight(version: str, artifacts: Path | None = None, commit: str | None = None,
              rehearsal: bool = False) -> dict:
    if not re.fullmatch(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version):
        raise ValueError("Release preview requires an explicit canonical version")
    if "-" in version and any(part.isdigit() and len(part) > 1 and part.startswith("0") for part in version.split("-", 1)[1].split(".")):
        raise ValueError("Numeric prerelease identifiers cannot have leading zeros")
    plan = read_json(ROOT / f"tools/releases/{version}.json")
    profile = release_profile()
    policy = read_json(ROOT / "tools/release_baseline.json")
    if (plan.get("schema_version") != 1 or plan.get("version") != version or plan.get("kind") != "full"
            or plan.get("update_repository") != policy["source_repository"]
            or plan.get("frontend_profile") != profile["id"]
            or plan.get("resource_channel_migration") is not False):
        raise ValueError("Release plan differs from the approved full-package preparation")
    notes = ROOT / plan["release_notes"]
    if not notes.resolve().is_relative_to((ROOT / "docs/zh_cn/releases").resolve()):
        raise ValueError("Unexpected release notes path")
    content = notes.read_text(encoding="utf-8")
    if not content.startswith(f"# {version}\n") or re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", content):
        raise ValueError("Release notes are missing or unfinished")
    result = {"version": version, "kind": "full", "update_repository": plan["update_repository"],
              "frontend_profile": profile["id"], "notes_sha256": checksum(notes),
              "publication_performed": False, "artifact_validation": "not_requested"}
    if artifacts is None:
        return result
    if not commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Require the exact artifact source commit")
    targets = {}
    for platform in PLATFORMS:
        os_name, arch = platform.split("-")
        folder = artifacts / f"TKFMaa-{'macos' if os_name == 'osx' else os_name}-{'x86_64' if arch == 'x64' else 'aarch64'}"
        clean(folder, check=True)
        proof = read_json(folder / "package-provenance.json")
        if (proof["source"] != {"commit": commit, "worktree_dirty": False, "rehearsal": rehearsal}
                or proof["kind"] != "full" or proof["version"] != version or proof["platform"] != platform
                or proof["baseline"] != policy or proof["update_source"] != "https://github.com/" + plan["update_repository"]):
            raise ValueError(f"Artifact identity or source mismatch: {platform}")
        actual = {path.relative_to(folder).as_posix(): checksum(path) for path in folder.rglob("*")
                  if path.is_file() and path.relative_to(folder).as_posix() != "package-provenance.json"}
        if actual != proof["files"]:
            raise ValueError(f"Artifact files differ from provenance: {platform}")
        verify_proof(proof["frontend_build"], actual, platform)
        interface = read_json(folder / "interface.json")
        if interface["version"] != version or interface["github"] != proof["update_source"]:
            raise ValueError(f"Artifact Interface differs: {platform}")
        if any(proof["installed_distributions"].get(name) != value for name, value in policy["dependencies"].items()):
            raise ValueError(f"Artifact dependency differs: {platform}")
        targets[platform] = len(actual)
    result.update(artifact_validation="passed", platforms=targets, source_commit=commit, rehearsal=rehearsal)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--expect-rehearsal", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = preflight(args.version, args.artifacts, args.source_sha, args.expect_rehearsal)
    text = json.dumps(result, ensure_ascii=False, indent=4) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    print(text, end="")

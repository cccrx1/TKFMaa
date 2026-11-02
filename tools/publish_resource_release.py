"""Rehearse offline or explicitly publish a verified bundle from a serialized Actions job."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.parse import quote

from package_resources import ROOT, collect_resources, digest, verify_archive
from release_github import GitHub
from release_support import baseline, check_selection, compatibility_fingerprint, file_entry, read_json, source_identity, version_key
from mirror_full_release import verify_full_archive


def validate_bundle(folder: Path) -> tuple[dict, list[dict]]:
    manifest = read_json(folder / "release-manifest.json")
    policy = baseline()
    if (manifest["schema_version"] != 1 or manifest["kind"] not in {"resource", "full"}
            or manifest["baseline"] != policy or manifest["repository"] not in policy["allowed_update_repositories"]):
        raise ValueError("Unapproved release identity or baseline")
    version_key(manifest["version"])
    if manifest["publishable"] != (not manifest["source"]["worktree_dirty"] and not manifest["source"]["rehearsal"]):
        raise ValueError("Inconsistent rehearsal marker")
    expected = {item["platform"]: item["name"] for item in manifest["assets"]}
    names = [*expected.values(), "checksums.txt", "release-manifest.json"]
    if len(manifest["assets"]) != 6 or len(manifest["packages"]) != 6:
        raise ValueError("Exactly six packages required")
    check_selection(names, expected)
    if {path.name for path in folder.iterdir()} != set(names):
        raise ValueError("Unexpected or missing release attachments")
    packages = {item["platform"]: item for item in manifest["packages"]}
    if set(packages) != set(expected):
        raise ValueError("Missing or duplicate package metadata")
    for item in manifest["assets"]:
        name = item["name"]
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Unsafe archive name")
        if manifest["kind"] == "resource" and name != f"TKFMaa-resource-{item['platform']}-{manifest['version']}.zip":
            raise ValueError("Unexpected archive name")
        if file_entry(folder / name) != {key: item[key] for key in ("name", "size", "sha256")}:
            raise ValueError("Local asset modified after preparation")
        package = packages[item["platform"]]
        if manifest["kind"] == "full":
            verified = verify_full_archive(folder / name, manifest["version"], item["platform"], manifest["source"], policy, manifest["repository"])
            if verified != package or manifest["full_source"]["repository"] != policy["source_repository"] or manifest["full_source"]["tag"] != manifest["version"]:
                raise ValueError("Full mirror metadata differs")
            continue
        if (package["archive"] != name or package["version"] != manifest["version"]
                or package["source_commit"] != manifest["source"]["commit"]
                or package["worktree_dirty"] != manifest["source"]["worktree_dirty"]
                or package["update_source"] != "https://github.com/" + manifest["repository"]
                or package["requires"] != {"python": policy["python"], "maafw": policy["maafw"]}):
            raise ValueError("Package identity differs from release manifest")
        verify_archive(folder / name, package)
    checksum = "".join(f"{item['sha256']}  {item['name']}\n" for item in sorted(manifest["assets"], key=lambda item: item["name"]))
    if (folder / "checksums.txt").read_bytes() != checksum.encode():
        raise ValueError("Checksums modified after preparation")
    return manifest, [file_entry(folder / name) for name in names]


def plan(folder: Path, snapshot: dict) -> dict:
    manifest, assets = validate_bundle(folder)
    version = manifest["version"]
    if snapshot.get("repository") != manifest["repository"] or snapshot.get("complete") is not True:
        raise ValueError("Require a complete release snapshot for the intended repository")
    marker = "TKFMaa-manifest-sha256: " + digest((folder / "release-manifest.json").read_bytes())
    matching = []
    for release in snapshot["releases"]:
        tag = release["tag_name"]
        if tag == version:
            matching.append(release)
        elif version_key(tag) >= version_key(version):
            raise ValueError("A same-or-newer version exists; refuse out-of-order publication")
    if len(matching) > 1:
        raise ValueError("Duplicate release version")
    if not matching and any(tag["name"] == version for tag in snapshot.get("tags", [])):
        raise ValueError("Existing tag without a matching draft; refuse reuse")
    pending = list(assets)
    if matching:
        release = matching[0]
        if release.get("draft") is not True:
            raise ValueError("Public versions are immutable")
        if marker not in release.get("body", "").splitlines():
            raise ValueError("Draft belongs to different prepared content")
        if release.get("prerelease") != ("-" in version):
            raise ValueError("Draft release channel differs")
        uploaded = release["assets"]
        expected = {item["name"]: item for item in assets}
        seen = set()
        for item in uploaded:
            name = item["name"]
            if name in seen or name not in expected:
                raise ValueError("Duplicate or unexpected draft attachment")
            seen.add(name)
            wanted = expected[name]
            if item.get("size") != wanted["size"] or item.get("digest") != "sha256:" + wanted["sha256"]:
                raise ValueError("Draft attachment size/digest missing or different")
        pending = [item for item in assets if item["name"] not in seen]
    return {"mode": "offline-dry-run", "network_writes": False, "version": version,
            "repository": manifest["repository"], "candidate_publishable": manifest["publishable"],
            "action": "resume_matching_draft" if matching else "create_draft",
            "body_marker": marker, "prerelease": "-" in version,
            "uploads_needed": pending,
            "before_publication": ["refresh all release pages under repository-wide publication lock",
                                   "verify all eight remote asset sizes and GitHub digests",
                                   "recheck six-target asset selection", "require clean source and device acceptance"],
            "publication_implemented": True}


def publish(folder: Path, repository: str, version: str, commit: str, notes: str, acceptance: dict, client=None) -> dict:
    manifest, assets = validate_bundle(folder)
    if (manifest["repository"] != repository or manifest["version"] != version
            or manifest["source"]["commit"] != commit or not manifest["publishable"]):
        raise ValueError("Explicit publication inputs differ or candidate is rehearsal-only")
    source_identity(ROOT, commit)
    manifest_hash = digest((folder / "release-manifest.json").read_bytes())
    if (acceptance.get("source_commit") != commit or acceptance.get("version") != version
            or acceptance.get("manifest_sha256") != manifest_hash or acceptance.get("windows_x64_passed") is not True
            or not isinstance(acceptance.get("evidence"), str) or not acceptance["evidence"].strip()):
        raise ValueError("Require acceptance tied to exact source, version and prepared manifest")
    if not notes.strip():
        raise ValueError("Release notes are required")
    if (os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_REPOSITORY") != repository
            or os.environ.get("TKFMAA_RELEASE_CONCURRENCY") != "tkfmaa-release-publish"
            or not re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", ""))):
        raise ValueError("Publishing is restricted to the repository-wide serialized Actions workflow")
    if manifest["kind"] == "resource" and os.environ.get("TKFMAA_CHANNEL_BASELINE_SHA256") != compatibility_fingerprint(manifest["baseline"]):
        raise ValueError("Resource baseline differs from the channel's oldest supported clients; migration required")
    client = client or GitHub(repository, os.environ.get("GITHUB_TOKEN"), writable=True)
    if client.repository != repository:
        raise ValueError("Wrong publishing client repository")
    # Freeze reviewed files before the first remote mutation; upload these exact bytes.
    with tempfile.TemporaryDirectory(prefix="tkfmaa-publish-") as temporary:
        stage = Path(temporary)
        for item in assets:
            shutil.copyfile(folder / item["name"], stage / item["name"])
        _, frozen_assets = validate_bundle(stage)
        if assets != frozen_assets or digest((stage / "release-manifest.json").read_bytes()) != manifest_hash:
            raise ValueError("Bundle changed while freezing")
        if manifest["kind"] == "resource":
            for package in manifest["packages"]:
                os_name = {"win": "win", "osx": "macos", "linux": "linux"}[package["platform"].split("-")[0]]
                if verify_archive(stage / package["archive"], package) != collect_resources(ROOT, version, os_name, repository):
                    raise ValueError("Release payload differs from checked out source")
        else:
            verify_mirror_origin(manifest)
        snapshot = client.snapshot()
        proposed = plan(stage, snapshot)
        matches = [release for release in snapshot["releases"] if release["tag_name"] == version]
        if matches:
            release = matches[0]
        else:
            release = client.request("POST", "/releases", {"tag_name": version, "target_commitish": os.environ["GITHUB_SHA"],
                "name": version, "body": notes.strip() + "\n\n" + proposed["body_marker"],
                "draft": True, "prerelease": proposed["prerelease"]})
        release_id = int(release["id"])
        for item in proposed["uploads_needed"]:
            client.request("POST", f"/releases/{release_id}/assets?name=" + quote(item["name"], safe=""), upload=stage / item["name"])
        # GitHub digest availability can lag upload. A bounded wait leaves a resumable draft.
        for attempt in range(6):
            current = client.snapshot()
            candidate = next((item for item in current["releases"] if item["id"] == release_id), None)
            if candidate and all(item.get("digest") for item in candidate["assets"]) and len(candidate["assets"]) == len(assets):
                final_plan = plan(stage, current)
                if final_plan["uploads_needed"]:
                    raise ValueError("Incomplete draft")
                break
            if attempt == 5:
                raise ValueError("Remote digest verification incomplete; draft retained")
            time.sleep(2)
        # Refresh immediately before making the draft public (same repository lock).
        refreshed = client.snapshot()
        if not any(item["id"] == release_id and item["tag_name"] == version for item in refreshed["releases"]):
            raise ValueError("Draft identity changed before publication")
        if plan(stage, refreshed)["uploads_needed"]:
            raise ValueError("Draft changed before publication")
        result = client.request("PATCH", f"/releases/{release_id}", {"draft": False, "make_latest": "false" if "-" in version else "true"})
        if result.get("draft") is not False or result.get("tag_name") != version:
            raise ValueError("Unexpected publish response; inspect remote state before retry")
        return {"published": True, "version": version, "repository": repository, "release_id": release_id}


def verify_mirror_origin(manifest: dict) -> None:
    client = GitHub(manifest["baseline"]["source_repository"])
    release = client.request("GET", "/releases/tags/" + quote(manifest["version"], safe=""))
    if release["draft"] or release["id"] != manifest["full_source"]["release_id"] or client.resolve_tag(manifest["version"]) != manifest["source"]["commit"]:
        raise ValueError("Full mirror origin changed")
    assets = client.pages(f"/releases/{int(release['id'])}/assets")
    check_selection([item["name"] for item in assets], {item["platform"]: item["name"] for item in manifest["assets"]})
    for item in manifest["assets"]:
        remote = next((asset for asset in assets if asset["id"] == item["source_asset_id"]), None)
        if not remote or remote["name"] != item["name"] or remote["size"] != item["size"] or remote.get("digest") != "sha256:" + item["sha256"]:
            raise ValueError("Full mirror origin asset changed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--remote-snapshot", type=Path, help="Offline JSON fixture; not live remote verification")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--publish", action="store_true")
    parser.add_argument("--repository")
    parser.add_argument("--version")
    parser.add_argument("--source-sha")
    parser.add_argument("--notes-file", type=Path)
    parser.add_argument("--acceptance-file", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        if args.remote_snapshot is None:
            parser.error("--dry-run requires --remote-snapshot")
        result = plan(args.prepared, read_json(args.remote_snapshot))
    else:
        if args.remote_snapshot or not all((args.repository, args.version, args.source_sha, args.notes_file, args.acceptance_file)):
            parser.error("--publish requires explicit repository/version/source/notes/acceptance; offline snapshot not allowed")
        result = publish(args.prepared, args.repository, args.version, args.source_sha,
                         args.notes_file.read_text(encoding="utf-8"), read_json(args.acceptance_file))
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    main()

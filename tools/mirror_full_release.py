"""Prepare unchanged full ZIPs from a public, commit-verified source Release."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from urllib.parse import quote
import zipfile

from package_resources import ROOT, collect_resources, digest
from frontend_build import verify_proof
from release_github import GitHub
from release_support import TARGETS, baseline, check_selection, file_entry, source_identity, version_key, write_json


def verify_full_archive(path: Path, version: str, target: str, source: dict, policy: dict, repository: str) -> dict:
    hashes, small = {}, {}
    with zipfile.ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 8 * 1024**3:
            raise ValueError("Full archive exceeds size limit")
        seen = set()
        for item in archive.infolist():
            name = item.filename.rstrip("/") if item.is_dir() else item.filename
            if (not name or "\\" in name or ":" in name or PurePosixPath(name).is_absolute()
                    or any(part in {"", ".", ".."} or part.endswith((".", " ")) for part in name.split("/"))
                    or (item.external_attr >> 16) & 0o170000 == 0o120000 or name.casefold() in seen):
                raise ValueError("Unsafe, duplicate or symlink full archive entry")
            seen.add(name.casefold())
            if item.is_dir():
                continue
            checksum = hashlib.sha256()
            with archive.open(item) as stream:
                while chunk := stream.read(1024 * 1024):
                    checksum.update(chunk)
            hashes[name] = checksum.hexdigest()
            if name in {"interface.json", "package-provenance.json"}:
                if item.file_size > 16 * 1024**2:
                    raise ValueError("Oversized provenance/Interface")
                small[name] = archive.read(item)
    provenance = json.loads(small["package-provenance.json"])
    hashes.pop("package-provenance.json")
    if (provenance["schema_version"] != 1 or provenance["kind"] != "full"
            or provenance["version"] != version or provenance["platform"] != target
            or provenance["source"] != source or provenance["baseline"] != policy
            or provenance["update_source"] != "https://github.com/" + repository
            or provenance["files"] != hashes):
        raise ValueError("Full archive provenance, baseline or content mismatch")
    if "frontend_build" in provenance:
        verify_proof(provenance["frontend_build"], hashes, target)
    for name, required in policy["dependencies"].items():
        if provenance["installed_distributions"].get(name) != required:
            raise ValueError("Full archive dependency baseline differs")
    interface = json.loads(small["interface.json"])
    if interface["version"] != version or interface["github"] != provenance["update_source"]:
        raise ValueError("Full archive Interface identity differs")
    os_name = {"win": "win", "osx": "macos", "linux": "linux"}[target.split("-")[0]]
    expected = collect_resources(ROOT, version, os_name, repository)
    resources = {name: value for name, value in hashes.items() if name == "interface.json" or name.startswith(("resource/", "agent/"))}
    if resources != {name: digest(data) for name, data in expected.items()}:
        raise ValueError("Full archive resources differ from checked out source")
    executable = "python/python.exe" if os_name == "win" else "python/bin/python3"
    if executable not in hashes or not any(name.startswith(f"runtimes/{target}/native/") for name in hashes):
        raise ValueError("Full archive lacks runtime")
    if not any(Path(name).name.lower() in {"mfaavalonia.exe", "mfaavalonia", "mfaavalonia.dll"} for name in hashes):
        raise ValueError("Full archive lacks frontend")
    return provenance


def mirror(output: Path, version: str, repository: str, commit: str, client=None) -> dict:
    version_key(version)
    policy = baseline()
    source = source_identity(ROOT, commit)
    if repository not in policy["allowed_update_repositories"] or output.exists():
        raise ValueError("Unapproved destination or existing output")
    client = client or GitHub(policy["source_repository"])
    if client.repository != policy["source_repository"]:
        raise ValueError("Unapproved source repository")
    release = client.request("GET", "/releases/tags/" + quote(version, safe=""))
    if release["draft"] or release["tag_name"] != version or release["prerelease"] != ("-" in version):
        raise ValueError("Source Release must be public and match version/channel")
    if client.resolve_tag(version) != commit:
        raise ValueError("Source tag commit differs")
    remote = client.pages(f"/releases/{int(release['id'])}/assets")
    names = {target: f"TKFMaa-{ {'win': 'win', 'osx': 'macos', 'linux': 'linux'}[target.split('-')[0]]}-{ {'x64': 'x86_64', 'arm64': 'aarch64'}[target.split('-')[1]]}-{version}.zip" for target in TARGETS}
    check_selection([item["name"] for item in remote], names)
    assets, packages = [], []
    with tempfile.TemporaryDirectory(prefix="tkfmaa-full-mirror-") as folder:
        stage = Path(folder)
        for target, name in names.items():
            item = next(item for item in remote if item["name"] == name)
            client.download(item, stage / name)
            local = file_entry(stage / name)
            if item.get("digest") != "sha256:" + local["sha256"] or item["size"] != local["size"]:
                raise ValueError("Downloaded mirror differs from source asset")
            provenance = verify_full_archive(stage / name, version, target, source, policy, repository)
            packages.append(provenance)
            assets.append({**file_entry(stage / name), "platform": target, "source_asset_id": item["id"]})
        def identities(items):
            return sorted((item["id"], item["name"], item["size"], item.get("digest")) for item in items)
        if client.resolve_tag(version) != commit or identities(client.pages(f"/releases/{int(release['id'])}/assets")) != identities(remote):
            raise ValueError("Source release changed while mirroring")
        source_identity(ROOT, commit)
        manifest = {"schema_version": 1, "kind": "full", "version": version, "repository": repository,
                    "source": source, "baseline": policy, "publishable": True, "assets": assets, "packages": packages,
                    "full_source": {"repository": policy["source_repository"], "release_id": release["id"], "tag": version},
                    "validation": {"target_device_tests": "require_acceptance_record"}}
        write_json(stage / "release-manifest.json", manifest)
        (stage / "checksums.txt").write_text("".join(f"{item['sha256']}  {item['name']}\n" for item in sorted(assets, key=lambda item: item["name"])), encoding="utf-8", newline="\n")
        output.mkdir(parents=True, exist_ok=False)
        for path in stage.iterdir():
            shutil.copyfile(path, output / path.name)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    result = mirror(args.output, args.version, args.repository, args.source_sha)
    print(json.dumps({"prepared": True, "kind": result["kind"], "assets": len(result["assets"])}))


if __name__ == "__main__":
    main()

"""Verify the pinned patched frontend source and assembled binary inventory."""

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools/frontend_candidate/manifest.json"
PROFILE = ROOT / "tools/frontend_release.json"
PLATFORMS = ("win-x64", "win-arm64", "osx-x64", "osx-arm64", "linux-x64", "linux-arm64")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def required_files(platform: str) -> set[str]:
    if platform not in PLATFORMS:
        raise ValueError(f"Unsupported frontend platform: {platform}")
    return {"MFAAvalonia.exe" if platform.startswith("win-") else "MFAAvalonia",
            "MFAAvalonia.dll", "libs/MFAAvalonia.Core.dll",
            "MFAAvalonia.deps.json", "MFAAvalonia.runtimeconfig.json"}


def release_profile() -> dict:
    manifest = read_json(MANIFEST)
    profile = read_json(PROFILE)
    baseline = read_json(ROOT / "tools/release_baseline.json")
    if (profile.get("schema_version") != 1 or profile.get("platforms") != list(PLATFORMS)
            or profile.get("manifest_sha256") != hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
            or any(profile.get(key) != baseline[key] for key in ("python", "maafw", "frontend"))
            or manifest["revision"] != baseline["frontend_revision"]
            or manifest["frontend"] != profile["frontend"] or manifest["maafw"] != profile["maafw"]):
        raise ValueError("Frontend release profile differs from pinned source or runtime baseline")
    return profile


def verify_proof(proof: dict, files: dict[str, str], platform: str, candidate: bool = False) -> None:
    expected = read_json(MANIFEST)
    if (proof.get("schema_version") != 1 or proof.get("platform") != platform
            or proof.get("source") != expected or not isinstance(proof.get("files"), dict)
            or not required_files(platform).issubset(proof["files"])):
        raise ValueError("Invalid frontend provenance or missing required binaries")
    if candidate:
        if platform != "win-x64" or proof.get("publishable") is not False:
            raise ValueError("Invalid candidate frontend provenance")
    elif proof.get("build_profile") != release_profile():
        raise ValueError("Frontend build does not match the release profile")
    for name, checksum in proof["files"].items():
        if files.get(name) != checksum:
            raise ValueError(f"Frontend file changed: {name}")


def stage(published: Path, output: Path, source: Path, platform: str, candidate: bool = False) -> dict:
    manifest = read_json(MANIFEST)
    if read_json(source / "tkfmaa-candidate-source.json") != manifest:
        raise ValueError("Frontend source provenance differs from repository manifest")
    for name, hashes in manifest["files"].items():
        if hashlib.sha256((source / name).read_text(encoding="utf-8-sig").encode()).hexdigest() != hashes["after_sha256"]:
            raise ValueError(f"Frontend source changed: {name}")
    if output.exists():
        raise FileExistsError(f"Refuse to overwrite frontend staging directory: {output}")
    required = required_files(platform)
    if any(not (published / name).is_file() for name in required):
        raise ValueError("Published frontend is missing required binaries")
    runtime = read_json(published / "MFAAvalonia.runtimeconfig.json")["runtimeOptions"]
    if runtime.get("framework", {}).get("name") != "Microsoft.NETCore.App" or runtime["framework"]["version"] != "10.0.0":
        raise ValueError("Frontend no longer matches the existing .NET 10 runtime requirement")
    profile = None if candidate else release_profile()
    shutil.copytree(published, output)
    files = {}
    for path in sorted(output.rglob("*")):
        relative = path.relative_to(output).as_posix()
        if path.is_file() and (
            relative in required
            or (len(path.relative_to(output).parts) == 1 and path.suffix in {".exe", ".dll"})
            or (relative.startswith("libs/") and not relative.startswith("libs/MaaAgentBinary/")
                and path.suffix in {".dll", ".so", ".dylib"})
        ):
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    proof = {"schema_version": 1, "platform": platform, "source": manifest, "files": files}
    if candidate:
        proof["publishable"] = False
    else:
        proof["build_profile"] = profile
    name = "frontend-candidate-provenance.json" if candidate else "frontend-build-provenance.json"
    (output / name).write_text(json.dumps(proof, ensure_ascii=False, indent=4) + "\n", encoding="utf-8", newline="\n")
    return proof

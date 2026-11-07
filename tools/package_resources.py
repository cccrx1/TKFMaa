"""Build resource-only archives from current source without downloading runtimes."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import zipfile

import jsonc


ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = {"win": "win", "macos": "osx", "linux": "linux"}
ARCHES = {"x86_64": "x64", "aarch64": "arm64"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_payload_references(files: dict[str, bytes]) -> None:
    """Check explicit template references in this standalone Interface bundle."""
    for required in ("interface.json", "agent/main.py"):
        if required not in files:
            raise ValueError(f"Required package file missing: {required}")
    if not any(name.startswith("resource/") for name in files):
        raise ValueError("Required package directory missing: resource")

    def visit(value, source: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "template":
                    templates = [child] if isinstance(child, str) else child
                    if not isinstance(templates, list) or not all(isinstance(item, str) for item in templates):
                        raise ValueError(f"Invalid template reference in {source}")
                    for template in templates:
                        path = PurePosixPath(template)
                        if (not template or "\\" in template or ":" in template
                                or path.is_absolute() or ".." in path.parts):
                            raise ValueError(f"Unsafe template reference {template!r} in {source}")
                        name = (PurePosixPath("resource/image") / path).as_posix()
                        directory = name.rstrip("/") + "/"
                        if name not in files and not any(
                            item.startswith(directory) and PurePosixPath(item).suffix.lower()
                            in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} for item in files
                        ):
                            raise ValueError(f"Missing template {template!r} referenced by {source}")
                visit(child, source)
        elif isinstance(value, list):
            for child in value:
                visit(child, source)

    for name, data in files.items():
        if name == "interface.json" or (name.startswith("resource/pipeline/") and name.endswith((".json", ".jsonc"))):
            visit(jsonc.loads(data.decode("utf-8-sig")), name)


def safe_name(name: str) -> None:
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or path.is_absolute()
            or any(part in {"", ".", ".."} for part in name.split("/"))):
        raise ValueError(f"Unsafe package path: {name}")
    if name != "interface.json" and not name.startswith(("resource/", "agent/")):
        raise ValueError(f"Unexpected package root: {name}")
    if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
        raise ValueError(f"Hidden file or cache in package: {name}")
    allowed = {"agent": {".py"}, "pipeline": {".json", ".jsonc"},
               "image": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
               "model": {".onnx", ".txt"}, "announcement": {".md", ".json", ".png"}}
    if name != "interface.json":
        kind = "agent" if path.parts[0] == "agent" else path.parts[1]
        if path.suffix.lower() not in allowed.get(kind, set()):
            raise ValueError(f"Unexpected resource file: {name}")


def collect_resources(root: Path, version: str, os_name: str, update_repository: str | None = None) -> dict[str, bytes]:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?", version):
        raise ValueError("Version must look like v1.2.3 or v1.2.3-beta.1")
    if os_name not in {*PLATFORMS, "android"}:
        raise ValueError("Unsupported target OS")
    interface_path = root / "assets/interface.json"
    if interface_path.is_symlink():
        raise ValueError("Symlink Interface is not accepted")
    with interface_path.open(encoding="utf-8") as stream:
        interface = jsonc.load(stream)
    if interface.get("interface_version") != 2 or interface.get("import"):
        raise ValueError("This packager requires a standalone Project Interface V2")
    if any(resource.get("path") != ["./resource"] for resource in interface.get("resource", [])):
        raise ValueError("Unexpected declared resource path")
    if not interface.get("resource") or not interface.get("agent"):
        raise ValueError("Resource and Agent declarations are required")
    interface["version"] = version
    interface["agent"]["child_exec"] = {
        "win": "./python/python.exe", "macos": "./python/bin/python3",
        "linux": "./python/bin/python3", "android": "python",
    }[os_name]
    interface["agent"]["child_args"] = ["./agent/main.py"]
    if update_repository is not None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", update_repository):
            raise ValueError("Update repository must be owner/repository")
        interface["github"] = "https://github.com/" + update_repository
    files = {"interface.json": (json.dumps(interface, ensure_ascii=False, indent=4) + "\n").encode("utf-8")}
    for source, prefix in ((root / "assets/resource", "resource"), (root / "agent", "agent")):
        if source.is_symlink() or not source.is_dir():
            raise ValueError(f"Missing or symlink source directory: {source}")
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink source is not accepted: {path}")
            relative = path.relative_to(source)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if not path.is_file() or path.suffix.lower() in {".pyc", ".pyo", ".log"}:
                continue
            name = prefix + "/" + relative.as_posix()
            safe_name(name)
            files[name] = path.read_bytes()
    if "agent/main.py" not in files:
        raise ValueError("Agent entry is missing")
    model_lock = json.loads((root / "tools/ocr_model.json").read_text(encoding="utf-8"))
    for item in model_lock["files"]:
        data = files.get("resource/model/ocr/" + item["name"], b"")
        if len(data) != item["bytes"] or digest(data) != item["sha256"]:
            raise ValueError("OCR model is missing or differs from its lock; run tools/configure.py --download")
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("Case-colliding resource names")
    check_payload_references(files)
    return files


def write_resource_tree(files: dict[str, bytes], destination: Path) -> None:
    for name, data in files.items():
        safe_name(name)
        path = destination / name
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Refusing a symlink staging path")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def write_archive(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            safe_name(name)
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)


def verify_archive(path: Path, manifest: dict) -> dict[str, bytes]:
    if path.name != manifest["archive"] or digest(path.read_bytes()) != manifest["sha256"]:
        raise ValueError("Archive identity or SHA256 mismatch")
    files = {}
    with zipfile.ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 512 * 1024 * 1024:
            raise ValueError("Resource archive exceeds size limit")
        for item in archive.infolist():
            safe_name(item.filename)
            if item.filename in files or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Duplicate entry or symlink in archive")
            files[item.filename] = archive.read(item)
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("Case-colliding archive entries")
    if {name: digest(data) for name, data in files.items()} != manifest["files"]:
        raise ValueError("Archive content differs from its manifest")
    check_payload_references(files)
    interface = json.loads(files["interface.json"])
    if interface["version"] != manifest["version"] or interface["github"] != manifest["update_source"]:
        raise ValueError("Packaged Interface identity differs")
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--os", choices=PLATFORMS, default="win")
    parser.add_argument("--arch", choices=ARCHES, default="x86_64")
    parser.add_argument("--output", type=Path, default=ROOT / "build/resources")
    parser.add_argument("--update-repository", help="Override update source in the generated package only")
    args = parser.parse_args()
    files = collect_resources(ROOT, args.version, args.os, args.update_repository)
    platform = f"{PLATFORMS[args.os]}-{ARCHES[args.arch]}"
    name = f"TKFMaa-resource-{platform}-{args.version}.zip"
    output = args.output.resolve()
    if output.is_relative_to(ROOT / "assets") or output.is_relative_to(ROOT / "agent"):
        raise ValueError("Output cannot be inside source resources")
    names = [name, name + ".sha256", name + ".manifest.json"]
    if any((output / item).exists() for item in names):
        raise ValueError("Output already exists; choose a new version or output directory")
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True).stdout)
    requirement = (ROOT / "tools/requirements.txt").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(dir=output, prefix=".resource-") as staging:
        archive = Path(staging) / name
        write_archive(archive, files)
        manifest = {"version": args.version, "platform": platform, "archive": name,
                    "sha256": digest(archive.read_bytes()), "source_commit": commit, "worktree_dirty": dirty,
                    "update_source": json.loads(files["interface.json"])["github"],
                    "requires": {"python": (ROOT / ".python-version").read_text().strip(),
                                 "maafw": re.search(r"^maafw==([^\s]+)", requirement, re.MULTILINE)[1]},
                    "files": {key: digest(value) for key, value in sorted(files.items())}}
        verify_archive(archive, manifest)
        (Path(staging) / names[1]).write_text(f"{manifest['sha256']}  {name}\n", encoding="utf-8", newline="\n")
        (Path(staging) / names[2]).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        for item in names:
            with (output / item).open("xb") as target:
                target.write((Path(staging) / item).read_bytes())
    print(json.dumps({"archive": str(output / name), "files": len(files), "sha256": manifest["sha256"]}))


if __name__ == "__main__":
    main()

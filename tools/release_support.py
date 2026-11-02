"""Local release policy. No credentials, network requests or repository writes."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from package_resources import ROOT, digest


TARGETS = tuple(f"{os_name}-{arch}" for os_name in ("win", "osx", "linux") for arch in ("x64", "arm64"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=4) + "\n")


def compatibility_fingerprint(policy: dict) -> str:
    contract = {key: policy[key] for key in ("id", "python", "maafw", "frontend", "dependencies")}
    return digest(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode())


def version_key(version: str) -> tuple:
    match = re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?", version)
    if not match:
        raise ValueError("Require canonical vMAJOR.MINOR.PATCH[-prerelease]; build metadata is not an update sequence")
    pre = match[4]
    identifiers = []
    for part in pre.split(".") if pre else []:
        if part.isdigit() and len(part) > 1 and part.startswith("0"):
            raise ValueError("Numeric prerelease identifiers cannot have leading zeros")
        identifiers.append((0, int(part)) if part.isdigit() else (1, part))
    return (*map(int, match.group(1, 2, 3)), pre is None, tuple(identifiers))


def baseline(root: Path = ROOT) -> dict:
    if sys.version_info[:2] != (3, 12):
        raise ValueError("Release verification requires Python 3.12")
    value = read_json(root / "tools/release_baseline.json")
    if value["schema_version"] != 1 or value["dependencies"]["maafw"] != value["maafw"]:
        raise ValueError("Invalid release baseline")
    if (root / ".python-version").read_text().strip() != value["python"]:
        raise ValueError("Python baseline changed; resource release needs a migration review")
    requirements = (root / "tools/requirements.txt").read_text(encoding="utf-8")
    if not re.search(r"^maafw==" + re.escape(value["maafw"]) + r"\s*$", requirements, re.M):
        raise ValueError("MaaFramework requirement differs from baseline")
    workflow = (root / ".github/workflows/install.yml").read_text(encoding="utf-8")
    for key, expected in (("MAAFW_VERSION", "v" + value["maafw"]), ("MFAA_VERSION", "v" + value["frontend"]), ("PYTHON_VERSION", value["python"])):
        if not re.search(r"^  " + key + r': "' + re.escape(expected) + r'"$', workflow, re.M):
            raise ValueError(f"{key} differs from release baseline")
    return value


def source_identity(root: Path, expected: str, allow_dirty: bool = False) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("Source must be a full lowercase 40-character commit SHA")
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root).decode("utf-8").strip()
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("Source SHA differs from checked out HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=all"))
    tracked = set(git("-c", "core.quotepath=false", "ls-files", "--", "agent", "assets/resource").splitlines())
    # Ignored executable/resource inputs must not silently enter a clean-SHA build.
    # OCR is the sole exception: its ignored files are checked against ocr_model.json.
    for directory in (root / "agent", root / "assets/resource"):
        for path in directory.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if (path.is_file() and path.suffix.lower() in {".py", ".json", ".jsonc", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".onnx", ".txt", ".md"}
                    and not any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(directory).parts)
                    and not relative.startswith("assets/resource/model/ocr/") and relative not in tracked):
                dirty = True
    if dirty and not allow_dirty:
        raise ValueError("Dirty source rejected; --allow-dirty is local rehearsal only")
    return {"commit": expected, "worktree_dirty": dirty, "rehearsal": allow_dirty}


def check_agent_imports(files: dict[str, bytes], policy: dict) -> None:
    local = {Path(name).parts[1].removesuffix(".py") for name in files if name.startswith("agent/")}
    allowed = set(sys.stdlib_module_names) | local | set(policy["agent_imports"])
    for name, data in files.items():
        if not name.startswith("agent/") or not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(data.decode("utf-8-sig"), filename=name)):
            imports = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imports = [node.module or ""]
            if any(item.split(".")[0] not in allowed for item in imports):
                raise ValueError(f"Unreviewed Agent dependency in {name}: {imports}")
    # Static imports are a guard, not a proof about dynamic imports or API compatibility.


def asset_priority(name: str, target: str) -> int:
    """MFA 2.16.2 GetAssetPriority, pinned revision in release_baseline.json."""
    os_name, arch = target.split("-")
    family = "windows" if os_name == "win" else "unix"
    aliases = {"win": "win|windows", "osx": "osx|macos|mac", "linux": "linux|debian|ubuntu", "unix": "unix|bsd|freebsd"}
    cpu = "x64|x86_64" if arch == "x64" else "arm64|aarch64"
    def pattern(os_value, arch_value):
        if os_value in aliases:
            return rf"\b(?:{aliases[os_value]})-(?:{arch_value})\b"
        return rf"\b{os_value}-{arch_value}\b"
    for expression, score in ((pattern(os_name, cpu), 100), (pattern(os_name, ".*"), 80),
                              (pattern(family, cpu), 60), (pattern(family, ".*"), 40), (rf"-(?:{cpu})", 20)):
        if re.search(expression, name.lower()):
            return score
    # Upstream lowercases before a case-sensitive Contains("MFA"), so no bonus applies.
    return 0


def check_selection(names: list[str], expected: dict[str, str]) -> None:
    if set(expected) != set(TARGETS) or len(names) != len(set(names)):
        raise ValueError("Require six desktop targets and unique asset names")
    for target in TARGETS:
        scores = {name: asset_priority(name, target) for name in names}
        best = max(scores.values(), default=0)
        winners = [name for name, score in scores.items() if score == best]
        if best != 100 or winners != [expected[target]] or not winners[0].endswith(".zip"):
            raise ValueError(f"Ambiguous or incorrect asset for {target}: {winners}")


def file_entry(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Require a regular asset file")
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"name": path.name, "size": path.stat().st_size, "sha256": checksum}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-requirement", choices=("numpy", "maaagentbinary", "strenum"))
    args = parser.parse_args()
    policy = baseline()
    if args.runtime_requirement:
        print(f"{args.runtime_requirement}=={policy['dependencies'][args.runtime_requirement]}")
    else:
        print(json.dumps({"baseline": policy["id"], "channel_baseline_sha256": compatibility_fingerprint(policy), "passed": True}))


if __name__ == "__main__":
    main()

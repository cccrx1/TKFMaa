"""Check version alignment without connecting to a device."""

import argparse
from importlib.metadata import version
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent


def check_environment(*, load_resource: bool = False) -> None:
    requirements = (ROOT / "tools/requirements.txt").read_text(encoding="utf-8")
    pinned = re.search(r"^maafw==([\d.]+)$", requirements, re.MULTILINE).group(1)
    workflow = yaml.safe_load((ROOT / ".github/workflows/install.yml").read_text(encoding="utf-8"))
    build = workflow["env"]
    maa_tools = re.search(
        r'maaVersion:\s*"([\d.]+)"', (ROOT / "maatools.config.mts").read_text(encoding="utf-8")
    ).group(1)
    python_version = (ROOT / ".python-version").read_text().strip()
    checks = {
        "build MaaFramework": (str(build["MAAFW_VERSION"]).removeprefix("v"), pinned),
        "maa-tools MaaFramework": (maa_tools, pinned),
        "installed maafw": (version("maafw").removeprefix("v"), pinned),
        "build Python": (str(build["PYTHON_VERSION"]), python_version),
        "Python interpreter": (f"{sys.version_info.major}.{sys.version_info.minor}", python_version),
        "build Python ABI": (str(build["PYTHON_ABI"]), f"cp{python_version.replace('.', '')}"),
    }
    from maa.library import Library

    checks["loaded native runtime"] = (Library.version().removeprefix("v"), pinned)
    failures = []
    for name, (actual, expected) in checks.items():
        print(f"{name}: {actual} (expected {expected})")
        if actual != expected:
            failures.append(name)
    if failures:
        raise ValueError(f"Version mismatch: {', '.join(failures)}")
    print(f"Native library: {Library.framework_libpath}")
    print(f"Build frontend: {build['MFAA_VERSION']} (GUI compatibility requires a packaged app test)")
    if load_resource:
        from maa.resource import Resource
        from maa.tasker import Tasker

        Tasker.set_log_dir(ROOT / "debug/environment")
        resource = Resource()
        job = resource.post_bundle(ROOT / "assets/resource").wait()
        if not job.succeeded or not resource.loaded:
            raise ValueError("Resource bundle failed to load")
        print("Resource bundle loaded (no device actions)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load-resource", action="store_true")
    args = parser.parse_args()
    try:
        check_environment(load_resource=args.load_resource)
    except Exception as exc:
        print(f"Environment check failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

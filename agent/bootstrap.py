import os
import platform
import sys
from pathlib import Path


def configure_runtime() -> None:
    """Configure bundled Python packages and the shared MaaFW native runtime."""
    project_root = Path(__file__).resolve().parent.parent
    vendored_packages = project_root / "python_packages"
    if not vendored_packages.is_dir():
        return

    if sys.version_info[:2] != (3, 14):
        raise RuntimeError(
            "This release requires Python 3.14 because its bundled NumPy "
            f"is CPython 3.14-specific; current version is {sys.version.split()[0]}."
        )

    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        arch = "arm64"
    elif machine in {"amd64", "x86_64"}:
        arch = "x64"
    else:
        raise RuntimeError(
            f"Unsupported Python architecture: {platform.machine()}; "
            "use a 64-bit x64 or ARM64 CPython 3.14 build."
        )
    platform_prefix = {"windows": "win", "darwin": "osx", "linux": "linux"}.get(
        system
    )
    if platform_prefix is None:
        raise RuntimeError(f"Unsupported release platform: {platform.system()}")

    native_dir = project_root / "runtimes" / f"{platform_prefix}-{arch}" / "native"
    if not native_dir.is_dir():
        raise RuntimeError(f"Bundled MaaFW runtime is missing: {native_dir}")

    # A release must never pick up a stale global MaaFW installation.
    os.environ["MAAFW_BINARY_PATH"] = str(native_dir)

    vendored_path = str(vendored_packages)
    if vendored_path not in sys.path:
        sys.path.insert(0, vendored_path)

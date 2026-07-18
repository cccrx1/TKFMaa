import os
import platform
import sys
from pathlib import Path


def configure_runtime() -> None:
    """Point MaaFw at the native runtime shared with the frontend."""
    project_root = Path(__file__).resolve().parent.parent
    bundled_python_dir = project_root / "python"
    using_bundled_python = bundled_python_dir.is_dir() and Path(
        sys.executable
    ).resolve().is_relative_to(bundled_python_dir.resolve())

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
    if using_bundled_python and not native_dir.is_dir():
        raise RuntimeError(f"Bundled MaaFW runtime is missing: {native_dir}")

    if native_dir.is_dir():
        # Prefer the release runtime even when the user also installed MaaFw.
        os.environ["MAAFW_BINARY_PATH"] = str(native_dir)

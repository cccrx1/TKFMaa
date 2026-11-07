"""Stage a pinned patched desktop frontend; this command never publishes."""

import argparse
from pathlib import Path

from frontend_build import PLATFORMS, stage


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    args = parser.parse_args()
    stage(args.published, args.output, args.source, args.platform)
    print("Pinned patched frontend staged; publication not performed")

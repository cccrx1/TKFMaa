"""Stage a Windows x64 candidate frontend with verifiable, non-release provenance."""

import argparse
from pathlib import Path

from frontend_build import stage as stage_frontend


def stage(published: Path, output: Path, source: Path) -> dict:
    return stage_frontend(published, output, source, "win-x64", candidate=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    stage(args.published, args.output, args.source)
    print("Candidate frontend staged; not approved for Release")

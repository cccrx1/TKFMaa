"""Download six schemas from a stable MaaFramework tag."""

import argparse
import json
from pathlib import Path
import re
import tempfile
from urllib.request import urlopen

from maafw_release import stable_version


ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = (
    "interface.schema.json",
    "interface_config.schema.json",
    "interface_import.schema.json",
    "pipeline.schema.json",
    "custom.action.schema.json",
    "custom.recognition.schema.json",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maafw-tag", help="Stable tag, defaults to the resource channel version")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "deps/tools")
    args = parser.parse_args()
    if args.maafw_tag and args.output_dir.resolve() == (ROOT / "deps/tools").resolve():
        raise ValueError("Use a separate output directory for full-package schemas")
    requirements = (ROOT / "tools/requirements.txt").read_text(encoding="utf-8")
    version = stable_version(args.maafw_tag or re.search(r"^maafw==([\d.]+)$", requirements, re.MULTILINE)[1])
    target_dir = args.output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="schemas-", dir=target_dir.parent) as staging:
        for name in SCHEMAS:
            url = f"https://raw.githubusercontent.com/MaaXYZ/MaaFramework/v{version}/tools/{name}"
            with urlopen(url, timeout=60) as response:
                data = response.read()
            schema = json.loads(data)
            if not isinstance(schema, dict) or "$schema" not in schema:
                raise ValueError(f"Invalid JSON Schema: {name}")
            (Path(staging) / name).write_bytes(data)
        # Do not publish partially downloaded or invalid JSON schemas.
        for name in SCHEMAS:
            (target_dir / name).write_bytes((Path(staging) / name).read_bytes())
    print(f"Synchronized {len(SCHEMAS)} schemas from MaaFramework v{version}")


if __name__ == "__main__":
    main()

"""Download six schemas from the MaaFramework version pinned by this project."""

import json
from pathlib import Path
import re
import tempfile
from urllib.request import urlopen


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
    requirements = (ROOT / "tools/requirements.txt").read_text(encoding="utf-8")
    pinned = re.search(r"^maafw==([\d.]+)$", requirements, re.MULTILINE).group(1)
    target_dir = ROOT / "deps/tools"
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="schemas-", dir=target_dir.parent) as staging:
        for name in SCHEMAS:
            url = f"https://raw.githubusercontent.com/MaaXYZ/MaaFramework/v{pinned}/tools/{name}"
            with urlopen(url, timeout=60) as response:
                data = response.read()
            schema = json.loads(data)
            if not isinstance(schema, dict) or "$schema" not in schema:
                raise ValueError(f"Invalid JSON Schema: {name}")
            (Path(staging) / name).write_bytes(data)
        # Do not publish partially downloaded or invalid JSON schemas.
        for name in SCHEMAS:
            (target_dir / name).write_bytes((Path(staging) / name).read_bytes())
    print(f"Synchronized {len(SCHEMAS)} schemas from MaaFramework v{pinned}")


if __name__ == "__main__":
    main()

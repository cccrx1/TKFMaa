"""Select and record the stable MaaFramework release used by a complete build."""

import argparse
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen


def stable_version(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"v?(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}", value):
        raise ValueError(f"Expected a stable MaaFramework version, got {value!r}")
    return value.removeprefix("v")


def latest_tag(token: str | None = None) -> str:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request("https://api.github.com/repos/MaaXYZ/MaaFramework/releases/latest", headers=headers)
    with urlopen(request, timeout=30) as response:
        release = json.load(response)
    tag = release["tag_name"]
    if release["draft"] or release["prerelease"] or tag != "v" + stable_version(tag):
        raise ValueError(f"GitHub did not return a stable MaaFramework release tag: {tag!r}")
    return tag


def read_selection(path: Path, commit: str) -> str:
    selection = json.loads(path.read_text(encoding="utf-8"))
    if selection["source_sha"] != commit:
        raise ValueError("MaaFramework selection belongs to a different source commit")
    return stable_version(selection["tag"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    if args.selection.exists():
        tag = "v" + read_selection(args.selection, args.source_sha)
    else:
        tag = latest_tag(os.environ.get("GH_TOKEN"))
        args.selection.parent.mkdir(parents=True, exist_ok=True)
        with args.selection.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump({"tag": tag, "source_sha": args.source_sha}, stream)
            stream.write("\n")
    print(tag)


if __name__ == "__main__":
    main()

import argparse
import json
from pathlib import Path


INTERACTIVE_ACTIONS = {"Click", "ClickKey", "InputText", "LongPress", "Swipe"}
PRE_WAIT_FREEZES_MS = 300

# These controls only exist during an animation or intentionally operate on a moving screen.
EXEMPT_NODES = {
    "DailyRecruitmentCollectSkip": "skip button is only available during the recruitment animation",
    "DailyStaminaSkipSweepAnimationLower": "skip button is only available during the sweep animation",
    "DailyStaminaSkipSweepAnimationUpper": "skip button is only available during the sweep animation",
    "GameTapTitleScreen": "title screen background is continuously animated",
}


def needs_pre_wait(name: str, node: dict) -> bool:
    action_type = node.get("action", {}).get("type")
    recognition_type = node.get("recognition", {}).get("type")
    return (
        action_type in INTERACTIVE_ACTIONS
        and recognition_type not in {None, "DirectHit"}
        and "pre_wait_freezes" not in node
        and name not in EXEMPT_NODES
    )


def process_file(path: Path, check: bool) -> list[str]:
    pipeline = json.loads(path.read_text(encoding="utf-8"))
    missing = [name for name, node in pipeline.items() if needs_pre_wait(name, node)]

    if missing and not check:
        for name in missing:
            pipeline[name]["pre_wait_freezes"] = PRE_WAIT_FREEZES_MS
        path.write_text(
            json.dumps(pipeline, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add a short stability wait before recognition-driven interactive actions."
    )
    parser.add_argument("--check", action="store_true", help="report missing waits without changing files")
    parser.add_argument(
        "--pipeline-dir",
        type=Path,
        default=Path("assets/resource/pipeline"),
        help="directory containing Pipeline JSON files",
    )
    args = parser.parse_args()

    changed: dict[Path, list[str]] = {}
    for path in sorted(args.pipeline_dir.glob("*.json")):
        missing = process_file(path, args.check)
        if missing:
            changed[path] = missing

    if not changed:
        print("Interaction stability waits are up to date.")
        return 0

    verb = "missing" if args.check else "added"
    for path, nodes in changed.items():
        print(f"{path}: {verb} pre_wait_freezes for {len(nodes)} node(s)")

    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())

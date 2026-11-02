"""Verify a generated resource archive; never connects to a device."""

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import jsonc

from package_resources import ROOT, verify_archive, write_resource_tree


def check_custom_registrations(stage: Path) -> None:
    registered = {"custom_action": set(), "custom_recognition": set()}
    referenced = {key: set() for key in registered}
    for path in (stage / "agent").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in registered and node.args and isinstance(node.args[0], ast.Constant)):
                registered[node.func.attr].add(node.args[0].value)

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in referenced and isinstance(child, str):
                    referenced[key].add(child)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    pipelines = [path for path in (stage / "resource/pipeline").rglob("*") if path.suffix in {".json", ".jsonc"}]
    for path in [stage / "interface.json", *pipelines]:
        with path.open(encoding="utf-8-sig") as stream:
            visit(jsonc.load(stream))
    for kind in referenced:
        if referenced[kind] - registered[kind]:
            raise ValueError(f"Unregistered {kind}: {sorted(referenced[kind] - registered[kind])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    name = manifest["archive"]
    if Path(name).name != name or "\\" in name or "/" in name:
        raise ValueError("Unsafe archive name in manifest")
    files = verify_archive(args.manifest.parent / name, manifest)
    for schema in ("pipeline.schema.json", "interface.schema.json", "custom.action.schema.json", "custom.recognition.schema.json"):
        if not (ROOT / "deps/tools" / schema).is_file():
            raise ValueError(f"Required schema missing: {schema}")
    with tempfile.TemporaryDirectory(prefix="tkfmaa-resource-check-") as folder:
        stage = Path(folder)
        write_resource_tree(files, stage)
        subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_schema.py"),
                        "--schema-dir", str(ROOT / "deps/tools"), "--resource-dirs", str(stage / "resource"),
                        "--exclude-dirs", str(stage / "resource/announcement"),
                        "--interface-files", str(stage / "interface.json")], check=True)
        check_custom_registrations(stage)
        subprocess.run([sys.executable, "-B", "-c",
                        "from maa.resource import Resource; from maa.tasker import Tasker; import sys; "
                        "Tasker.set_log_dir(sys.argv[2]); r=Resource(); j=r.post_bundle(sys.argv[1]).wait(); "
                        "assert j.succeeded and r.loaded; print('Packaged resource load OK')",
                        str(stage / "resource"), str(stage / "logs")], check=True, cwd=stage)
        subprocess.run([sys.executable, "-B", "-c",
                        "import sys; sys.path.insert(0,sys.argv[1]); import main; print('Packaged Agent imports OK')",
                        str(stage / "agent")], check=True, cwd=stage)
    print(json.dumps({"passed": True, "archive": name, "device_tests": "not_run"}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import copy
import json
import sys
from pathlib import Path


OPTION_NAME = "体力消耗关卡"
REGULAR_AUTO_CLEAR_MODE = "regular_auto_clear"
REGULAR_AUTO_CLEAR_SENTINEL = "__REGULAR_ACTIVITY_CLEAR__"

RERUN_COLUMN_NODES = {
    "main": "DailyStaminaRerunMainColumnStart",
    "left": "DailyStaminaRerunLeftColumnStart",
    "right": "DailyStaminaRerunRightColumnStart",
}

ROUTE_START_NODES = {
    "rerun_map": "DailyStaminaRouteInnerRerunUiStart",
    "special_icon": "DailyStaminaRouteInnerSpecialUiStart",
    "challenge_button": "DailyStaminaRouteInnerChallengeUiStart",
    "normal_list": "DailyStaminaRouteInnerNormalListStart",
    "daily_affairs": "DailyStaminaRouteDailyAffairsStart",
}

ROUTE_ENTRY_MARKER_NODES = {
    "rerun_map": "DailyStaminaPresetRerunMapMarker",
    "special_icon": "DailyStaminaPresetInnerUiTitle",
    "challenge_button": "DailyStaminaPresetInnerUiTitle",
    "normal_list": "DailyStaminaPresetStageListAnySelectable",
    "daily_affairs": "DailyStaminaPresetDailyAffairsCategory",
}


def strip_jsonc_comments(text):
    result = []
    in_string = False
    escaped = False
    i = 0

    while i < len(text):
        char = text[i]
        nxt = text[i : i + 2]

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            result.append(char)
            in_string = True
            i += 1
        elif nxt == "//":
            while i < len(text) and text[i] != "\n":
                i += 1
        elif nxt == "/*":
            i += 2
            while i + 1 < len(text) and text[i : i + 2] != "*/":
                if text[i] == "\n":
                    result.append("\n")
                i += 1
            i += 2
        else:
            result.append(char)
            i += 1

    return "".join(result)


def load_source(path):
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "PyYAML is required for YAML stamina activity config. "
                "Install tools/requirements.txt first, or use a JSON/JSONC source."
            ) from exc
        return yaml.safe_load(text)
    if suffix == ".jsonc":
        return json.loads(strip_jsonc_comments(text))
    if suffix == ".json":
        return json.loads(text)
    raise SystemExit(f"Unsupported source format: {path}")


def load_jsonc(path):
    return json.loads(strip_jsonc_comments(path.read_text(encoding="utf-8")))


def validate_against_schema(config, schema_path):
    if not schema_path.exists():
        return
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        return

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(config),
        key=lambda error: list(error.path),
    )
    if not errors:
        return

    print(f"{schema_path} validation failed:", file=sys.stderr)
    for error in errors[:10]:
        path = ".".join(str(part) for part in error.path) or "<root>"
        print(f"- {path}: {error.message}", file=sys.stderr)
    raise SystemExit(1)


def deep_merge(*objects):
    result = {}
    for obj in objects:
        if not obj:
            continue
        for key, value in obj.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
    return result


def expand_activity_groups(config):
    expanded = copy.deepcopy(config)
    groups = expanded.get("activity_groups", {})
    if not isinstance(groups, dict):
        raise ValueError("activity_groups must be an object")

    activities = []
    for group_id, group in groups.items():
        if not isinstance(group, dict):
            raise ValueError(f"activity_groups.{group_id} must be an object")

        base = group.get("base")
        cases = group.get("cases")
        case_prefix = group.get("case_prefix")
        if not isinstance(base, dict):
            raise ValueError(f"activity_groups.{group_id}.base must be an object")
        if not isinstance(cases, list) or not cases:
            raise ValueError(
                f"activity_groups.{group_id}.cases must be a non-empty list"
            )
        if not case_prefix:
            raise ValueError(f"activity_groups.{group_id}.case_prefix is required")

        description_template = group.get("description_template", "")
        for index, case in enumerate(cases):
            if not isinstance(case, dict):
                raise ValueError(
                    f"activity_groups.{group_id}.cases[{index}] must be an object"
                )

            case_override = copy.deepcopy(case)
            case_suffix = case_override.pop("case_suffix", None)
            if not case_suffix and not case_override.get("name"):
                raise ValueError(
                    f"activity_groups.{group_id}.cases[{index}] requires "
                    "case_suffix or name"
                )

            case_name = case_override.get("name") or f"{case_prefix} - {case_suffix}"
            case_override["name"] = case_name
            if case_override.get("mode") == REGULAR_AUTO_CLEAR_MODE:
                case_override.setdefault("stage", {}).setdefault(
                    "expected", [REGULAR_AUTO_CLEAR_SENTINEL]
                )
            if not case_override.get("description") and description_template:
                case_override["description"] = description_template.format(
                    activity=case_prefix,
                    stage=case_suffix or case_name,
                    case=case_name,
                )

            activities.append(deep_merge(base, case_override))

    raw_activities = expanded.get("activities", [])
    if raw_activities is not None:
        if not isinstance(raw_activities, list):
            raise ValueError("activities must be a list")
        activities.extend(copy.deepcopy(raw_activities))

    expanded["activities"] = activities
    return expanded


def ocr_recognition(config, fallback_roi=None):
    if not config or not config.get("expected"):
        raise ValueError("OCR recognition requires a non-empty expected list")
    param = {"expected": config["expected"]}
    roi = config.get("roi", fallback_roi)
    if roi is not None:
        param["roi"] = roi
    return {"type": "OCR", "param": param}


def validate_roi(roi, field):
    if roi is None:
        return
    if not isinstance(roi, list) or len(roi) != 4:
        raise ValueError(f"{field} must be a 4-number ROI")
    if not all(isinstance(value, int) for value in roi):
        raise ValueError(f"{field} must contain integers")


def validate_config(config):
    if config.get("version") != 1:
        raise ValueError("version must be 1")
    templates = config.get("templates")
    activities = config.get("activities")
    if not isinstance(templates, dict) or not templates:
        raise ValueError("templates must be a non-empty object")
    if not isinstance(activities, list) or not activities:
        raise ValueError("activities must be a non-empty list")

    names = set()
    for activity in activities:
        name = activity.get("name")
        if not name:
            raise ValueError("activity.name is required")
        if name in names:
            raise ValueError(f"duplicate activity name: {name}")
        names.add(name)
        template_name = activity.get("template")
        if template_name not in templates:
            raise ValueError(f"unknown template for {name}: {template_name}")

        resolved = resolve_activity(config, activity)
        route_type = resolved.get("route_type")
        mode = resolved.get("mode")
        if route_type not in ROUTE_START_NODES:
            raise ValueError(f"{name}: unsupported route_type {route_type}")
        if mode and mode != REGULAR_AUTO_CLEAR_MODE:
            raise ValueError(f"{name}: unsupported mode {mode}")
        if mode == REGULAR_AUTO_CLEAR_MODE and route_type != "normal_list":
            raise ValueError(
                f"{name}: {REGULAR_AUTO_CLEAR_MODE} requires route_type normal_list"
            )
        for field, roi in (
            ("activity_section.roi", resolved.get("activity_section", {}).get("roi")),
            ("activity_name.roi", resolved.get("activity_name", {}).get("roi")),
            ("stage.roi", resolved.get("stage", {}).get("roi")),
            ("stamina.roi", resolved.get("stamina", {}).get("roi")),
        ):
            validate_roi(roi, f"{name}.{field}")

        if not resolved.get("activity_name", {}).get("expected"):
            raise ValueError(f"{name}: activity_name.expected is required")
        if not resolved.get("stage", {}).get("expected"):
            raise ValueError(f"{name}: stage.expected is required")
        if resolved.get("stamina", {}).get("cost", 0) <= 0:
            raise ValueError(f"{name}: stamina.cost must be greater than 0")
        if resolved.get("stamina", {}).get("reserve", 0) < 0:
            raise ValueError(f"{name}: stamina.reserve must not be negative")

        if route_type == "rerun_map":
            if resolved.get("rerun", {}).get("column") not in RERUN_COLUMN_NODES:
                raise ValueError(f"{name}: rerun.column must be main, left, or right")
            rerun_marker = resolved.get("rerun", {}).get("marker") or resolved.get(
                "inner_title"
            )
            if not rerun_marker or not rerun_marker.get("expected"):
                raise ValueError(
                    f"{name}: rerun.marker or inner_title.expected is required"
                )
        if route_type in ("special_icon", "normal_list"):
            if not (
                resolved.get("stage", {}).get("any_selectable")
                or resolved.get("inner_title", {}).get("expected")
            ):
                raise ValueError(
                    f"{name}: stage.any_selectable or inner_title is required for {route_type}"
                )
        if route_type == "special_icon":
            if not resolved.get("inner_title", {}).get("expected"):
                raise ValueError(f"{name}: inner_title.expected is required")
            if not resolved.get("stage_entry"):
                raise ValueError(f"{name}: stage_entry is required")
        if route_type == "challenge_button" and not resolved.get("inner_title", {}).get("expected"):
            raise ValueError(f"{name}: inner_title.expected is required")
        if route_type == "daily_affairs" and not (
            resolved.get("daily_affairs", {}).get("category", {}).get("expected")
        ):
            raise ValueError(f"{name}: daily_affairs.category.expected is required")


def resolve_activity(config, activity):
    defaults = config.get("defaults", {})
    template = config["templates"][activity["template"]]
    resolved = deep_merge(defaults, template, activity)
    if "activity_name_roi" in defaults:
        resolved.setdefault("activity_name", {}).setdefault(
            "roi", defaults["activity_name_roi"]
        )
    if "stage_roi" in defaults:
        resolved.setdefault("stage", {}).setdefault("roi", defaults["stage_roi"])
    if "stamina_roi" in defaults:
        resolved.setdefault("stamina", {}).setdefault("roi", defaults["stamina_roi"])
    if "reserve" in defaults:
        resolved.setdefault("stamina", {}).setdefault("reserve", defaults["reserve"])
    return resolved


def build_stamina_recognition(mode, stamina):
    return {
        "type": "Custom",
        "param": {
            "custom_recognition": "DailyStaminaCompare",
            "custom_recognition_param": {
                "mode": mode,
                "cost": stamina["cost"],
                "reserve": stamina.get("reserve", 0),
                "stamina_roi": stamina["roi"],
            },
        },
    }


def reference_recognition(node_name):
    return {
        "type": "And",
        "param": {
            "all_of": [node_name],
        },
    }


def build_override(resolved):
    route_type = resolved["route_type"]
    mode = resolved.get("mode")
    stage = resolved["stage"]
    stamina = resolved["stamina"]
    inner_title = resolved.get("inner_title")

    override = {
        "DailyStaminaPresetRouteStart": {
            "next": ["DailyStaminaRouteActivitySectionStart"]
        },
        "DailyStaminaPresetActivitySection": {
            "recognition": ocr_recognition(resolved["activity_section"])
        },
        "DailyStaminaPresetInnerRouteStart": {
            "recognition": reference_recognition(
                ROUTE_ENTRY_MARKER_NODES[route_type]
            ),
            "next": [ROUTE_START_NODES[route_type]]
        },
        "DailyStaminaPresetActivityName": {
            "recognition": ocr_recognition(resolved["activity_name"])
        },
        "DailyStaminaPresetStageListTarget": {
            "recognition": ocr_recognition(stage, resolved.get("stage_roi"))
        },
        "DailyStaminaPresetStaminaEnough": {
            "recognition": build_stamina_recognition("enough", stamina)
        },
        "DailyStaminaPresetStaminaLow": {
            "recognition": build_stamina_recognition("low", stamina)
        },
    }

    if route_type == "rerun_map":
        column = resolved["rerun"]["column"]
        override["DailyStaminaRouteInnerRerunUiStart"] = {
            "next": ["DailyStaminaRerunClickTarget", RERUN_COLUMN_NODES[column]]
        }
        marker = resolved.get("rerun", {}).get("marker") or inner_title
        if marker:
            override["DailyStaminaPresetRerunMapMarker"] = {
                "recognition": ocr_recognition(marker)
            }
        override["CommonReturnMainFromStaminaStageList"] = {
            "recognition": reference_recognition("DailyStaminaPresetRerunMapMarker")
        }

    if route_type in ("special_icon", "challenge_button"):
        override["DailyStaminaPresetInnerUiTitle"] = {
            "enabled": True,
            "recognition": ocr_recognition(resolved["inner_title"]),
        }

    if route_type == "special_icon":
        override["DailyStaminaPresetStageEntry"] = {
            "enabled": True,
            "recognition": resolved["stage_entry"],
        }

    if route_type == "daily_affairs":
        override["DailyStaminaPresetDailyAffairsCategory"] = {
            "enabled": True,
            "recognition": ocr_recognition(
                resolved["daily_affairs"]["category"]
            ),
        }

    any_selectable = stage.get("any_selectable") or inner_title
    if any_selectable:
        override["DailyStaminaPresetStageListAnySelectable"] = {
            "enabled": True,
            "recognition": ocr_recognition(any_selectable)
        }
        if route_type != "rerun_map":
            override["CommonReturnMainFromStaminaStageList"] = {
                "recognition": reference_recognition(
                    "DailyStaminaPresetStageListAnySelectable"
                )
            }

    override = deep_merge(override, resolved.get("extra_overrides", {}))

    if mode == REGULAR_AUTO_CLEAR_MODE:
        if not any_selectable:
            raise ValueError(
                f"{REGULAR_AUTO_CLEAR_MODE} requires stage.any_selectable"
            )
        override["DailyStaminaPresetInnerRouteStart"] = deep_merge(
            override["DailyStaminaPresetInnerRouteStart"],
            {"next": ["RegularActivityStageListDecision"]},
        )
        override["RegularActivityPresetStageListMarker"] = {
            "recognition": ocr_recognition(any_selectable)
        }

    return override


def build_cases(config):
    config = expand_activity_groups(config)
    validate_config(config)
    return [
        {
            "name": activity["name"],
            "description": activity.get("description", ""),
            "pipeline_override": build_override(resolve_activity(config, activity)),
        }
        for activity in config["activities"]
    ]


def write_interface(interface_path, interface):
    interface_path.write_text(
        json.dumps(interface, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def print_case(cases, name):
    for case in cases:
        if case["name"] == name:
            print(json.dumps(case, ensure_ascii=False, indent=4))
            return
    raise SystemExit(f"case not found: {name}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interface.json stamina activity cases from YAML/JSON config."
    )
    parser.add_argument("--source", default="assets/stamina_activities.yaml")
    parser.add_argument("--interface", default="assets/interface.json")
    parser.add_argument("--schema", default="deps/tools/stamina_activities.schema.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-case")
    args = parser.parse_args()

    source_path = Path(args.source)
    interface_path = Path(args.interface)
    config = load_source(source_path)
    validate_against_schema(config, Path(args.schema))
    cases = build_cases(config)

    if args.print_case:
        print_case(cases, args.print_case)
        return

    interface = load_jsonc(interface_path)
    try:
        option = interface["option"][OPTION_NAME]
    except KeyError as exc:
        raise SystemExit(f"missing option {OPTION_NAME} in {interface_path}") from exc

    if args.check:
        current = option.get("cases", [])
        expected_default_case = cases[0]["name"] if cases else None
        if current != cases or option.get("default_case") != expected_default_case:
            print(f"{interface_path} is not in sync with {source_path}", file=sys.stderr)
            print("Run: python tools/build_stamina_activities.py", file=sys.stderr)
            sys.exit(1)
        print(f"{interface_path} is in sync with {source_path}")
        return

    option["cases"] = cases
    if cases:
        option["default_case"] = cases[0]["name"]
    write_interface(interface_path, interface)
    print(f"Updated {interface_path} from {source_path}")


if __name__ == "__main__":
    main()

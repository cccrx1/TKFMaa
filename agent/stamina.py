import logging
import re

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JClick, JOCR

from common import safe_json_loads


_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUBSCRIPT_DIGITS = "₀₁₂₃₄₅₆₇₈₉"
_DECORATED_DIGITS = _SUPERSCRIPT_DIGITS + _SUBSCRIPT_DIGITS
_DECORATED_DIGIT_PATTERNS = {
    form: f"[{digit}{fullwidth}{superscript}{subscript}]"
    for digit, (fullwidth, superscript, subscript) in enumerate(
        zip("０１２３４５６７８９", _SUPERSCRIPT_DIGITS, _SUBSCRIPT_DIGITS)
    )
    for form in (superscript, subscript)
}
_NAME_VARIANT = re.compile(
    rf"\s*(?:½|(?<![\d{_DECORATED_DIGITS}])[1１¹₁]\s*[/／⁄∕]\s*[2２²₂]"
    rf"(?![\d{_DECORATED_DIGITS}])|(?P<digits>[{_DECORATED_DIGITS}]+))\s*"
)
_HALF_OCR = r"(?:[1１¹₁]?\s*½(?:\s*[/／⁄∕]?\s*[2２²₂])?|[1１¹₁]\s*[/／⁄∕]?\s*[2２²₂])"


def _stamina_name_pattern(name):
    parts = []
    cursor = 0
    for match in _NAME_VARIANT.finditer(name):
        parts.append(re.escape(name[cursor:match.start()]))
        variant = _HALF_OCR
        if digits := match.group("digits"):
            variant = r"\s*".join(_DECORATED_DIGIT_PATTERNS[digit] for digit in digits)
        parts.extend((r"\s*", variant, r"\s*"))
        cursor = match.end()
    parts.append(re.escape(name[cursor:]))
    return "".join(parts)


def build_custom_stamina_override(param):
    routes = {
        "normal_list": "DailyStaminaRouteInnerNormalListStart",
        "regular_paged_list": "DailyStaminaRouteRegularPagedFirstPageStart",
        "rerun_activity_map": "DailyStaminaRouteInnerRerunUiStart",
        "large_activity_stage_icon": "DailyStaminaRouteInnerSpecialUiStart",
        "large_activity_direct_stage": "DailyStaminaRouteInnerChallengeUiStart",
    }
    template = param.get("route", param.get("template"))
    if template not in routes:
        raise ValueError("请选择支持的自定义关卡模板")
    names = {}
    for field in ("activity", "stage", "list_marker", "stage_entry"):
        value = param.get(field, "")
        if not isinstance(value, str):
            raise ValueError(f"{field} 必须是文本")
        names[field] = value.strip()
    if not names["activity"] or not names["stage"]:
        raise ValueError("活动名称和关卡名称不能为空")
    if template == "large_activity_stage_icon" and not names["stage_entry"]:
        raise ValueError("大型活动关卡图标页需要填写关卡入口文字")
    if re.search(r"协会共斗|協會共鬥|挑战活动|挑戰活動|活动挑战|活動挑戰", names["activity"]):
        raise ValueError("请选择活动本体")
    cost = param.get("cost")
    if isinstance(cost, bool) or not re.fullmatch(r"[1-9][0-9]*", str(cost)):
        raise ValueError("每次体力消耗必须为正整数")

    def ocr(expected, roi):
        return {"type": "OCR", "param": {"expected": [expected], "roi": roi}}

    marker_text = names["list_marker"] or names["activity"]
    marker = _stamina_name_pattern(marker_text)
    marker_roi = [0, 90, 720, 180]
    stage = _stamina_name_pattern(names["stage"])
    stage_roi = [0, 160, 720, 1000]
    route_marker = "DailyStaminaPresetStageListAnySelectable"
    if template == "rerun_activity_map":
        route_marker = "DailyStaminaPresetRerunMapMarker"
        # The fixed header excludes animated map tiles that can distort the fraction OCR.
        marker_roi = [0, 116, 245, 55]
        # Map OCR can read the stamina badge as part of the stage label.
        stage += rf"(?: *[⚡ϟ4]? *{cost})?"
    elif template in ("large_activity_stage_icon", "large_activity_direct_stage"):
        route_marker = "DailyStaminaPresetInnerUiTitle"
    if route_marker == "DailyStaminaPresetInnerUiTitle" or _NAME_VARIANT.search(marker_text):
        marker = f"^{marker}$"
    marker_recognition = {"type": "And", "param": {"all_of": [route_marker]}}
    override = {
        "DailyStaminaPresetActivityName": {
            "recognition": ocr(f"^{_stamina_name_pattern(names['activity'])}$", [70, 765, 580, 86])
        },
        "DailyStaminaPresetStageListTarget": {
            "recognition": ocr(f"^{stage}$", stage_roi)
        },
        route_marker: {
            "enabled": True,
            "recognition": ocr(marker, marker_roi),
        },
        "DailyStaminaPresetInnerRouteStart": {
            "recognition": marker_recognition,
            "next": [routes[template]],
        },
        "CommonReturnMainFromStaminaStageList": {"recognition": marker_recognition},
    }
    if template == "large_activity_stage_icon":
        override["DailyStaminaPresetStageEntry"] = {
            "enabled": True,
            "recognition": ocr(f"^{_stamina_name_pattern(names['stage_entry'])}$", stage_roi),
        }
    for mode, node in (
        ("enough", "DailyStaminaPresetStaminaEnough"),
        ("low", "DailyStaminaPresetStaminaLow"),
    ):
        override[node] = {
            "recognition": {
                "type": "Custom",
                "param": {
                    "custom_recognition": "DailyStaminaCompare",
                    "custom_recognition_param": {
                        "mode": mode,
                        "cost": int(cost),
                        "reserve": 0,
                        "stamina_roi": [500, 0, 180, 45],
                    },
                },
            }
        }
    return override


@AgentServer.custom_action("DailyStaminaConfigureCustom")
class DailyStaminaConfigureCustom(CustomAction):
    def run(self, context, argv):
        param = safe_json_loads(argv.custom_action_param, {})
        if not isinstance(param, dict):
            return False
        if param.get("enabled") is False:
            return True
        if param.get("local_selection_missing") is True:
            logging.getLogger(__name__).error("本地活动或关卡已不可用，请重新选择目标")
            return False
        for node in (
            "DailyStaminaCustomInput",
            "DailyStaminaCustomTemplate",
        ):
            data = context.get_node_data(node)
            if not data or not isinstance(data.get("attach"), dict):
                logging.getLogger(__name__).error("自定义关卡配置节点缺失或无效: %s", node)
                return False
            param.update(data["attach"])
        try:
            override = build_custom_stamina_override(param)
        except (ValueError, TypeError) as exc:
            logging.getLogger(__name__).error("自定义关卡配置无效: %s", exc)
            return False
        return context.override_pipeline(override)


def _parse_stamina_text(text, *, require_ratio=False):
    normalized = re.sub(r"\s+", "", text).replace("\\", "/").replace("|", "/").replace("／", "/")
    match = (re.fullmatch if require_ratio else re.search)(r"(\d{1,4})/(\d{1,4})", normalized)
    if match:
        return int(match.group(1))
    if require_ratio:
        return None

    numbers = re.findall(r"\d+", normalized)
    if not numbers:
        return None
    if len(numbers) == 1:
        compact = numbers[0]
        for capacity in ("150", "50"):
            if len(compact) > len(capacity) and compact.endswith(capacity):
                return int(compact[: -len(capacity)])
        return int(compact)
    return int(numbers[0])


@AgentServer.custom_action("DailyStaminaOpenPotionRefill")
class DailyStaminaOpenPotionRefill(CustomAction):
    def run(self, context, argv):
        reading = next(
            (
                part for part in (argv.reco_detail.raw_detail or [])
                if part.get("name") == "DailyStaminaPresetStaminaLow"
            ),
            {},
        )
        texts = reading.get("detail", {}).get("best", {}).get("detail", {}).get("texts", [])
        stamina = _parse_stamina_text(" ".join(texts), require_ratio=True)
        if stamina is None:
            logging.getLogger(__name__).warning("用药前未读到完整体力数值，停止补充")
            return False

        if not context.override_pipeline({
            "__DailyStaminaPotionStaminaIncreased": {
                "recognition": {
                    "type": "Custom",
                    "param": {
                        "custom_recognition": "DailyStaminaCompare",
                        "custom_recognition_param": {
                            "cost": stamina + 1,
                            "require_ratio": True,
                            "stamina_roi": reading["box"],
                        },
                    },
                },
            },
        }):
            return False
        action = context.run_action_direct("Click", JClick(), box=argv.box)
        return bool(action and action.success)


@AgentServer.custom_recognition("DailyStaminaCompare")
class DailyStaminaCompare(CustomRecognition):
    def analyze(self, context, argv):
        param = safe_json_loads(argv.custom_recognition_param, {})
        mode = param.get("mode", "enough")
        cost = int(param.get("cost", 0))
        reserve = int(param.get("reserve", 0))
        roi = tuple(param.get("stamina_roi", [500, 0, 180, 45]))

        detail = context.run_recognition_direct(
            "OCR",
            JOCR(
                expected=[],
                roi=roi,
                threshold=0.3,
                only_rec=True,
            ),
            argv.image,
        )
        texts = []
        if detail:
            for result in detail.all_results:
                text = getattr(result, "text", "")
                if text:
                    texts.append(text)

        stamina = _parse_stamina_text(" ".join(texts), require_ratio=param.get("require_ratio", False))
        if stamina is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={
                    "reason": "stamina_parse_failed",
                    "texts": texts,
                    "mode": mode,
                    "cost": cost,
                    "reserve": reserve,
                },
            )

        enough = stamina >= cost + reserve
        hit = enough if mode == "enough" else not enough
        return CustomRecognition.AnalyzeResult(
            box=(roi[0], roi[1], roi[2], roi[3]) if hit else None,
            detail={
                "stamina": stamina,
                "cost": cost,
                "reserve": reserve,
                "mode": mode,
                "hit": hit,
                "texts": texts,
            },
        )

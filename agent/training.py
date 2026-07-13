import re

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


ITEMS = {
    "common": [
        {"name": "common_120", "value": 120, "box": (131, 1064, 107, 104), "count_roi": [131, 1119, 107, 45], "rare": False},
        {"name": "common_240", "value": 240, "box": (256, 1069, 95, 94), "count_roi": [256, 1124, 95, 39], "rare": False},
        {"name": "common_600", "value": 600, "box": (372, 1071, 90, 91), "count_roi": [372, 1126, 90, 36], "rare": False},
        {"name": "common_2400", "value": 2400, "box": (488, 1071, 90, 91), "count_roi": [488, 1126, 90, 36], "rare": True},
    ],
    "event": [
        {"name": "event_600_a", "value": 600, "box": (131, 1064, 107, 104), "count_roi": [131, 1119, 107, 45], "rare": False},
        {"name": "event_600_b", "value": 600, "box": (256, 1069, 95, 94), "count_roi": [256, 1124, 95, 39], "rare": False},
        {"name": "event_600_c", "value": 600, "box": (372, 1071, 90, 91), "count_roi": [372, 1126, 90, 36], "rare": False},
        {"name": "event_2000", "value": 2000, "box": (488, 1071, 90, 91), "count_roi": [488, 1126, 90, 36], "rare": True},
    ],
}


def _node_expected_value(context, node_name, default):
    node = context.get_node_data(node_name) or {}
    expected = node.get("recognition", {}).get("param", {}).get("expected", [])
    return expected[0] if expected else default


def _node_enabled(context, node_name, default):
    node = context.get_node_data(node_name)
    if not node:
        return default
    return bool(node.get("enabled", default))


def _read_config(context):
    return {
        "item_scope": _node_expected_value(context, "DailyTrainingConfigItemScope", "优先通用道具"),
        "allow_rare": _node_enabled(context, "DailyTrainingConfigAllowRare", False),
    }


def _ocr_texts(context, image, roi):
    detail = context.run_recognition_direct(
        "OCR",
        JOCR(expected=[], roi=tuple(roi), threshold=0.3, only_rec=True),
        image,
    )
    texts = []
    if detail:
        for result in detail.all_results:
            text = getattr(result, "text", "")
            if text:
                texts.append(text)
    return texts


def _parse_item_count(text):
    normalized = text.replace(",", "").replace(" ", "")
    numbers = re.findall(r"\d+", normalized)
    if not numbers:
        return None
    return int(numbers[-1])


def _read_item_count(context, image, item):
    roi = item.get("count_roi")
    if not roi:
        x, y, w, h = item["box"]
        roi = [x - 10, y + 55, w + 20, 45]
    texts = _ocr_texts(context, image, roi)
    return _parse_item_count(" ".join(texts)), texts


@AgentServer.custom_recognition("DailyTrainingChooseItem")
class DailyTrainingChooseItem(CustomRecognition):
    def analyze(self, context, argv):
        raw_param = argv.custom_recognition_param
        param = raw_param if isinstance(raw_param, dict) else safe_json_loads(raw_param, {})
        config = _read_config(context)
        tab = param.get("tab", "common")
        if tab not in ITEMS:
            tab = "common"
        tried = []

        for index, item in enumerate(ITEMS[tab]):
            if item["rare"] and not config["allow_rare"]:
                tried.append({"index": index, "item": item["name"], "skipped": "rare"})
                continue

            count, texts = _read_item_count(context, argv.image, item)
            tried.append({"index": index, "item": item["name"], "count": count, "texts": texts})
            if count is None or count > 0:
                return CustomRecognition.AnalyzeResult(
                    box=item["box"],
                    detail={
                        "tab": tab,
                        "item": item["name"],
                        "count": count,
                        "config": config,
                        "tried": tried,
                    },
                )

        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={
                "reason": "no_usable_item",
                "tab": tab,
                "config": config,
                "tried": tried,
            },
        )

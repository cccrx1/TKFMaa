from difflib import SequenceMatcher

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


SHOP_LIST_ROI = (60, 250, 600, 820)
SHOP_SLOTS = [
    {
        "name": "top_left",
        "name_roi": (75, 540, 165, 65),
        "sold_out_roi": (70, 430, 180, 115),
        "click_box": (75, 305, 170, 330),
    },
    {
        "name": "top_middle",
        "name_roi": (265, 540, 170, 65),
        "sold_out_roi": (260, 430, 180, 115),
        "click_box": (265, 305, 170, 330),
    },
    {
        "name": "top_right",
        "name_roi": (450, 540, 190, 65),
        "sold_out_roi": (440, 430, 190, 115),
        "click_box": (450, 305, 180, 330),
    },
    {
        "name": "bottom_left",
        "name_roi": (75, 905, 170, 65),
        "sold_out_roi": (70, 800, 180, 115),
        "click_box": (75, 675, 170, 330),
    },
    {
        "name": "bottom_middle",
        "name_roi": (265, 905, 170, 65),
        "sold_out_roi": (260, 800, 180, 115),
        "click_box": (265, 675, 170, 330),
    },
    {
        "name": "bottom_right",
        "name_roi": (450, 905, 190, 65),
        "sold_out_roi": (440, 800, 190, 115),
        "click_box": (450, 675, 180, 330),
    },
]

_LAST_TARGET_SIGNATURE = None
_HANDLED_ITEM_KEYS = set()
_PENDING_TARGET = None


def _is_word_char(ch):
    return ch.isalnum() or "\u4e00" <= ch <= "\u9fff"


def _normalize_text(text):
    return "".join(ch for ch in str(text or "") if _is_word_char(ch)).lower()


def _target_matches(target, item_text):
    """Allow explicit fragments and tolerate one-character OCR mistakes."""
    target = _normalize_text(target)
    item_text = _normalize_text(item_text)
    item_text = item_text.rstrip("0123456789")
    if not target or not item_text:
        return False

    shorter = min(len(target), len(item_text))
    if shorter >= 2 and (target in item_text or item_text in target):
        return True
    if shorter < 3:
        return False

    matcher = SequenceMatcher(None, target, item_text)
    longest = matcher.find_longest_match(0, len(target), 0, len(item_text)).size
    ratio = matcher.ratio()
    one_substitution = abs(len(target) - len(item_text)) <= 1 and ratio >= 0.66
    return one_substitution or (ratio >= 0.62 and longest >= 2)


def _split_targets(raw_targets):
    if isinstance(raw_targets, list):
        return raw_targets
    if not isinstance(raw_targets, str):
        return []

    targets = []
    current = []
    for ch in raw_targets:
        if _is_word_char(ch):
            current.append(ch)
        elif current:
            targets.append("".join(current))
            current = []
    if current:
        targets.append("".join(current))
    return targets


def _parse_targets(raw_targets):
    targets = []
    seen = set()
    for candidate in _split_targets(raw_targets):
        normalized = _normalize_text(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            targets.append({"raw": str(candidate), "normalized": normalized})
    return targets


def _reset_session(targets):
    global _LAST_TARGET_SIGNATURE, _HANDLED_ITEM_KEYS, _PENDING_TARGET

    signature = tuple(target["normalized"] for target in targets)
    if signature != _LAST_TARGET_SIGNATURE:
        _LAST_TARGET_SIGNATURE = signature
        _HANDLED_ITEM_KEYS = set()
        _PENDING_TARGET = None


def _ocr_results(context, image, roi, expected=None, threshold=0.3):
    detail = context.run_recognition_direct(
        "OCR",
        JOCR(expected=expected or [], roi=tuple(roi), threshold=threshold, only_rec=True),
        image,
    )
    return list(getattr(detail, "all_results", []) or [])


def _text_results(results):
    texts = []
    for result in results:
        text = getattr(result, "text", "")
        if text:
            texts.append(text)
    return texts


def _white_pixel_count(image, roi):
    x, y, w, h = [int(v) for v in roi]
    height, width = image.shape[:2]
    x1 = max(0, min(width, x))
    y1 = max(0, min(height, y))
    x2 = max(x1, min(width, x + w))
    y2 = max(y1, min(height, y + h))
    if x1 == x2 or y1 == y2:
        return 0

    region = image[y1:y2, x1:x2]
    # argv.image is BGR. The sold-out banner has large high-contrast white
    # letters; normal item cards only have small white quantity text here.
    bright = (region[:, :, 0] > 210) & (region[:, :, 1] > 210) & (region[:, :, 2] > 210)
    balanced = (region.max(axis=2) - region.min(axis=2)) < 45
    return int((bright & balanced).sum())


def _magenta_pixel_count(image, roi):
    x, y, w, h = [int(v) for v in roi]
    height, width = image.shape[:2]
    x1 = max(0, min(width, x))
    y1 = max(0, min(height, y))
    x2 = max(x1, min(width, x + w))
    y2 = max(y1, min(height, y + h))
    if x1 == x2 or y1 == y2:
        return 0

    region = image[y1:y2, x1:x2]
    blue = region[:, :, 0]
    green = region[:, :, 1]
    red = region[:, :, 2]
    magenta = (red > 90) & (blue > 70) & (green < 115) & (red > green + 25) & (blue > green + 5)
    return int(magenta.sum())


def _slot_texts(context, image, slot, expected):
    # Read the card text without expected filtering first. Expected filtering can
    # turn a small OCR error into an empty result before fuzzy matching sees it.
    results = _ocr_results(context, image, slot["name_roi"], threshold=0.2)
    if not results and expected:
        results = _ocr_results(context, image, slot["name_roi"], expected, threshold=0.2)
    return _text_results(results)


def _slot_sold_out(context, image, slot):
    texts = _text_results(
        _ocr_results(
            context,
            image,
            slot["sold_out_roi"],
            expected=["SOLD OUT", "SOLDOUT"],
            threshold=0.2,
        )
    )
    normalized = _normalize_text("".join(texts))
    white_count = _white_pixel_count(image, slot["sold_out_roi"])
    magenta_count = _magenta_pixel_count(image, slot["sold_out_roi"])
    # Color counts remain diagnostics only. Normal item cards can contain enough
    # bright lettering to resemble the banner, so purchase blocking requires OCR.
    return "soldout" in normalized, texts, white_count, magenta_count


def _read_visible_items(context, image, targets):
    expected = [target["raw"] for target in targets]
    visible = []
    for slot in SHOP_SLOTS:
        texts = _slot_texts(context, image, slot, expected)
        normalized = _normalize_text("".join(texts))
        sold_out, sold_out_texts, sold_out_white, sold_out_magenta = _slot_sold_out(context, image, slot)
        if not normalized and not sold_out_texts:
            continue
        visible.append(
            {
                "slot": slot["name"],
                "texts": texts,
                "text": "".join(texts),
                "normalized": normalized,
                "sold_out": sold_out,
                "sold_out_texts": sold_out_texts,
                "sold_out_white": sold_out_white,
                "sold_out_magenta": sold_out_magenta,
                "box": slot["click_box"],
            }
        )
    return visible


def _visible_signature(visible):
    return tuple((entry["slot"], entry["normalized"], entry["sold_out"]) for entry in visible)


def _item_key(shop_id, target, item, visible):
    return (shop_id, target["normalized"], item["slot"], _visible_signature(visible))


def _analyze_target_item(context, argv, default_shop_id):
    global _PENDING_TARGET

    raw_param = argv.custom_recognition_param
    param = raw_param if isinstance(raw_param, dict) else safe_json_loads(raw_param, {})
    targets = _parse_targets(param.get("target_names", param.get("targets", "")))
    shop_id = str(param.get("shop_id", default_shop_id))
    _reset_session([{"normalized": shop_id}, *targets])

    raw_targets = [target["raw"] for target in targets]
    visible = _read_visible_items(context, argv.image, targets)
    skipped = []

    for target in targets:
        normalized_target = target["normalized"]
        for item in visible:
            text = item["normalized"]
            if not text:
                continue
            if _target_matches(normalized_target, text):
                if item["sold_out"]:
                    skipped.append(
                        {
                            "target": target["raw"],
                            "slot": item["slot"],
                            "reason": "sold_out",
                            "texts": item["texts"],
                            "sold_out_texts": item["sold_out_texts"],
                            "sold_out_white": item["sold_out_white"],
                            "sold_out_magenta": item["sold_out_magenta"],
                        }
                    )
                    continue

                key = _item_key(shop_id, target, item, visible)
                if key in _HANDLED_ITEM_KEYS:
                    skipped.append(
                        {
                            "target": target["raw"],
                            "slot": item["slot"],
                            "reason": "already_handled",
                            "texts": item["texts"],
                        }
                    )
                    continue

                _PENDING_TARGET = key
                return CustomRecognition.AnalyzeResult(
                    box=item["box"],
                    detail={
                        "target": target["raw"],
                        "shop_id": shop_id,
                        "slot": item["slot"],
                        "visible": [entry["text"] for entry in visible],
                        "items": [
                            {
                                "slot": entry["slot"],
                                "text": entry["text"],
                                "sold_out": entry["sold_out"],
                                "sold_out_white": entry["sold_out_white"],
                                "sold_out_magenta": entry["sold_out_magenta"],
                            }
                            for entry in visible
                        ],
                        "targets": raw_targets,
                        "skipped": skipped,
                    },
                )

    return CustomRecognition.AnalyzeResult(
        box=None,
        detail={
            "reason": "no_target_visible",
            "shop_id": shop_id,
            "visible": [entry["text"] for entry in visible],
            "items": [
                {
                    "slot": entry["slot"],
                    "text": entry["text"],
                    "sold_out": entry["sold_out"],
                    "sold_out_white": entry["sold_out_white"],
                    "sold_out_magenta": entry["sold_out_magenta"],
                }
                for entry in visible
            ],
            "targets": raw_targets,
            "skipped": skipped,
        },
    )


@AgentServer.custom_action("DailyShopResetExchangeSession")
class DailyShopResetExchangeSession(CustomAction):
    def run(self, context, argv):
        global _LAST_TARGET_SIGNATURE, _HANDLED_ITEM_KEYS, _PENDING_TARGET
        _LAST_TARGET_SIGNATURE = None
        _HANDLED_ITEM_KEYS = set()
        _PENDING_TARGET = None
        return True


@AgentServer.custom_action("DailyShopMarkTargetPurchased")
class DailyShopMarkTargetPurchased(CustomAction):
    def run(self, context, argv):
        global _PENDING_TARGET
        if _PENDING_TARGET:
            _HANDLED_ITEM_KEYS.add(_PENDING_TARGET)
            _PENDING_TARGET = None
        return True


@AgentServer.custom_recognition("DailyShopExchangeTargetItem")
class DailyShopExchangeTargetItem(CustomRecognition):
    def analyze(self, context, argv):
        return _analyze_target_item(context, argv, "exchange")


@AgentServer.custom_recognition("DailyShopGuildTargetItem")
class DailyShopGuildTargetItem(CustomRecognition):
    def analyze(self, context, argv):
        return _analyze_target_item(context, argv, "guild")

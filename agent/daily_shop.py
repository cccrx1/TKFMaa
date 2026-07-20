from difflib import SequenceMatcher

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


SHOP_SLOTS = [
    {
        "name": "top_left",
        "card_roi": (70, 280, 182, 365),
        "click_box": (70, 280, 182, 365),
    },
    {
        "name": "top_middle",
        "card_roi": (255, 280, 180, 365),
        "click_box": (255, 280, 180, 365),
    },
    {
        "name": "top_right",
        "card_roi": (435, 280, 180, 365),
        "click_box": (435, 280, 180, 365),
    },
    {
        "name": "bottom_left",
        "card_roi": (70, 650, 182, 370),
        "click_box": (70, 650, 182, 370),
    },
    {
        "name": "bottom_middle",
        "card_roi": (255, 650, 180, 370),
        "click_box": (255, 650, 180, 370),
    },
    {
        "name": "bottom_right",
        "card_roi": (435, 650, 180, 370),
        "click_box": (435, 650, 180, 370),
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


def _ocr_results(context, image, roi, expected=None, threshold=0.3, *, only_rec=True):
    detail = context.run_recognition_direct(
        "OCR",
        JOCR(expected=expected or [], roi=tuple(roi), threshold=threshold, only_rec=only_rec),
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


def _longest_ascii_letter_run(text):
    longest = 0
    current = 0
    for ch in _normalize_text(text):
        if "a" <= ch <= "z":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _sold_out_texts(texts):
    normalized = _normalize_text("".join(texts))
    if "soldout" not in normalized and "currently" not in normalized and _longest_ascii_letter_run(normalized) < 3:
        return []

    markers = [text for text in texts if _longest_ascii_letter_run(text) >= 3]
    return markers or texts


def _slot_texts(context, image, slot):
    # One detection pass reads the item name and any sold-out banner from the
    # whole card. The ROI includes the 13-15 px shift between list endpoints.
    return _text_results(
        _ocr_results(context, image, slot["card_roi"], threshold=0.2, only_rec=False)
    )


def _read_visible_items(context, image, targets):
    visible = []
    for slot in SHOP_SLOTS:
        texts = _slot_texts(context, image, slot)
        normalized = _normalize_text("".join(texts))
        sold_out_texts = _sold_out_texts(texts)
        if not normalized:
            continue
        visible.append(
            {
                "slot": slot["name"],
                "texts": texts,
                "text": "".join(texts),
                "normalized": normalized,
                "normalized_texts": [_normalize_text(text) for text in texts],
                "sold_out": bool(sold_out_texts),
                "sold_out_texts": sold_out_texts,
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
            texts = item["normalized_texts"]
            if not texts:
                continue
            if any(_target_matches(normalized_target, text) for text in texts):
                if item["sold_out"]:
                    skipped.append(
                        {
                            "target": target["raw"],
                            "slot": item["slot"],
                            "reason": "sold_out",
                            "texts": item["texts"],
                            "sold_out_texts": item["sold_out_texts"],
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
                                "sold_out_texts": entry["sold_out_texts"],
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
                    "sold_out_texts": entry["sold_out_texts"],
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

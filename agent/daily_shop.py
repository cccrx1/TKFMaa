import re
import unicodedata
from dataclasses import dataclass

import numpy as np

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


PRIORITY_ITEMS = {
    "exchange": {"紧急录用证", "招募命令"},
    "guild": {"召唤契约", "魔晶石", "阿克色记录"},
}
TITLE_ROI = (78, 432, 375, 44)
SOLD_OUT = "sold_out"
UNCERTAIN = "uncertain"
NO_BANNER = "no_banner"
MAX_UNREAD_PROBES = 2
_MIDDLE = (0, 0, 1, 1)


@dataclass(frozen=True)
class Target:
    name: str
    priority: bool


@dataclass(frozen=True)
class Card:
    slot: int
    title: str
    box: tuple[int, int, int, int]
    stock: str = NO_BANNER

    @property
    def origin(self):
        return self.box[0] - 40, self.box[1] - 74


@dataclass(frozen=True)
class Pending:
    shop: str
    position: str
    card: Card
    target: Target
    match: str
    terms: tuple[int, int] | None = None

    @property
    def key(self):
        return (self.shop, self.position, self.card.slot)


_SHELVES = {}
_OUTCOMES = {}
_UNREAD_PROBES = {}
_PENDING = None
_VERIFIED_TITLE = ""
_DONE_SHOP = None
_SCAN_POSITION = "top"


def _params(raw):
    value = raw if isinstance(raw, dict) else safe_json_loads(raw, {})
    return value if isinstance(value, dict) else {}


def _normalize_text(text):
    return "".join(ch for ch in unicodedata.normalize("NFKC", str(text or "")) if ch.isalnum()).casefold()


def _parse_targets(raw, shop):
    if isinstance(raw, str):
        raw = re.findall(r"!?[^\W_]+", unicodedata.normalize("NFKC", raw))
    if not isinstance(raw, list):
        return ()
    targets = {}
    for entry in raw:
        entry = unicodedata.normalize("NFKC", str(entry)).strip()
        name = _normalize_text(entry)
        if len(name) < 2:
            continue
        priority = entry.startswith("!") or name in PRIORITY_ITEMS.get(shop, ())
        targets[name] = targets.get(name, False) or priority
    return tuple(Target(name, priority) for name, priority in targets.items())


def _ocr(context, image, roi, *, only_rec=True):
    detail = context.run_recognition_direct(
        "OCR", JOCR(roi=roi, threshold=0.3, only_rec=only_rec), image
    )
    return [result for result in (getattr(detail, "all_results", None) or []) if getattr(result, "text", "")]


def _list_state(image, shop):
    if not isinstance(image, np.ndarray) or image.shape != (1280, 720, 3):
        return None
    # The selected tab is cyan, and the light thumb spans ~388 px on the four-row list.
    # Reject shifted/longer layouts rather than using endpoint slot IDs on the wrong cards.
    x = 124 if shop == "exchange" else 482
    tab = image[195:222, x:x + 10].astype(np.int16)
    if not (np.median(tab[:, :, 0] - tab[:, :, 2]) > 45 and np.median(tab[:, :, 1]) > 100):
        return None
    rail = image[280:1048, 692:700]
    rows = np.flatnonzero(np.count_nonzero(np.min(rail, axis=2) >= 195, axis=1) >= 6) + 280
    if not (365 <= len(rows) <= 410 and rows[-1] - rows[0] + 1 <= len(rows) + 3):
        return None
    if rows[0] <= 291:
        return "top"
    if rows[-1] >= 1037:
        return "bottom"
    return "middle"


def _stock(context, image, x, y):
    node = "__DailyShopSoldOutBanner"
    roi = [x, y + 118, 170, 101]
    result = context.run_recognition(node, image, {node: {"recognition": {"param": {"roi": roi}}}})
    if result and result.hit:
        return SOLD_OUT
    if result is None or any(match.score >= 0.55 for match in (result.all_results or [])):
        return UNCERTAIN
    return NO_BANNER


def _slots(position):
    for row, y in enumerate((304, 675) if position == "top" else (291, 662)):
        for col, x in enumerate((78, 259, 440)):
            yield row * 3 + col, x, y


def _read_slot(context, image, slot, x, y):
    strip = image[y + 305:y + 327, x + 61:x + 102].astype(np.int16)
    if np.median(strip[:, :, 0] - strip[:, :, 2]) < 45:
        return None
    roi = (x, y + 264, 170, 33)
    results = _ocr(context, image, roi)
    title = _normalize_text(results[0].text) if results else ""
    if len(title) < 2:
        results = _ocr(context, image, roi, only_rec=False)
        title = _normalize_text(results[0].text) if results else ""
    return Card(slot, title, (x + 40, y + 74, 90, 140), _stock(context, image, x, y))


def _read_shelf(context, image, shop, position):
    shelf = _SHELVES.setdefault((shop, position), {})
    reads = 0
    for slot, x, y in _slots(position):
        # Title and price are stable; only the artwork and surrounding background animate.
        signature = image[y + 268:y + 328, x + 5:x + 166:2]
        if slot in shelf and np.mean(np.abs(shelf[slot][1] - signature)) < 3:
            continue
        shelf[slot] = (_read_slot(context, image, slot, x, y), signature.astype(np.int16))
        reads += 1
    return reads


def _one_edit(left, right):
    if min(len(left), len(right)) < 3 or abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return len(left) >= 4 and sum(a != b for a, b in zip(left, right)) == 1
    short, long = sorted((left, right), key=len)
    return any(short == long[:i] + long[i + 1:] for i in range(len(long)))


def _cards(shop, position):
    return [card for card, _ in _SHELVES.get((shop, position), {}).values() if card is not None]


def _match(card, target):
    if card.title == target.name:
        return "exact"
    if not target.priority and target.name in card.title:
        return "fragment"
    if _one_edit(card.title, target.name):
        return "weak"
    return None


def _unresolved_priority(shop, targets):
    sold = {c.title for pos in ("top", "bottom") for c in _cards(shop, pos) if c.stock == SOLD_OUT}
    checked = {title for key, (state, title) in _OUTCOMES.items() if key[0] == shop
               and state in ("purchased", "attempted")}
    return [t for t in targets if t.priority and t.name not in sold | checked]


def _select_card(shop, position, targets, *, priority):
    cards = [c for c in _cards(shop, position)
             if c.stock != SOLD_OUT and (shop, position, c.slot) not in _OUTCOMES]
    relevant = [t for t in targets if t.priority == priority]
    for rank in ("exact", "fragment", "weak"):
        for target in relevant:
            for card in cards:
                if _match(card, target) != rank:
                    continue
                if rank == "weak" and (
                    any(t.name == card.title for t in targets)
                    or sum(_match(card, t) == "weak" for t in relevant) != 1
                ):
                    continue
                return Pending(shop, position, card, target, rank)
    if priority and _UNREAD_PROBES.get(shop, 0) < MAX_UNREAD_PROBES:
        unresolved = _unresolved_priority(shop, targets)
        if len(unresolved) == 1:
            for card in cards:
                if len(card.title) < 2:
                    return Pending(shop, position, card, unresolved[0], "unread")
    return None


def _number(context, image, roi, *, only_rec=True):
    values = []
    for result in _ocr(context, image, roi, only_rec=only_rec):
        text = unicodedata.normalize("NFKC", result.text).replace(",", "").strip()
        match = re.fullmatch(r"[x×]?\s*([0-9]+)", text, flags=re.IGNORECASE)
        if match:
            values.append(int(match[1]))
    return values[0] if len(values) == 1 and values[0] > 0 else None


def _card_terms(context, image, card):
    x, y = card.origin
    price = _number(context, image, (x + 60, y + 302, 103, 33))
    quantity = _number(context, image, (x + 80, y + 188, 88, 33))
    return (price, quantity) if price and quantity else None


def _detail_terms_match(context, image, shop, terms):
    icon = image[752:776, 484:528].astype(np.int16)
    b, g, r = icon.transpose(2, 0, 1)
    color = (r - g > 65) & (r - b > 45) if shop == "exchange" else (g - r > 30) & (g - b > 20)
    if np.count_nonzero(color) < 20:
        return False
    price = _number(context, image, (529, 747, 98, 37))
    quantity = _number(context, image, (145, 609, 108, 46), only_rec=False)
    return (price, quantity) == terms


def _analyze_target_item(context, argv, shop):
    global _PENDING, _VERIFIED_TITLE, _DONE_SHOP
    _PENDING = None
    _VERIFIED_TITLE = ""
    _DONE_SHOP = None
    position = _SCAN_POSITION
    if _list_state(argv.image, shop) != position:
        return CustomRecognition.AnalyzeResult(box=None, detail={"reason": "unexpected_list_position"})

    params = _params(argv.custom_recognition_param)
    targets = _parse_targets(params.get("target_names", ""), shop)
    other = "bottom" if position == "top" else "top"
    reads = _read_shelf(context, argv.image, shop, position) if targets else 0
    other_scanned = (shop, other) in _SHELVES
    other_priority = _select_card(shop, other, targets, priority=True)
    while True:
        candidate = _select_card(shop, position, targets, priority=True)
        waiting_for_other = not other_scanned and bool(_unresolved_priority(shop, targets))
        if not candidate and not other_priority and not waiting_for_other:
            candidate = _select_card(shop, position, targets, priority=False)
        if not candidate:
            break
        card = candidate.card
        # Validate only the next candidate; a banner may have changed after a purchase.
        if _stock(context, argv.image, *card.origin) == SOLD_OUT:
            _, signature = _SHELVES[(shop, position)][card.slot]
            _SHELVES[(shop, position)][card.slot] = (Card(card.slot, card.title, card.box, SOLD_OUT), signature)
            continue
        duplicate = bool(card.title) and sum(
            c.title == card.title for pos in ("top", "bottom") for c in _cards(shop, pos)
        ) > 1
        terms = _card_terms(context, argv.image, card) if duplicate else None
        if duplicate and not terms:
            _OUTCOMES[candidate.key] = ("terms_unread", card.title)
            continue
        _PENDING = Pending(shop, position, card, candidate.target, candidate.match, terms)
        break
    if not _PENDING and (not targets or (
        other_scanned and not other_priority and not _select_card(shop, other, targets, priority=False)
    )):
        _DONE_SHOP = shop

    return CustomRecognition.AnalyzeResult(
        box=_PENDING.card.box if _PENDING else None,
        detail={
            "shop": shop,
            "position": position,
            "slot_reads": reads,
            "cards": [{"slot": c.slot, "title": c.title, "stock": c.stock} for c in _cards(shop, position)],
            "slot": _PENDING.card.slot if _PENDING else None,
            "candidate": _PENDING.target.name if _PENDING else None,
            "match": _PENDING.match if _PENDING else None,
            "terms": _PENDING.terms if _PENDING else None,
            "priority_unresolved": [t.name for t in _unresolved_priority(shop, targets)],
            "outcomes": [{"position": key[1], "slot": key[2], "status": status, "title": title}
                         for key, (status, title) in _OUTCOMES.items() if key[0] == shop],
            "done": _DONE_SHOP == shop,
        },
    )


def _detail_matches(pending, title):
    if pending.match == "fragment":
        return title == pending.card.title and pending.target.name in title
    return title == pending.target.name


@AgentServer.custom_action("DailyShopResetExchangeSession")
class DailyShopResetExchangeSession(CustomAction):
    def run(self, context, argv):
        global _PENDING, _VERIFIED_TITLE, _DONE_SHOP, _SCAN_POSITION
        _SHELVES.clear()
        _OUTCOMES.clear()
        _UNREAD_PROBES.clear()
        _PENDING = None
        _VERIFIED_TITLE = ""
        _DONE_SHOP = None
        _SCAN_POSITION = "top"
        return True


@AgentServer.custom_action("DailyShopSetScanPosition")
class DailyShopSetScanPosition(CustomAction):
    def run(self, context, argv):
        global _SCAN_POSITION, _PENDING, _VERIFIED_TITLE
        position = _params(argv.custom_action_param).get("position")
        if position not in ("top", "bottom"):
            return False
        _SCAN_POSITION = position
        _PENDING = None
        _VERIFIED_TITLE = ""
        return True


@AgentServer.custom_recognition("DailyShopListReady")
class DailyShopListReady(CustomRecognition):
    def analyze(self, context, argv):
        param = _params(argv.custom_recognition_param)
        shop = param.get("shop")
        position = _list_state(argv.image, shop) if shop in PRIORITY_ITEMS else None
        matched = position is not None and param.get("position", position) == position
        return CustomRecognition.AnalyzeResult(box=_MIDDLE if matched else None, detail={"position": position})


@AgentServer.custom_recognition("DailyShopShelfDone")
class DailyShopShelfDone(CustomRecognition):
    def analyze(self, context, argv):
        shop = _params(argv.custom_recognition_param).get("shop")
        matched = shop in PRIORITY_ITEMS and shop == _DONE_SHOP and _list_state(argv.image, shop) == _SCAN_POSITION
        return CustomRecognition.AnalyzeResult(box=_MIDDLE if matched else None, detail={"shop": shop, "done": matched})


@AgentServer.custom_action("DailyShopOpenTargetDetail")
class DailyShopOpenTargetDetail(CustomAction):
    def run(self, context, argv):
        if not _PENDING or _PENDING.key in _OUTCOMES or tuple(argv.box) != _PENDING.card.box:
            return False
        _OUTCOMES[_PENDING.key] = ("opened_unverified", _PENDING.card.title)
        if _PENDING.match == "unread":
            _UNREAD_PROBES[_PENDING.shop] = _UNREAD_PROBES.get(_PENDING.shop, 0) + 1
        result = context.run_action("__DailyShopPurchaseClick", box=argv.box)
        return bool(result and result.success)


@AgentServer.custom_recognition("DailyShopVerifyPurchaseDetail")
class DailyShopVerifyPurchaseDetail(CustomRecognition):
    def analyze(self, context, argv):
        global _VERIFIED_TITLE
        _VERIFIED_TITLE = ""
        if not _PENDING or _OUTCOMES.get(_PENDING.key, (None,))[0] != "opened_unverified":
            return CustomRecognition.AnalyzeResult(box=None, detail={"reason": "no_opened_candidate"})

        results = _ocr(context, argv.image, TITLE_ROI, only_rec=False)
        titles = {_normalize_text(r.text) for r in results if _normalize_text(r.text)}
        if _PENDING.target.priority and not titles:
            results += _ocr(context, argv.image, TITLE_ROI)
            titles = {_normalize_text(r.text) for r in results if _normalize_text(r.text)}
        if len(titles) == 1 and _detail_matches(_PENDING, next(iter(titles))):
            if not _PENDING.terms or _detail_terms_match(context, argv.image, _PENDING.shop, _PENDING.terms):
                _VERIFIED_TITLE = next(iter(titles))
        match = next((r for r in results if _VERIFIED_TITLE and _normalize_text(r.text) == _VERIFIED_TITLE), None)
        return CustomRecognition.AnalyzeResult(
            box=getattr(match, "box", None),
            detail={"matched": _VERIFIED_TITLE, "texts": [r.text for r in results]},
        )


@AgentServer.custom_action("DailyShopPurchaseOnce")
class DailyShopPurchaseOnce(CustomAction):
    def run(self, context, argv):
        if not _PENDING or not _VERIFIED_TITLE or _OUTCOMES.get(_PENDING.key, (None,))[0] != "opened_unverified":
            return False
        # Reserve before dispatch. An unconfirmed outcome never authorizes another click.
        _OUTCOMES[_PENDING.key] = ("attempted", _VERIFIED_TITLE)
        result = context.run_action("__DailyShopPurchaseClick", box=argv.box)
        return bool(result and result.success)


@AgentServer.custom_action("DailyShopMarkTargetPurchased")
class DailyShopMarkTargetPurchased(CustomAction):
    def run(self, context, argv):
        if _PENDING and _OUTCOMES.get(_PENDING.key, (None,))[0] == "attempted" and _VERIFIED_TITLE:
            _OUTCOMES[_PENDING.key] = ("purchased", _VERIFIED_TITLE)
        return True


@AgentServer.custom_recognition("DailyShopExchangeTargetItem")
class DailyShopExchangeTargetItem(CustomRecognition):
    def analyze(self, context, argv):
        return _analyze_target_item(context, argv, "exchange")


@AgentServer.custom_recognition("DailyShopGuildTargetItem")
class DailyShopGuildTargetItem(CustomRecognition):
    def analyze(self, context, argv):
        return _analyze_target_item(context, argv, "guild")

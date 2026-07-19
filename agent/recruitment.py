import itertools
import re

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


TAG_ROI = (95, 440, 530, 165)
REFRESH_ROI = (370, 610, 230, 70)
TAG_SLOT_ROIS = [
    (116, 463, 149, 51),
    (283, 462, 156, 54),
    (453, 466, 153, 47),
    (113, 533, 160, 54),
    (284, 538, 156, 53),
]
MAX_SELECTABLE_TAGS = 3
_LAST_RECRUIT_DECISION = None

RECRUITMENT_POOL = [
    {"name": "魔王 巴尔", "stars": 3, "tags": {"领袖", "火属性", "魔族", "中体型", "攻击者", "爆发力", "输出"}},
    {"name": "魔王 撒旦", "stars": 3, "tags": {"领袖", "闇属性", "魔族", "中体型", "守护者", "生存力", "回击", "巨乳", "防御", "保护"}},
    {"name": "精灵王 赛露西亚", "stars": 3, "tags": {"领袖", "风属性", "亚人", "中体型", "巨乳", "辅助者", "爆发力", "支援"}},
    {"name": "矮人王 兰儿", "stars": 3, "tags": {"领袖", "水属性", "亚人", "小体型", "贫乳", "攻击者", "爆发力", "越战越强", "输出"}},
    {"name": "法斯公主 露露", "stars": 3, "tags": {"领袖", "风属性", "人类", "治疗者", "回复"}},
    {"name": "魔王 伊布力斯", "stars": 3, "tags": {"领袖", "光属性", "魔族", "中体型", "攻击者", "生存力", "输出", "群体攻击"}},
    {"name": "古代勇者 乌鲁塔", "stars": 3, "tags": {"领袖", "风属性", "守护者", "人类", "中体型", "保护", "防御"}},
    {"name": "现代勇者 神田绫音", "stars": 3, "tags": {"领袖", "光属性", "攻击者", "人类", "爆发力", "输出", "中体型"}},
    {"name": "贤者 白", "stars": 3, "tags": {"领袖", "风属性", "治疗者", "亚人", "中体型", "支援", "回复"}},
    {"name": "毒蝎 莫默", "stars": 3, "tags": {"领袖", "水属性", "攻击者", "魔族", "中体型", "贫乳", "爆发力", "输出"}},
    {"name": "魔管家 艾可", "stars": 2, "tags": {"菁英", "闇属性", "魔族", "辅助者", "中体型", "美乳", "支援"}},
    {"name": "圣骑士长 雷欧娜", "stars": 2, "tags": {"菁英", "水属性", "人类", "守护者", "美乳", "中体型", "生存力", "保护", "防御"}},
    {"name": "神官长 菲欧菈", "stars": 2, "tags": {"菁英", "光属性", "人类", "治疗者", "美乳", "中体型", "回复"}},
    {"name": "女忍者 凛月", "stars": 2, "tags": {"菁英", "风属性", "人类", "攻击者", "美乳", "中体型", "输出", "群体攻击", "爆发力"}},
    {"name": "剑圣 神无雪", "stars": 2, "tags": {"菁英", "火属性", "亚人", "攻击者", "美乳", "中体型", "越战越强", "削弱"}},
    {"name": "妖狐 静", "stars": 2, "tags": {"菁英", "水属性", "美乳", "妨碍者", "亚人", "小体型", "削弱", "干扰"}},
    {"name": "大将军 朱诺安", "stars": 2, "tags": {"菁英", "闇属性", "人类", "攻击者", "巨乳", "中体型", "输出", "支援"}},
    {"name": "天才女军师 布兰妮", "stars": 2, "tags": {"菁英", "光属性", "人类", "妨碍者", "美乳", "中体型", "群体攻击", "削弱", "爆发力", "支援"}},
    {"name": "史莱姆女王 娜芙拉拉", "stars": 2, "tags": {"菁英", "风属性", "魔族", "守护者", "巨乳", "中体型", "保护", "防御", "生存力", "回复"}},
    {"name": "魔法少女 托特拉", "stars": 2, "tags": {"菁英", "光属性", "攻击者", "中体型", "人类", "爆发力", "美乳", "削弱", "输出"}},
    {"name": "最后的银龙 普利特拉", "stars": 2, "tags": {"菁英", "闇属性", "妨碍者", "亚人", "中体型", "削弱", "美乳"}},
    {"name": "刺针 嘉维尔", "stars": 2, "tags": {"菁英", "风属性", "攻击者", "美乳", "人类", "中体型", "输出"}},
    {"name": "精灵舞者 塔诺西雅", "stars": 2, "tags": {"菁英", "光属性", "辅助者", "亚人", "回复", "美乳", "中体型"}},
    {"name": "工会看板娘 小萤", "stars": 2, "tags": {"菁英", "水属性", "治疗者", "支援", "人类", "贫乳", "回复", "中体型"}},
    {"name": "流浪魔法师 尤依", "stars": 1, "tags": {"火属性", "攻击者", "人类", "巨乳", "小体型", "越战越强", "输出"}},
    {"name": "龙女 伊维斯", "stars": 1, "tags": {"火属性", "攻击者", "亚人", "贫乳", "小体型", "越战越强", "群体攻击", "输出"}},
    {"name": "猫妖 娜娜", "stars": 1, "tags": {"风属性", "攻击者", "魔族", "贫乳", "小体型", "输出"}},
    {"name": "美人鱼 玛莲", "stars": 1, "tags": {"水属性", "治疗者", "亚人", "美乳", "中体型", "回复"}},
    {"name": "犬人族 朵拉", "stars": 1, "tags": {"风属性", "守护者", "亚人", "美乳", "保护", "生存力", "中体型", "防御"}},
    {"name": "双蛇军团护士长 艾琳", "stars": 1, "tags": {"光属性", "治疗者", "人类", "巨乳", "中体型", "回复"}},
    {"name": "魅魔 撒芭丝", "stars": 1, "tags": {"闇属性", "妨碍者", "魔族", "美乳", "干扰", "削弱", "中体型"}},
    {"name": "闇黑精灵 索拉卡", "stars": 1, "tags": {"闇属性", "妨碍者", "亚人", "中体型", "削弱", "美乳"}},
    {"name": "白蔷薇 伊艾", "stars": 1, "tags": {"光属性", "治疗者", "人类", "贫乳", "小体型", "回复"}},
    {"name": "法斯帝国法师 佩托拉", "stars": 0, "tags": {"光属性", "攻击者", "人类", "贫乳", "中体型", "群体攻击", "输出", "士兵"}},
    {"name": "矮人战士 可儿", "stars": 0, "tags": {"水属性", "攻击者", "亚人", "贫乳", "小体型", "输出", "爆发力", "士兵"}},
    {"name": "精灵射手 奥菈", "stars": 0, "tags": {"风属性", "攻击者", "亚人", "美乳", "中体型", "输出", "士兵"}},
    {"name": "魔族法师 玛努艾拉", "stars": 0, "tags": {"闇属性", "攻击者", "中体型", "魔族", "美乳", "输出", "士兵"}},
    {"name": "烈日国武士 桔梗", "stars": 0, "tags": {"火属性", "妨碍者", "人类", "美乳", "中体型", "削弱", "士兵"}},
    {"name": "蛇女 拉米亚", "stars": 0, "tags": {"火属性", "妨碍者", "美乳", "中体型", "削弱", "干扰", "士兵"}},
    {"name": "史莱姆娘 萝尔", "stars": 0, "tags": {"水属性", "妨碍者", "魔族", "美乳", "小体型", "削弱", "生存力", "士兵", "回复"}},
    {"name": "鸟身女妖 哈比", "stars": 0, "tags": {"风属性", "妨碍者", "魔族", "美乳", "中体型", "干扰", "士兵"}},
    {"name": "法斯帝国士兵 赛莲", "stars": 0, "tags": {"闇属性", "守护者", "人类", "美乳", "中体型", "保护", "防御", "士兵"}},
    {"name": "牛女 米诺", "stars": 0, "tags": {"风属性", "守护者", "亚人", "巨乳", "中体型", "干扰", "保护", "防御", "生存力", "士兵"}},
    {"name": "魔族战士 芙蕾", "stars": 0, "tags": {"光属性", "守护者", "魔族", "美乳", "中体型", "保护", "士兵", "防御"}},
    {"name": "圣光骑士 玛蒂娜", "stars": 0, "tags": {"光属性", "守护者", "人类", "美乳", "中体型", "保护", "生存力", "防御", "士兵"}},
    {"name": "双蛇军团士兵 夏琳", "stars": 0, "tags": {"火属性", "守护者", "人类", "美乳", "中体型", "防御", "群体攻击", "保护", "士兵"}},
    {"name": "烈日国巫女 枫", "stars": 0, "tags": {"风属性", "治疗者", "人类", "美乳", "中体型", "回复", "士兵"}},
    {"name": "主神教团僧兵 克蕾雅", "stars": 0, "tags": {"光属性", "治疗者", "人类", "美乳", "中体型", "回复", "士兵"}},
    {"name": "试做机三号", "stars": 0, "tags": {"光属性", "攻击者", "小体型", "士兵", "美乳", "输出", "生存力"}},
    {"name": "法斯菁英近卫 安娜", "stars": 0, "tags": {"火属性", "守护者", "人类", "中体型", "防御", "士兵", "保护", "美乳"}},
    {"name": "法斯高阶法师 诺诺可", "stars": 0, "tags": {"水属性", "攻击者", "人类", "中体型", "美乳", "输出", "士兵", "爆发力"}},
    {"name": "法斯精锐骑士 布兰", "stars": 0, "tags": {"风属性", "攻击者", "人类", "中体型", "美乳", "输出", "防御", "士兵"}},
    {"name": "惩戒天使", "stars": 0, "tags": {"水属性", "守护者", "士兵", "生存力", "中体型", "回击", "群体攻击", "美乳", "亚人"}},
    {"name": "福音天使", "stars": 0, "tags": {"水属性", "治疗者", "士兵", "保护", "美乳", "中体型"}},
    {"name": "木乃伊 穆穆", "stars": 0, "tags": {"闇属性", "生存力", "妨碍者", "中体型", "保护", "干扰", "美乳"}},
    {"name": "人马 赛希", "stars": 0, "tags": {"风属性", "巨乳", "中体型", "攻击者", "亚人", "爆发力", "输出"}},
    {"name": "猎犬小队 茉莉", "stars": 0, "tags": {"水属性", "人类", "贫乳", "攻击者", "小体型", "士兵"}},
    {"name": "猎犬小队 安雅", "stars": 0, "tags": {"风属性", "妨碍者", "士兵", "人类"}},
]

KNOWN_TAGS = sorted({tag for item in RECRUITMENT_POOL for tag in item["tags"]}, key=len, reverse=True)


def _clean_text(text):
    text = re.sub(r"\s+", "", text or "")
    text = text.replace("暗属性", "闇属性").replace("间属性", "闇属性")
    text = text.replace("菁英", "菁英").replace("精英", "菁英")
    text = text.replace("防御者", "守护者")
    return text


def _tags_in_text(text):
    text = _clean_text(text)
    found = []
    for tag in KNOWN_TAGS:
        index = text.find(tag)
        if index >= 0:
            found.append((index, tag))
    found.sort(key=lambda item: item[0])
    return [tag for _, tag in found]


def _ocr_results(context, image, roi, *, only_rec=True):
    detail = context.run_recognition_direct(
        "OCR",
        JOCR(expected=[], roi=tuple(roi), threshold=0.3, only_rec=only_rec),
        image,
    )
    return list(getattr(detail, "all_results", []) or [])


def _intersects(a, b):
    ax, ay, aw, ah = [int(v) for v in list(a)]
    bx, by, bw, bh = [int(v) for v in list(b)]
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _slot_boxes_for_result(box, count):
    if count <= 1:
        return [box]
    matched = [slot for slot in TAG_SLOT_ROIS if _intersects(box, slot)]
    if len(matched) < count:
        matched = TAG_SLOT_ROIS
    if len(matched) > count:
        last = len(matched) - 1
        return [matched[round(last * index / (count - 1))] for index in range(count)]
    return matched[:count]


def _append_tag(tags, tag, box):
    if any(existing["tag"] == tag for existing in tags):
        return
    x, y, w, h = [int(v) for v in list(box)]
    center_box = [x + w // 2 - 8, y + h // 2 - 8, 16, 16]
    tags.append({"tag": tag, "box": center_box})


def _read_tags_by_slots(context, image):
    tags = []
    for roi in TAG_SLOT_ROIS:
        slot_tags = []
        for result in _ocr_results(context, image, roi):
            slot_tags.extend(_tags_in_text(getattr(result, "text", "")))
        for tag in slot_tags:
            _append_tag(tags, tag, roi)
            break
    return tags


def _read_tags_whole_roi(context, image, existing_tags):
    tags = list(existing_tags)
    known = {entry["tag"] for entry in tags}
    for result in _ocr_results(context, image, TAG_ROI, only_rec=False):
        box = getattr(result, "box", None)
        result_tags = _tags_in_text(getattr(result, "text", ""))
        if not result_tags or not box:
            continue
        tag_boxes = _slot_boxes_for_result(box, len(result_tags))
        for index, tag in enumerate(result_tags):
            if tag in known:
                continue
            tag_box = tag_boxes[min(index, len(tag_boxes) - 1)]
            _append_tag(tags, tag, tag_box)
            known.add(tag)
    return tags


def _read_visible_tags(context, image):
    return _read_tags_whole_roi(context, image, _read_tags_by_slots(context, image))


def _read_refresh_count(context, image):
    text = "".join(getattr(result, "text", "") for result in _ocr_results(context, image, REFRESH_ROI))
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _matches(combo):
    combo_set = set(combo)
    matches = []
    for item in RECRUITMENT_POOL:
        if item["stars"] == 3 and "领袖" not in combo_set:
            continue
        if combo_set.issubset(item["tags"]):
            matches.append(item)
    return matches


def _rank_combo(combo, matches):
    stars = [item["stars"] for item in matches]
    return {
        "tags": list(combo),
        "matches": [item["name"] for item in matches],
        "min_stars": min(stars),
        "max_stars": max(stars),
        "candidate_count": len(matches),
        "guaranteed_2_star": min(stars) >= 2,
    }


def _choose_combo(tags):
    available = [entry["tag"] for entry in tags]
    ranked = []
    max_size = min(MAX_SELECTABLE_TAGS, len(available))
    for size in range(max_size, 0, -1):
        for combo in itertools.combinations(available, size):
            matches = _matches(combo)
            if matches:
                ranked.append(_rank_combo(combo, matches))
    if not ranked:
        return None, []

    ranked.sort(
        key=lambda item: (
            item["guaranteed_2_star"],
            item["min_stars"],
            item["max_stars"],
            len(item["tags"]),
            -item["candidate_count"],
        ),
        reverse=True,
    )
    return ranked[0], ranked


def _decision(context, image):
    tags = _read_visible_tags(context, image)
    visible = [entry["tag"] for entry in tags]
    leader = "领袖" in visible
    refresh_count = _read_refresh_count(context, image)
    choice, ranked = _choose_combo(tags)

    if leader:
        action = "skip_leader"
    elif choice and choice["guaranteed_2_star"]:
        action = "recruit_guaranteed"
    elif refresh_count > 0:
        action = "refresh"
    else:
        action = "recruit_fallback"

    return {
        "action": action,
        "visible_tags": visible,
        "tag_boxes": {entry["tag"]: entry["box"] for entry in tags},
        "refresh_count": refresh_count,
        "choice": choice,
        "ranked": ranked[:8],
    }


def _tag_box(decision, index):
    choice = decision.get("choice")
    if not choice or index >= len(choice["tags"]):
        return None
    box = decision["tag_boxes"].get(choice["tags"][index])
    return tuple(box) if box else None


@AgentServer.custom_recognition("DailyRecruitDecision")
class DailyRecruitDecision(CustomRecognition):
    def analyze(self, context, argv):
        global _LAST_RECRUIT_DECISION

        raw_param = argv.custom_recognition_param
        param = raw_param if isinstance(raw_param, dict) else safe_json_loads(raw_param, {})
        mode = param.get("mode", "ready")
        decision = _decision(context, argv.image) if mode != "select_tag" else _LAST_RECRUIT_DECISION
        if not decision:
            decision = _decision(context, argv.image)
        box = None

        if mode in {"skip_leader", "refresh"}:
            _LAST_RECRUIT_DECISION = None

        if mode == decision["action"] or (mode == "recruit_fallback" and decision["action"] == "refresh"):
            box = (100, 400, 520, 280)
            if mode in {"recruit_guaranteed", "recruit_fallback"}:
                _LAST_RECRUIT_DECISION = decision
        elif mode == "select_tag":
            index = int(param.get("index", 0))
            if decision["action"] in {"recruit_guaranteed", "recruit_fallback", "refresh"}:
                box = _tag_box(decision, index)

        return CustomRecognition.AnalyzeResult(box=box, detail=decision)

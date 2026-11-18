"""Associate a duration button with its room; never navigate from Python."""

import json
import re
from hashlib import sha256

import numpy as np

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR


ROOMS = {
    "Bedroom": ("魔王寝室", "魔王寢室"),
    "Dungeon": ("地牢",),
    "Training": ("训练所", "訓練所"),
    "TreasureVault": ("宝藏库", "寶藏庫"),
    "SealRoom": ("封印密室",),
}


def duration_button_fractions(image, box):
    """Measure purple and light pixels inside the OCR-anchored button."""
    x, y, w, h = map(int, box)
    patch = image[max(220, y - 30):y + h + 5, max(145, x - 5):min(575, x + w + 5)]
    if patch.size == 0:
        return 0.0, 0.0
    b, g, r = [patch[:, :, i].astype(np.int16) for i in range(3)]
    purple = (b > g + 25) & (b > r + 20) & (g < 190)
    light = (b >= 170) & (g >= 170) & (r >= 170)
    return float(purple.mean()), float(light.mean())


@AgentServer.custom_recognition("DispatchDurationRecognition")
class DispatchDurationRecognition(CustomRecognition):
    def __init__(self):
        super().__init__()
        self._cache = {}

    def recognize(self, context, image, name, param=None):
        key = (sha256(image.tobytes()).digest(), name, repr(param))
        if key not in self._cache:
            if len(self._cache) >= 24:
                self._cache.clear()
            self._cache[key] = (
                context.run_recognition(name, image)
                if param is None
                else context.run_recognition_direct("OCR", param, image)
            )
        return self._cache[key]

    def analyze(self, context, argv):
        try:
            param = json.loads(argv.custom_recognition_param)
            if not isinstance(param, dict):
                raise ValueError("parameters must be an object")
            state = context.get_node_data("DailyDispatchSelectionState") or {}
            room = param.get("room") or state.get("attach", {}).get("room")
            names = ROOMS[room]
            hours = int(param["hours"])
            mode = param.get("mode", "any")
            if hours not in (6, 9, 12, 22) or mode not in ("any", "selected", "unselected"):
                raise ValueError("invalid duration/mode")
        except (ValueError, KeyError, TypeError):
            return self.miss("invalid_parameters")
        page = self.recognize(context, argv.image, "__DailyDispatchSelectionHeader")
        if not page or not page.hit:
            return self.miss("not_selection_page")
        title = self.recognize(
            context, argv.image, "room", JOCR(expected=list(names), roi=(140, 220, 440, 530))
        )
        if not title or not title.hit or title.box is None:
            return self.miss("room_not_visible")
        x, y, w, h = map(int, title.box)
        # Observed titles are 30-70px tall. The duration baseline is 85-165px
        # below the title top. Restrict the search before the next room card.
        top, bottom = y + h + 45, min(y + 185, 755)
        if top >= bottom or y + h + 100 > 765:
            return self.miss("room_buttons_clipped")
        result = self.recognize(
            context, argv.image, "duration", JOCR(expected=[r"(22|12|9|6)\s*(hrs|小時|小时)"],
                        roi=(150, top, 420, bottom - top))
        )
        candidates = []
        for item in getattr(result, "filtered_results", []) or []:
            text = re.sub(r"\s+", "", item.text or "")
            if not re.search(rf"(?<!\d){hours}(?:hrs|小時|小时)", text, re.I):
                continue
            box = list(map(int, item.box))
            if box[1] < 245 or box[1] + box[3] > 750:
                continue
            candidates.append(box)
        if len(candidates) != 1:
            return self.miss("ambiguous_or_missing_duration")
        box = candidates[0]
        purple, light = duration_button_fractions(argv.image, box)
        selected = purple >= 0.35
        # Locked durations keep their OCR text but use a dark gray background.
        # Only a recognized purple or light button may be selected or clicked.
        if not selected and light < 0.35:
            return self.miss("unavailable_button", room=room, hours=hours,
                             purple_fraction=purple, light_fraction=light)
        if mode == "selected" and not selected:
            return self.miss("not_selected", fraction=purple)
        if mode == "unselected" and selected:
            return self.miss("already_selected", fraction=purple)
        return CustomRecognition.AnalyzeResult(box=box, detail={
            "room": room, "hours": hours, "selected": selected,
            "purple_fraction": purple, "light_fraction": light, "room_box": [x, y, w, h],
        })

    @staticmethod
    def miss(reason, **detail):
        return CustomRecognition.AnalyzeResult(box=None, detail={"reason": reason, **detail})


@AgentServer.custom_action("DispatchSetRoom")
class DispatchSetRoom(CustomAction):
    """Only reset recognition context; navigation belongs to the Pipeline."""

    def run(self, context, argv):
        try:
            room = json.loads(argv.custom_action_param)["room"]
        except (ValueError, KeyError, TypeError):
            return False
        if not isinstance(room, str) or room not in ROOMS:
            return False
        return context.override_pipeline({"DailyDispatchSelectionState": {"attach": {"room": room}}})

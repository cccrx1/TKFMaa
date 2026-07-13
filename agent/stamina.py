import re

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JOCR

from common import safe_json_loads


def _parse_stamina_text(text):
    normalized = text.replace(" ", "").replace("\\", "/").replace("|", "/")
    match = re.search(r"(\d{1,4})/(\d{1,4})", normalized)
    if match:
        return int(match.group(1))

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

        stamina = _parse_stamina_text(" ".join(texts))
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

"""Check task postconditions on one screenshot without performing any action."""

import json

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition


@AgentServer.custom_recognition("TaskCompletionGuard")
class TaskCompletionGuard(CustomRecognition):
    def analyze(self, context, argv):
        param = argv.custom_recognition_param
        if isinstance(param, str):
            try:
                param = json.loads(param)
            except (ValueError, TypeError):
                param = None
        if not isinstance(param, dict):
            return self._miss("invalid_parameters")
        required, absent = param.get("required"), param.get("absent")
        if not isinstance(required, list) or not required or not isinstance(absent, list):
            return self._miss("invalid_parameters")
        if any(not isinstance(name, str) or not name or name == argv.node_name for name in required + absent):
            return self._miss("invalid_node_names")

        checks = []
        box = None
        for name, expected in [(name, True) for name in required] + [(name, False) for name in absent]:
            node = context.get_node_data(name)
            if not isinstance(node, dict) or not node or node.get("enabled") is False:
                return self._miss("unavailable_check", checks, name)
            result = context.run_recognition(name, argv.image)
            if result is None:
                return self._miss("recognition_unavailable", checks, name)
            checks.append({"node": name, "hit": bool(result.hit), "expected": expected})
            if bool(result.hit) != expected:
                return self._miss("required_missing" if expected else "remaining_target", checks, name)
            if box is None and expected:
                box = result.box
        if box is None:
            return self._miss("missing_page_box", checks)
        return CustomRecognition.AnalyzeResult(box=box, detail={"complete": True, "checks": checks})

    @staticmethod
    def _miss(reason, checks=None, node=None):
        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={"complete": False, "reason": reason, "node": node, "checks": checks or []},
        )

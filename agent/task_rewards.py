"""Allow a bounded daily-reward skip using evidence from the current task only."""

from bootstrap import configure_runtime

configure_runtime()

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition


DAILY_CLAIM = "DailyTaskRewardsClaimDailyAvailable"
DAILY_INVENTORY_POPUP = "DailyTaskRewardsCloseDailyInventoryFullPopup"
DAILY_PAGE_CHECK = "__DailyTaskRewardsDailyPageReady"
TABS = ("Daily", "Weekly", "Monthly", "Personal", "Activity", "Guild")
CLAIM_TABS = {f"DailyTaskRewardsClaim{tab}Available": tab for tab in TABS}
PAGE_TABS = {
    f"DailyTaskRewards{step}{tab}": tab for tab in TABS for step in ("Select", "Claim")
}
REWARD_POPUPS = {
    "DailyTaskRewardsCloseExpandedRewardPopup",
    "DailyTaskRewardsCloseCompactRewardPopup",
}


def _daily_inventory_evidence(nodes):
    attempts = 0
    inventory_popups = 0
    last_claim = None
    current_tab = None
    last_response_confirmed = False
    for node in nodes:
        if not node.completed:
            continue
        if node.name in PAGE_TABS:
            current_tab = PAGE_TABS[node.name]
        if node.name in CLAIM_TABS:
            last_claim = node.name
            current_tab = CLAIM_TABS[node.name]
            if node.name == DAILY_CLAIM:
                attempts += 1
                last_response_confirmed = False
        elif node.name == "DailyTaskRewardsCloseClaimPopup" and current_tab == "Daily":
            last_response_confirmed = False
        elif last_claim == DAILY_CLAIM and current_tab == "Daily":
            if node.name == DAILY_INVENTORY_POPUP:
                inventory_popups += 1
                last_response_confirmed = True
            elif node.name in REWARD_POPUPS:
                last_response_confirmed = True
    return {
        "attempts": attempts,
        "inventory_popups": inventory_popups,
        "last_response_confirmed": last_response_confirmed,
    }


@AgentServer.custom_recognition("DailyTaskRewardsInventorySkip")
class DailyTaskRewardsInventorySkip(CustomRecognition):
    def analyze(self, context, argv):
        claim = context.get_node_data(DAILY_CLAIM)
        limit = claim.get("max_hit") if isinstance(claim, dict) else None
        if (
            not isinstance(claim, dict)
            or claim.get("enabled") is False
            or type(limit) is not int
            or not 0 < limit <= 3
        ):
            return self._miss("invalid_claim_limit")

        nodes = getattr(argv.task_detail, "nodes", None)
        if nodes is None:
            return self._miss("unavailable_task_history")
        evidence = _daily_inventory_evidence(nodes)
        if evidence["attempts"] < limit:
            return self._miss("remaining_attempts", evidence)
        if not evidence["inventory_popups"]:
            return self._miss("no_daily_inventory_limit", evidence)
        if not evidence["last_response_confirmed"]:
            return self._miss("unconfirmed_last_response", evidence)

        page = context.get_node_data(DAILY_PAGE_CHECK)
        if not isinstance(page, dict) or not page or page.get("enabled") is False:
            return self._miss("unavailable_page_check", evidence)
        result = context.run_recognition(DAILY_PAGE_CHECK, argv.image)
        if result is None or not result.hit or result.box is None:
            return self._miss("daily_page_not_ready", evidence)
        return CustomRecognition.AnalyzeResult(
            box=result.box,
            detail={"status": "partial", "reason": "daily_inventory_limit", "limit": limit, **evidence},
        )

    @staticmethod
    def _miss(reason, evidence=None):
        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={"skip": False, "reason": reason, **(evidence or {})},
        )

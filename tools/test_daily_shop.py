"""Regression checks for missed-item recovery and shop session state."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
import daily_shop  # noqa: E402


class DailyShopTests(unittest.TestCase):
    def setUp(self):
        daily_shop.DailyShopResetExchangeSession().run(None, None)

    def set_position(self, position):
        daily_shop.DailyShopSetScanPosition().run(
            None, SimpleNamespace(custom_action_param={"position": position})
        )

    def choose(self, shop="exchange", title="安娜的记忆精粹", visible=True, sold_out=False):
        item = {
            "slot": "top_right",
            "texts": [title],
            "text": title,
            "normalized_texts": [daily_shop._normalize_text(title)],
            "sold_out": sold_out,
            "sold_out_texts": ["SOLD OUT"] if sold_out else [],
            "box": (435, 280, 180, 365),
        }
        argv = SimpleNamespace(
            custom_recognition_param={"shop_id": shop, "target_names": ["记忆精粹"]}, image=None
        )
        with patch.object(daily_shop, "_read_visible_items", return_value=[item] if visible else []):
            return daily_shop._analyze_target_item(None, argv, shop)

    def test_purchase_at_top_does_not_hide_a_bottom_item_in_the_same_screen_slot(self):
        self.assertIsNotNone(self.choose().box)
        daily_shop.DailyShopMarkTargetPurchased().run(None, None)
        self.set_position("bottom")
        self.assertIsNotNone(self.choose(title="诺诺可的记忆精粹").box)

    def test_second_pass_keeps_purchased_marks_across_shop_switches(self):
        self.assertIsNotNone(self.choose().box)
        daily_shop.DailyShopMarkTargetPurchased().run(None, None)
        self.assertIsNotNone(self.choose(shop="guild").box)
        daily_shop.DailyShopMarkVerificationPass().run(None, None)
        self.assertIsNone(self.choose().box)
        daily_shop.DailyShopResetExchangeSession().run(None, None)
        self.assertIsNotNone(self.choose().box)

    def test_a_first_pass_miss_is_eligible_on_the_second_pass(self):
        self.assertIsNone(self.choose(visible=False).box)
        daily_shop.DailyShopMarkVerificationPass().run(None, None)
        self.assertIsNotNone(self.choose().box)

    def test_opening_detail_without_purchase_does_not_mark_the_item_handled(self):
        self.assertIsNotNone(self.choose().box)
        self.assertIsNotNone(self.choose().box)
        self.assertIsNone(self.choose(sold_out=True).box)


if __name__ == "__main__":
    unittest.main()

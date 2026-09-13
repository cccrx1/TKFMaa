"""Regression checks for training inventory and consumption limits (no device required)."""

import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
import training  # noqa: E402


class TrainingTests(unittest.TestCase):
    def choose(self, counts, param=None, allow_rare=False):
        context = SimpleNamespace(
            get_node_data=lambda name: {"enabled": allow_rare} if name.endswith("AllowRare") else {}
        )
        argv = SimpleNamespace(custom_recognition_param=param, image=None)
        with patch.object(training, "_read_item_count", side_effect=[(n, []) for n in counts]):
            return training.DailyTrainingChooseItem().analyze(context, argv)

    def test_inventory_text_must_be_an_unambiguous_count(self):
        for text, count in [("778", 778), ("0", 0), ("1,234", 1234), ("× 12", 12), ("x5", 5)]:
            with self.subTest(text=text):
                self.assertEqual(training._parse_item_count(text), count)
        for text in ["", "???", "+120", "0.04%", "12 34", "1,23", "-1", "3/50"]:
            with self.subTest(text=text):
                self.assertIsNone(training._parse_item_count(text))

    def test_unreadable_slot_is_skipped_and_a_known_stock_is_used(self):
        result = self.choose([None, 0, 63])
        self.assertEqual(result.detail["item"], "common_600")
        self.assertEqual(result.detail["tried"][0]["skipped"], "unreadable_count")

    def test_unknown_or_empty_stock_never_selects_a_rare_item_by_default(self):
        for counts in [[None, None, None], [0, 0, 0]]:
            result = self.choose(counts)
            self.assertIsNone(result.box)
            self.assertEqual(result.detail["tried"][-1]["skipped"], "rare")

    def test_rare_requires_boolean_opt_in_and_positive_stock(self):
        result = self.choose([0, 0, 0, 231], allow_rare=True)
        self.assertEqual(result.detail["item"], "common_2400")
        self.assertIsNone(self.choose([0, 0, 0, None], allow_rare=True).box)
        self.assertIsNone(self.choose([0, 0, 0], allow_rare="false").box)

    def test_invalid_parameters_do_not_select_a_default_item(self):
        for param in ["[]", "broken json", 42, {"tab": []}, {"tab": "unknown"}]:
            with self.subTest(param=param):
                self.assertIsNone(self.choose([], param=param).box)

    def test_zero_and_positive_points_are_disjoint(self):
        pipeline = json.loads((ROOT / "assets/resource/pipeline/daily_training.json").read_text(encoding="utf-8"))
        positive = pipeline["__DailyTrainingMainHasCount"]["recognition"]["param"]["expected"]
        zero = pipeline["__DailyTrainingMainZeroCount"]["recognition"]["param"]["expected"]
        for text in ["0/50", "00 / 50", "10/50", "35 / 50", "50/50", "invalid"]:
            p = any(re.search(pattern, text) for pattern in positive)
            z = any(re.search(pattern, text) for pattern in zero)
            self.assertFalse(p and z, text)
            self.assertEqual(p, text in ["10/50", "35 / 50", "50/50"])
            self.assertEqual(z, text in ["0/50", "00 / 50"])

    def test_input_limits_node_hits_instead_of_blind_click_repeats(self):
        interface = json.loads((ROOT / "assets/interface.json").read_text(encoding="utf-8"))
        override = interface["option"]["指定调教次数"]["pipeline_override"]["DailyTrainingClickCenterSlow"]
        self.assertEqual(override, {"max_hit": "{次数}"})
        pipeline = json.loads((ROOT / "assets/resource/pipeline/daily_training.json").read_text(encoding="utf-8"))
        node = pipeline["DailyTrainingClickCenterSlow"]
        self.assertNotIn("repeat", node)
        self.assertLess(node["next"].index("DailyTrainingCloseShortagePopup"), node["next"].index("DailyTrainingClickCenterSlow"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExperimentConfigTests(unittest.TestCase):
    def test_state_sizes_and_paired_pilot_seeds_are_configured(self) -> None:
        config = json.loads(
            (ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig")
        )
        self.assertEqual(config["state_modes"]["simple"]["dimension"], 3)
        self.assertEqual(config["state_modes"]["rich"]["dimension"], 9)
        self.assertEqual(config["state_scales"]["simple"], [20.0, 20.0, 1.0])
        self.assertEqual(config["state_scales"]["rich"][:3], [20.0, 20.0, 1.0])
        self.assertEqual(config["training"]["episodes"], 20)
        self.assertEqual(config["training"]["seed_start"], 42)
        self.assertEqual(config["evaluation"]["seeds"], [100, 101, 102])
        self.assertEqual(config["action_meanings"]["0"], "keep_current_green_axis")
        self.assertEqual(config["action_meanings"]["1"], "request_other_green_axis")


if __name__ == "__main__":
    unittest.main()

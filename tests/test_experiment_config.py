from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExperimentConfigTests(unittest.TestCase):
    def test_state_sizes_and_high_demand_experiment_are_configured(self) -> None:
        config = json.loads(
            (ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig")
        )
        self.assertEqual(config["state_modes"]["simple"]["dimension"], 3)
        self.assertEqual(config["state_modes"]["rich"]["dimension"], 9)
        self.assertEqual(config["state_scales"]["simple"], [20.0, 20.0, 1.0])
        self.assertEqual(config["state_scales"]["rich"][:3], [20.0, 20.0, 1.0])
        self.assertEqual(config["training"]["episodes"], 160)
        self.assertEqual(config["training"]["seed_start"], 42)
        self.assertEqual(config["evaluation"]["seeds"], list(range(300, 310)))
        self.assertEqual(config["vehicles_per_hour_per_approach"], 900)
        training_seeds = set(
            range(
                config["training"]["seed_start"],
                config["training"]["seed_start"] + config["training"]["episodes"],
            )
        )
        self.assertTrue(training_seeds.isdisjoint(config["evaluation"]["seeds"]))
        self.assertEqual(config["action_meanings"]["0"], "keep_current_green_axis")
        self.assertEqual(config["action_meanings"]["1"], "request_other_green_axis")

    def test_route_flows_match_shared_high_demand_setting(self) -> None:
        config = json.loads(
            (ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig")
        )
        root = ET.parse(ROOT / "simulation" / "routes.rou.xml").getroot()
        flows = root.findall("flow")
        self.assertEqual(len(flows), 4)
        self.assertEqual(
            {int(flow.attrib["vehsPerHour"]) for flow in flows},
            {config["vehicles_per_hour_per_approach"]},
        )


if __name__ == "__main__":
    unittest.main()

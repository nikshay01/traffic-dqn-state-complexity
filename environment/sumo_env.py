"""Small TraCI environment for the verified single-intersection pilot."""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

import traci


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SumoEnvironment:
    """Control one SUMO intersection using the project's shared contract."""

    def __init__(self, config_path: str | Path = "simulation/config.sumocfg") -> None:
        self.project_root = PROJECT_ROOT
        self.experiment = json.loads(
            (self.project_root / "config" / "experiment.json").read_text(encoding="utf-8-sig")
        )
        self.sumo_config_path = Path(config_path)
        if not self.sumo_config_path.is_absolute():
            self.sumo_config_path = self.project_root / self.sumo_config_path
        if not self.sumo_config_path.is_file():
            raise FileNotFoundError(f"SUMO config not found: {self.sumo_config_path}")

        manifest_path = self.project_root / self.experiment["network_manifest"]
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if self.manifest.get("verified") is not True:
            raise ValueError(f"Network manifest is not verified: {manifest_path}")

        self.traffic_light_id = self.manifest["traffic_light_id"]
        self.phase_program_id = str(self.manifest["phase_program_id"])
        self.green_phases = {
            int(self.manifest["green_phase_indices"]["north_south"]): "north_south",
            int(self.manifest["green_phase_indices"]["east_west"]): "east_west",
        }
        if len(self.green_phases) != 2:
            raise ValueError("North-south and east-west green phases must be different")

        lanes = self.manifest["incoming_lanes"]
        self.axis_lanes = {
            "north_south": list(lanes["north"]) + list(lanes["south"]),
            "east_west": list(lanes["east"]) + list(lanes["west"]),
        }
        if any(not group for group in self.axis_lanes.values()):
            raise ValueError("The network manifest must list incoming lanes for both axes")

        self.clearance_phases = self.manifest["clearance_phase_indices_by_switch"]
        self.decision_interval = float(self.experiment["decision_interval_seconds"])
        self.step_length = float(self.experiment["simulation_step_seconds"])
        self.episode_end = float(self.experiment["episode_end_seconds"])
        self.steps_per_decision = round(self.decision_interval / self.step_length)
        if self.steps_per_decision < 1 or not math.isclose(
            self.steps_per_decision * self.step_length, self.decision_interval
        ):
            raise ValueError("Decision interval must be a positive multiple of SUMO step length")

        self.sumo_binary = self._find_sumo_binary()
        self._started = False
        self._arrived_vehicles = 0
        self._episode_queue_sum = 0.0
        self._episode_sim_steps = 0

    @staticmethod
    def _find_sumo_binary() -> str:
        sumo_home = os.environ.get("SUMO_HOME")
        if not sumo_home:
            try:
                import sumo

                sumo_home = sumo.SUMO_HOME
            except (ImportError, AttributeError):
                sumo_home = None
        if sumo_home:
            bin_dir = Path(sumo_home) / "bin"
            for filename in ("sumo.exe", "sumo"):
                candidate = bin_dir / filename
                if candidate.is_file():
                    return str(candidate)
        binary = shutil.which("sumo")
        if binary:
            return binary
        raise FileNotFoundError(
            "SUMO executable not found. Activate this project's .venv and set SUMO_HOME, "
            "or install SUMO and add its bin folder to PATH."
        )

    def reset(self, seed: int | None = None) -> None:
        if self._started:
            self.close()
        chosen_seed = self.experiment["pilot_seed"] if seed is None else seed
        traci.start(
            [
                self.sumo_binary,
                "-c",
                str(self.sumo_config_path),
                "--seed",
                str(chosen_seed),
            ]
        )
        self._started = True
        self._arrived_vehicles = 0
        self._episode_queue_sum = 0.0
        self._episode_sim_steps = 0

        traffic_lights = set(traci.trafficlight.getIDList())
        if self.traffic_light_id not in traffic_lights:
            self.close()
            raise ValueError(f"Traffic light from manifest is missing in SUMO: {self.traffic_light_id}")
        if traci.trafficlight.getProgram(self.traffic_light_id) != self.phase_program_id:
            self.close()
            raise ValueError("SUMO loaded a different traffic-light program than the manifest")
        actual_lanes = set(traci.lane.getIDList())
        missing_lanes = sorted(
            lane for group in self.axis_lanes.values() for lane in group if lane not in actual_lanes
        )
        if missing_lanes:
            self.close()
            raise ValueError(f"Incoming lanes from manifest are missing in SUMO: {missing_lanes}")
        self._axis_for_current_phase()

    def get_state(self, mode: str = "simple") -> list[float]:
        self._require_running()
        if mode not in ("simple", "rich"):
            raise ValueError("mode must be 'simple' or 'rich'")
        axis = self._axis_for_current_phase()

        ns_queue, ew_queue = self._queue_totals()
        green_axis = 0.0 if axis == "north_south" else 1.0
        state = [float(ns_queue), float(ew_queue), green_axis]
        if mode == "rich":
            ns_lanes = self.axis_lanes["north_south"]
            ew_lanes = self.axis_lanes["east_west"]
            state.extend(
                [
                    self._waiting_total(ns_lanes),
                    self._waiting_total(ew_lanes),
                    self._mean_lane_value(ns_lanes, traci.lane.getLastStepMeanSpeed),
                    self._mean_lane_value(ew_lanes, traci.lane.getLastStepMeanSpeed),
                    self._mean_lane_value(ns_lanes, traci.lane.getLastStepOccupancy) / 100.0,
                    self._mean_lane_value(ew_lanes, traci.lane.getLastStepOccupancy) / 100.0,
                ]
            )
        if not all(math.isfinite(value) for value in state):
            raise ValueError(f"State contains a non-finite value: {state}")
        return state

    def step(self, action: int, mode: str = "simple") -> tuple[list[float], float, bool, dict[str, Any]]:
        self._require_running()
        if action not in (0, 1):
            raise ValueError("action must be 0 (keep axis) or 1 (request the other axis)")
        phase_before = int(traci.trafficlight.getPhase(self.traffic_light_id))
        axis_before = self._axis_for_current_phase()
        target_axis = axis_before if action == 0 else self._other_axis(axis_before)
        target_phase = next(phase for phase, axis in self.green_phases.items() if axis == target_axis)

        if action == 0:
            traci.trafficlight.setPhaseDuration(
                self.traffic_light_id, self.decision_interval + self.step_length
            )
        else:
            transition_key = (
                "north_south_to_east_west"
                if axis_before == "north_south"
                else "east_west_to_north_south"
            )
            transition = self.clearance_phases[transition_key]
            if not transition:
                raise ValueError(f"No verified clearance phase is configured for {transition_key}")
            traci.trafficlight.setPhase(self.traffic_light_id, int(transition[0]))

        queue_samples: list[float] = []
        elapsed = 0.0
        for _ in range(self.steps_per_decision):
            if traci.simulation.getTime() >= self.episode_end:
                break
            traci.simulationStep()
            elapsed += self.step_length
            ns_queue, ew_queue = self._queue_totals()
            total_queue = float(ns_queue + ew_queue)
            queue_samples.append(total_queue)
            self._episode_queue_sum += total_queue
            self._episode_sim_steps += 1
            self._arrived_vehicles += int(traci.simulation.getArrivedNumber())

        phase_after = int(traci.trafficlight.getPhase(self.traffic_light_id))
        done = traci.simulation.getTime() >= self.episode_end
        axis_after = self._axis_for_current_phase()
        if axis_after != target_axis:
            raise RuntimeError(
                f"Signal did not reach the requested legal green axis: "
                f"expected {target_axis} at phase {target_phase}, got {axis_after} at phase {phase_after}"
            )
        reward = -sum(queue_samples) / len(queue_samples) if queue_samples else 0.0
        observation = self.get_state(mode)
        info: dict[str, Any] = {
            "phase_before": phase_before,
            "phase_after": phase_after,
            "axis_before": axis_before,
            "axis_after": axis_after,
            "elapsed_simulation_s": elapsed,
            "mean_total_queue_vehicles": -reward,
            "arrived_vehicles_this_step": self._arrived_vehicles,
        }
        return observation, float(reward), bool(done), info

    def close(self) -> None:
        if self._started:
            try:
                traci.close()
            finally:
                self._started = False

    def _axis_for_current_phase(self) -> str:
        phase = int(traci.trafficlight.getPhase(self.traffic_light_id))
        if phase not in self.green_phases:
            raise RuntimeError(
                f"Observation requested during non-green phase {phase}; "
                "the verified signal program or decision interval may have changed"
            )
        return self.green_phases[phase]

    def _queue_totals(self) -> tuple[int, int]:
        ns_queue = sum(
            int(traci.lane.getLastStepHaltingNumber(lane))
            for lane in self.axis_lanes["north_south"]
        )
        ew_queue = sum(
            int(traci.lane.getLastStepHaltingNumber(lane))
            for lane in self.axis_lanes["east_west"]
        )
        return ns_queue, ew_queue

    @staticmethod
    def _waiting_total(lanes: list[str]) -> float:
        return float(sum(float(traci.lane.getWaitingTime(lane)) for lane in lanes))

    @staticmethod
    def _mean_lane_value(lanes: list[str], getter: Any) -> float:
        if not lanes:
            return 0.0
        return float(sum(float(getter(lane)) for lane in lanes) / len(lanes))

    @staticmethod
    def _other_axis(axis: str) -> str:
        return "east_west" if axis == "north_south" else "north_south"

    def _require_running(self) -> None:
        if not self._started:
            raise RuntimeError("Call reset() before using the SUMO environment")

    def __enter__(self) -> "SumoEnvironment":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

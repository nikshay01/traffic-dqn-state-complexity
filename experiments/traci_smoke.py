"""Executable smoke check for the SUMO + TraCI environment contract."""

from __future__ import annotations

import math

from environment.sumo_env import SumoEnvironment


def main() -> None:
    env = SumoEnvironment()
    try:
        env.reset(seed=42)
        simple = env.get_state("simple")
        rich = env.get_state("rich")
        assert len(simple) == 3, f"simple state length was {len(simple)}"
        assert len(rich) == 9, f"rich state length was {len(rich)}"
        assert all(math.isfinite(value) for value in simple + rich)

        switched_state, switch_reward, done, switch_info = env.step(1, mode="rich")
        assert len(switched_state) == 9
        assert switch_info["axis_before"] != switch_info["axis_after"]
        assert switch_info["elapsed_simulation_s"] == 15.0
        assert not done

        held_state, hold_reward, done, hold_info = env.step(0, mode="simple")
        assert len(held_state) == 3
        assert hold_info["axis_before"] == hold_info["axis_after"]
        assert hold_info["elapsed_simulation_s"] == 15.0
        assert not done

        print("SUMO/TraCI smoke run passed")
        print(f"simple state length: {len(simple)}")
        print(f"rich state length: {len(rich)}")
        print(
            "switch action: phase "
            f"{switch_info['phase_before']} -> {switch_info['phase_after']}, "
            f"axis {switch_info['axis_before']} -> {switch_info['axis_after']}, "
            f"reward {switch_reward:.3f}"
        )
        print(
            "hold action: phase "
            f"{hold_info['phase_before']} -> {hold_info['phase_after']}, "
            f"axis {hold_info['axis_before']} -> {hold_info['axis_after']}, "
            f"reward {hold_reward:.3f}"
        )
    finally:
        env.close()


if __name__ == "__main__":
    main()

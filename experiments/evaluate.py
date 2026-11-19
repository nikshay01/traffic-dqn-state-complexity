"""Evaluate saved DQNs against reproducible random and fixed-time controllers."""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path
from typing import Callable

import torch

from agents import DQNAgent
from environment.sumo_env import SumoEnvironment


ROOT = Path(__file__).resolve().parents[1]
CSV_FIELDS = [
    "seed",
    "agent",
    "state_mode",
    "episode",
    "episode_return",
    "mean_wait_s",
    "mean_queue_vehicles",
    "throughput_vehicles",
    "simulated_seconds",
    "wall_time_seconds",
]


def read_config() -> dict:
    return json.loads((ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig"))


def make_agent(mode: str, seed: int, config: dict, device: str, checkpoint: Path) -> DQNAgent:
    dqn = dict(config["dqn"])
    dqn.pop("device", None)
    agent = DQNAgent(
        state_dim=config["state_modes"][mode]["dimension"],
        action_dim=2,
        seed=seed,
        device=device,
        state_scales=config["state_scales"][mode],
        **dqn,
    )
    agent.load(checkpoint)
    return agent


def run_episode(
    *,
    env: SumoEnvironment,
    state_mode: str,
    seed: int,
    agent_name: str,
    episode: int,
    action_picker: Callable[[list[float], int], int],
) -> dict:
    tripinfo = ROOT / "results" / f"tripinfo_eval_{agent_name}_{state_mode}_seed{seed}.xml"
    started = time.perf_counter()
    env.reset(seed=seed, tripinfo_path=tripinfo)
    state = env.get_state(state_mode)
    episode_return = 0.0
    decision = 0
    while True:
        action = action_picker(state, decision)
        state, reward, done, _info = env.step(action, mode=state_mode)
        episode_return += reward
        decision += 1
        if done:
            break
    env.close()
    return {
        "seed": seed,
        "agent": agent_name,
        "state_mode": state_mode,
        "episode": episode,
        "episode_return": f"{episode_return:.6f}",
        **env.get_episode_metrics(),
        "wall_time_seconds": f"{time.perf_counter() - started:.3f}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, help="override shared evaluation seeds")
    parser.add_argument("--device", default="auto", help="auto, cpu, or cuda")
    parser.add_argument("--output", type=Path, help="CSV destination (default from shared config)")
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=ROOT / "results" / "checkpoints",
        help="directory containing dqn_simple.pt and dqn_rich.pt",
    )
    args = parser.parse_args()

    config = read_config()
    seeds = args.seeds or config["evaluation"]["seeds"]
    output_csv = args.output or ROOT / config["evaluation_csv"]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)

    rows: list[dict] = []
    env = SumoEnvironment(config_path=config["sumo_config"])
    try:
        dqn_agents = {
            mode: make_agent(
                mode,
                seed=int(seeds[0]),
                config=config,
                device=args.device,
                checkpoint=args.checkpoint_dir / f"dqn_{mode}.pt",
            )
            for mode in ("simple", "rich")
        }
        for episode, seed in enumerate(seeds, start=1):
            for mode, agent in dqn_agents.items():
                rows.append(
                    run_episode(
                        env=env,
                        state_mode=mode,
                        seed=seed,
                        agent_name="DQN",
                        episode=episode,
                        action_picker=lambda state, _step, current=agent: current.select_action(
                            state, training=False
                        ),
                    )
                )

            rng = random.Random(seed)
            rows.append(
                run_episode(
                    env=env,
                    state_mode="simple",
                    seed=seed,
                    agent_name="random",
                    episode=episode,
                    action_picker=lambda _state, _step, generator=rng: generator.randrange(2),
                )
            )
            interval = int(config["evaluation"]["fixed_time_switch_every_decisions"])
            rows.append(
                run_episode(
                    env=env,
                    state_mode="simple",
                    seed=seed,
                    agent_name=f"fixed_time_{interval}decision",
                    episode=episode,
                    action_picker=lambda _state, step, n=interval: int((step + 1) % n == 0),
                )
            )
    finally:
        env.close()

    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} evaluation episodes to {output_csv}")
    for row in rows:
        waiting = row["mean_wait_s"]
        waiting_text = "n/a" if waiting is None else f"{waiting:.3f}"
        print(
            f"{row['agent']:24s} mode={row['state_mode']:6s} seed={row['seed']} "
            f"return={float(row['episode_return']):.3f} "
            f"mean_queue={row['mean_queue_vehicles']:.3f} "
            f"mean_wait_completed={waiting_text} "
            f"throughput={row['throughput_vehicles']}"
        )


if __name__ == "__main__":
    main()

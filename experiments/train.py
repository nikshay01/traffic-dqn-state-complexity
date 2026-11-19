"""Train one DQN for each frozen observation representation."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

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


def load_config() -> dict:
    return json.loads((ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig"))


def create_agent(mode: str, seed: int, config: dict, device: str) -> DQNAgent:
    dqn = dict(config["dqn"])
    dqn.pop("device", None)
    return DQNAgent(
        state_dim=config["state_modes"][mode]["dimension"],
        action_dim=2,
        seed=seed,
        device=device,
        state_scales=config["state_scales"][mode],
        **dqn,
    )


def train_mode(
    mode: str,
    episodes: int,
    seed_start: int,
    device: str,
    config: dict,
    output_csv: Path,
) -> Path:
    agent = create_agent(mode, seed_start, config, device)
    env = SumoEnvironment(config_path=config["sumo_config"])
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_csv.exists() or output_csv.stat().st_size == 0
    checkpoint_path = ROOT / "results" / "checkpoints" / f"dqn_{mode}.pt"

    with output_csv.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
            csv_file.flush()
        try:
            for episode_index in range(episodes):
                seed = seed_start + episode_index
                tripinfo = (
                    ROOT
                    / "results"
                    / f"tripinfo_train_{mode}_ep{episode_index + 1:03d}_seed{seed}.xml"
                )
                start_time = time.perf_counter()
                env.reset(seed=seed, tripinfo_path=tripinfo)
                state = env.get_state(mode)
                episode_return = 0.0
                decision = 0
                while True:
                    action = agent.select_action(state, training=True)
                    next_state, reward, done, _info = env.step(action, mode=mode)
                    agent.remember(state, action, reward, next_state, done)
                    if len(agent.replay_buffer) >= config["training"]["learning_starts"]:
                        agent.train_step()
                    episode_return += reward
                    state = next_state
                    decision += 1
                    if done:
                        break

                env.close()
                metrics = env.get_episode_metrics()
                row = {
                    "seed": seed,
                    "agent": "DQN",
                    "state_mode": mode,
                    "episode": episode_index + 1,
                    "episode_return": f"{episode_return:.6f}",
                    **metrics,
                    "wall_time_seconds": f"{time.perf_counter() - start_time:.3f}",
                }
                writer.writerow(row)
                csv_file.flush()
                print(
                    f"{mode} episode {episode_index + 1}/{episodes} seed={seed} "
                    f"return={episode_return:.3f} "
                    f"mean_queue={metrics['mean_queue_vehicles']:.3f} "
                    f"throughput={metrics['throughput_vehicles']} "
                    f"decisions={decision}"
                )
        finally:
            env.close()

    agent.save(checkpoint_path)
    print(f"saved {mode} checkpoint: {checkpoint_path}")
    return checkpoint_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, help="override pilot episode count per state mode")
    parser.add_argument("--seed-start", type=int, help="override first paired training seed")
    parser.add_argument("--modes", nargs="+", choices=("simple", "rich"), default=("simple", "rich"))
    parser.add_argument("--device", default="auto", help="auto, cpu, or cuda")
    parser.add_argument("--output", type=Path, help="CSV destination (default from shared config)")
    args = parser.parse_args()

    config = load_config()
    episodes = (
        int(config["training"]["episodes"]) if args.episodes is None else args.episodes
    )
    if episodes < 1:
        parser.error("--episodes must be at least 1")
    seed_start = (
        int(config["training"]["seed_start"]) if args.seed_start is None else args.seed_start
    )
    output_csv = args.output or ROOT / config["output_csv"]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_csv.write_text("", encoding="utf-8")
    torch.set_num_threads(1)
    print(f"requested device: {args.device}; CUDA available: {torch.cuda.is_available()}")
    for mode in args.modes:
        train_mode(mode, episodes, seed_start, args.device, config, output_csv)


if __name__ == "__main__":
    main()

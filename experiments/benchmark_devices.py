"""Compare CPU and CUDA DQN update throughput on a synthetic replay buffer."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch

from agents import DQNAgent


ROOT = Path(__file__).resolve().parents[1]


def benchmark(device: str, updates: int, state_dim: int, config: dict) -> float:
    options = dict(config["dqn"])
    options.pop("device", None)
    agent = DQNAgent(
        state_dim=state_dim,
        seed=1234,
        device=device,
        state_scales=config["state_scales"]["rich"],
        **options,
    )
    rng = random.Random(1234)
    for _ in range(max(256, config["dqn"]["batch_size"])):
        state = [rng.random() for _ in range(state_dim)]
        next_state = [rng.random() for _ in range(state_dim)]
        agent.remember(state, rng.randrange(2), rng.uniform(-10, 0), next_state, False)
    for _ in range(20):
        agent.train_step()
    if device == "cuda":
        torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(updates):
        agent.train_step()
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    return updates / elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--updates", type=int, default=300)
    args = parser.parse_args()
    if args.updates < 1:
        parser.error("--updates must be positive")
    torch.set_num_threads(1)
    config = json.loads((ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig"))

    rates = {"cpu": benchmark("cpu", args.updates, 9, config)}
    print(f"CPU updates/second: {rates['cpu']:.2f}")
    if torch.cuda.is_available():
        rates["cuda"] = benchmark("cuda", args.updates, 9, config)
        print(f"CUDA updates/second: {rates['cuda']:.2f}")
        speedup = rates["cuda"] / rates["cpu"]
        print(f"CUDA/CPU throughput ratio: {speedup:.3f}x")
    else:
        print("CUDA unavailable to this PyTorch installation")


if __name__ == "__main__":
    main()

"""Run training, held-out evaluation, and CSV summarization in sequence."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="auto", help="auto, cpu, or cuda")
    parser.add_argument("--episodes", type=int, help="override training episodes per state mode")
    parser.add_argument("--seed-start", type=int, help="override first paired training seed")
    parser.add_argument(
        "--evaluation-seeds", nargs="+", type=int, help="override shared evaluation seeds"
    )
    args = parser.parse_args()
    if args.episodes is not None and args.episodes < 1:
        parser.error("--episodes must be at least 1")

    train = [sys.executable, "-u", "-m", "experiments.train", "--device", args.device]
    if args.episodes is not None:
        train.extend(["--episodes", str(args.episodes)])
    if args.seed_start is not None:
        train.extend(["--seed-start", str(args.seed_start)])

    evaluate = [sys.executable, "-u", "-m", "experiments.evaluate", "--device", args.device]
    if args.evaluation_seeds:
        evaluate.append("--seeds")
        evaluate.extend(str(seed) for seed in args.evaluation_seeds)

    steps = (
        ("Train both state modes", train),
        ("Evaluate DQNs and baselines", evaluate),
        ("Summarize evaluation CSV", [sys.executable, "-u", "-m", "analysis.summarize_evaluation"]),
    )
    for label, command in steps:
        print(f"\n=== {label} ===", flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

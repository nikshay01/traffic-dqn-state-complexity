"""Summarize evaluation CSVs with means and sample standard deviations."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    "episode_return",
    "mean_wait_s",
    "mean_queue_vehicles",
    "throughput_vehicles",
    "simulated_seconds",
    "wall_time_seconds",
)
SUMMARY_FIELDS = [
    "agent",
    "state_mode",
    "n_episodes",
    *[field for metric in METRICS for field in (f"{metric}_n", f"{metric}_mean", f"{metric}_sd")],
]


def summarize(input_path: Path, output_path: Path) -> list[dict[str, str | int | float]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with input_path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            groups[(row["agent"], row["state_mode"])].append(row)

    summaries: list[dict[str, str | int | float]] = []
    for (agent, mode), rows in sorted(groups.items()):
        summary: dict[str, str | int | float] = {
            "agent": agent,
            "state_mode": mode,
            "n_episodes": len(rows),
        }
        for metric in METRICS:
            values = [float(row[metric]) for row in rows if row.get(metric, "") != ""]
            summary[f"{metric}_n"] = len(values)
            summary[f"{metric}_mean"] = (
                f"{statistics.fmean(values):.6f}" if values else ""
            )
            summary[f"{metric}_sd"] = (
                f"{statistics.stdev(values):.6f}" if len(values) > 1 else ""
            )
        summaries.append(summary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summaries)
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "results" / "evaluation.csv")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results" / "evaluation_summary.csv"
    )
    args = parser.parse_args()
    for row in summarize(args.input, args.output):
        waiting = row["mean_wait_s_mean"]
        waiting_text = "n/a" if waiting == "" else str(waiting)
        print(
            f"{row['agent']:24s} mode={row['state_mode']:6s} n={row['n_episodes']} "
            f"mean_queue={row['mean_queue_vehicles_mean']} "
            f"mean_wait_completed={waiting_text} "
            f"mean_throughput={row['throughput_vehicles_mean']}"
        )
    print(f"summary written to {args.output}")


if __name__ == "__main__":
    main()

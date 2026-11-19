"""Create reproducible Matplotlib figures from the pilot CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
COLORS = {
    "simple": "#1769AA",
    "rich": "#4E8B72",
    "fixed_time_1decision": "#7656A8",
    "random": "#C0782C",
}
METHODS = (
    ("DQN", "simple", "DQN simple\n(3 features)", COLORS["simple"]),
    ("DQN", "rich", "DQN rich\n(9 features)", COLORS["rich"]),
    ("fixed_time_1decision", "simple", "Fixed time\n(15-s interval)", COLORS["fixed_time_1decision"]),
    ("random", "simple", "Random", COLORS["random"]),
)
EVALUATION_METRICS = (
    ("episode_return", "Episode return\n(higher is better)"),
    ("mean_queue_vehicles", "Mean queue\n(vehicles)"),
    ("mean_wait_s", "Completed-trip mean wait\n(seconds)"),
    ("throughput_vehicles", "Throughput\n(arrived vehicles / episode)"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def save_figure(figure: plt.Figure, output_dir: Path, stem: str) -> None:
    figure.savefig(output_dir / f"{stem}.png", dpi=240, bbox_inches="tight")
    figure.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(figure)


def plot_training(
    training_rows: list[dict[str, str]], output_dir: Path, scenario_label: str
) -> None:
    figure, axis = plt.subplots(figsize=(8.4, 5.2), layout="constrained")
    for mode, label, color, marker, linestyle, marker_face in (
        ("simple", "DQN simple (3 features)", COLORS["simple"], "o", "-", COLORS["simple"]),
        ("rich", "DQN rich (9 features)", COLORS["rich"], "s", "--", "none"),
    ):
        rows = sorted(
            (row for row in training_rows if row["state_mode"] == mode),
            key=lambda row: int(row["episode"]),
        )
        if not rows:
            raise ValueError(f"No training rows found for state mode {mode}")
        episodes = [int(row["episode"]) for row in rows]
        returns = [float(row["episode_return"]) for row in rows]
        axis.plot(
            episodes,
            returns,
            color=color,
            marker=marker,
            markerfacecolor=marker_face,
            markersize=4,
            linewidth=1.8,
            linestyle=linestyle,
            label=label,
        )

    axis.set_title(
        f"Training episode return | {scenario_label}\n"
        "Single training run per state mode; no confidence band",
        fontsize=11,
    )
    axis.set_xlabel("Training episode")
    axis.set_ylabel("Episode return (sum of interval rewards)")
    axis.grid(True, alpha=0.25)
    axis.legend(frameon=False)
    save_figure(figure, output_dir, "training_return")


def plot_evaluation(
    evaluation_rows: list[dict[str, str]], output_dir: Path, scenario_label: str
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(11.2, 8.0), layout="constrained")
    x_positions = list(range(len(METHODS)))
    seed_values = sorted({int(row["seed"]) for row in evaluation_rows})
    if seed_values and seed_values == list(range(seed_values[0], seed_values[-1] + 1)):
        seed_label = f"Seeds {seed_values[0]}–{seed_values[-1]}"
    else:
        seed_label = f"{len(seed_values)} shared evaluation seeds"

    for axis, (metric, title) in zip(axes.flat, EVALUATION_METRICS, strict=True):
        for x, (agent, mode, label, color) in zip(x_positions, METHODS, strict=True):
            rows = sorted(
                (
                    row
                    for row in evaluation_rows
                    if row["agent"] == agent and row["state_mode"] == mode
                ),
                key=lambda row: int(row["seed"]),
            )
            values = [
                float(row[metric])
                for row in rows
                if row.get(metric, "") not in ("", "None")
            ]
            if not values:
                continue

            count = len(values)
            offset_step = min(0.04, 0.36 / max(1, count - 1))
            offsets = [(index - (count - 1) / 2) * offset_step for index in range(count)]
            axis.scatter(
                [x + offset for offset in offsets],
                values,
                color=color,
                s=30,
                alpha=0.8,
                zorder=3,
            )
            mean = statistics.fmean(values)
            spread = statistics.stdev(values) if len(values) > 1 else 0.0
            axis.errorbar(
                x,
                mean,
                yerr=spread,
                fmt="D",
                color=color,
                markersize=5,
                capsize=4,
                linewidth=1.5,
                zorder=4,
            )

        axis.set_title(title)
        axis.set_xticks(x_positions, [method[2] for method in METHODS])
        axis.grid(axis="y", alpha=0.25)
        axis.tick_params(axis="x", labelsize=8)

    figure.suptitle(
        f"Held-out evaluation by controller | {scenario_label}\n"
        f"{seed_label}; diamonds show mean ± sample SD; waiting time is for completed trips only",
        fontsize=13,
    )
    save_figure(figure, output_dir, "evaluation_comparison")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--training",
        type=Path,
        default=ROOT / "results" / "high_demand_train_episodes.csv",
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=ROOT / "results" / "high_demand_evaluation.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "figures_high_demand",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "config" / "experiment.json").read_text(encoding="utf-8-sig"))
    scenario_label = (
        f"synthetic demand {config['vehicles_per_hour_per_approach']:,} veh/h/approach, "
        f"{config['episode_end_seconds']} s episodes"
    )
    plot_training(read_csv(args.training), args.output_dir, scenario_label)
    plot_evaluation(read_csv(args.evaluation), args.output_dir, scenario_label)
    print(f"Figures saved to {args.output_dir}")
    print("  training_return.png/.pdf")
    print("  evaluation_comparison.png/.pdf")


if __name__ == "__main__":
    main()

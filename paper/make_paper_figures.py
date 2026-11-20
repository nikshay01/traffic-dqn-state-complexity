"""Create figures only from the project's recorded training/evaluation CSVs."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "rich": "#138a72",
    "simple": "#386cb0",
    "fixed": "#777777",
    "random": "#d9792b",
    "grid": "#dddddd",
}
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "figure.dpi": 160,
        "savefig.dpi": 600,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=600, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def training_curves() -> None:
    rows = read_csv(ROOT / "results" / "high_demand_train_episodes.csv")
    fig, axes = plt.subplots(3, 1, figsize=(6.15, 4.0), sharex=True)
    metrics = [
        ("mean_queue_vehicles", "Time-average queue (vehicles)"),
        ("mean_wait_s", "Completed-trip waiting time (s)"),
        ("throughput_vehicles", "Arrivals by 300 s (vehicles)"),
    ]
    styles = [("simple", COLORS["simple"], "Compact (3)"),
              ("rich", COLORS["rich"], "Rich (9)")]
    for ax, (metric, ylabel) in zip(axes, metrics):
        for mode, color, label in styles:
            series = sorted((r for r in rows if r["state_mode"] == mode),
                            key=lambda r: int(r["episode"]))
            x = np.asarray([int(r["episode"]) for r in series])
            y = np.asarray([float(r[metric]) for r in series])
            rolling = np.convolve(y, np.ones(10) / 10, mode="valid")
            ax.plot(x, y, color=color, alpha=0.13, lw=0.6)
            ax.plot(x[9:], rolling, color=color, lw=1.4, label=label)
        ax.axvline(31, color="#555555", ls="--", lw=0.75, alpha=0.8)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
    axes[0].legend(loc="upper right", frameon=False, ncol=2)
    axes[0].text(33, axes[0].get_ylim()[1],
                 "epsilon reaches floor around episode 31",
                 ha="left", va="top", fontsize=6.5, color="#555555")
    axes[-1].set_xlabel("Training episode (160 episodes per state mode)")
    fig.tight_layout(h_pad=0.55)
    save(fig, "training_progress")


def evaluation_plot() -> None:
    rows = read_csv(ROOT / "results" / "high_demand_evaluation.csv")
    agents = [
        ("DQN", "rich", "Rich DQN (9)", COLORS["rich"]),
        ("DQN", "simple", "Compact DQN (3)", COLORS["simple"]),
        ("fixed_time_1decision", "simple", "Fixed-time", COLORS["fixed"]),
        ("random", "simple", "Random", COLORS["random"]),
    ]
    metrics = [
        ("mean_queue_vehicles", "Mean queue (vehicles)", True),
        ("mean_wait_s", "Completed-trip wait (s)", True),
        ("throughput_vehicles", "Arrivals / episode", False),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(6.15, 2.45))
    y_positions = np.arange(len(agents))
    for ax, (metric, title, lower_better) in zip(axes, metrics):
        for y, (agent, mode, _label, color) in zip(y_positions, agents):
            values = [float(r[metric]) for r in rows
                      if r["agent"] == agent and r["state_mode"] == mode]
            mean = float(np.mean(values))
            sd = float(np.std(values, ddof=1))
            ax.errorbar(mean, y, xerr=sd, fmt="o", color=color,
                        ecolor=color, capsize=2, ms=4, lw=1.0)
        ax.set_title(title)
        ax.set_yticks(y_positions, [a[2] for a in agents])
        ax.invert_yaxis()
        ax.grid(axis="x", color=COLORS["grid"], lw=0.5)
        ax.set_xlabel("Lower is better" if lower_better else "Higher is better")
    fig.suptitle("Held-out evaluation means ± sample SD (10 shared seeds)",
                 y=1.04, fontsize=9)
    fig.tight_layout()
    save(fig, "evaluation_means")


def paired_improvements() -> None:
    rows = read_csv(ROOT / "results" / "high_demand_evaluation.csv")
    indexed = {(r["agent"], r["state_mode"], int(r["seed"])): r for r in rows}
    seeds = list(range(300, 310))
    metrics = [
        ("mean_queue_vehicles", "Queue reduction (vehicles)"),
        ("mean_wait_s", "Waiting-time reduction (s)"),
        ("throughput_vehicles", "Arrival increase (vehicles)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(6.15, 2.95), sharey=True)
    y = np.arange(len(seeds))
    for ax, (metric, title) in zip(axes, metrics):
        delta = []
        for seed in seeds:
            compact = float(indexed[("DQN", "simple", seed)][metric])
            rich = float(indexed[("DQN", "rich", seed)][metric])
            delta.append(compact - rich if metric != "throughput_vehicles"
                         else rich - compact)
        ax.axvline(0, color="#333333", lw=0.8, ls="--")
        ax.scatter(delta, y, s=15, color=COLORS["rich"], zorder=3)
        ax.axvline(float(np.mean(delta)), color=COLORS["simple"], lw=1.0,
                   label="Mean difference")
        ax.set_title(title)
        ax.set_xlabel("Positive favors rich state")
        ax.grid(axis="x", color=COLORS["grid"], lw=0.5)
    axes[0].set_yticks(y, [str(seed) for seed in seeds])
    axes[0].set_ylabel("Evaluation seed")
    axes[-1].legend(frameon=False, fontsize=6.5, loc="lower right")
    fig.tight_layout()
    save(fig, "paired_seed_differences")


if __name__ == "__main__":
    training_curves()
    evaluation_plot()
    paired_improvements()
    print(f"Wrote three data-derived figures to {OUT}")

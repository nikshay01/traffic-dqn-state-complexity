# Traffic Signal DQN State Complexity Pilot

A single-intersection SUMO pilot comparing compact and richer DQN observations. This is an integration prototype, not a validated research result.

## Verified on the lead laptop

- Python 3.11.9; Git; Eclipse SUMO 1.28.0, TraCI 1.28.0, and sumolib 1.28.0 in `.venv`.
- One SUMO CLI run completed the 300-second, 300-vehicles/hour-per-approach scenario with seed 42.
- The TraCI smoke run returned state lengths 3 and 9, switched safely from phase 0 to phase 2, and held phase 2 on action 0.
- The generated signal and lane IDs are recorded in `simulation/network_manifest.json` and were checked against the generated network and the TraCI run.
- Member 2/3 implementations are in environment/, agents/, and experiments/. The code makes no performance claim; see actual local result files under results/ after running the pilot.

## Windows setup

In PowerShell, from this repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SUMO_HOME = python -c "import sumo; print(sumo.SUMO_HOME)"
$env:Path = "$env:SUMO_HOME\bin;$env:Path"
python --version
python -c "import traci, sumolib; print('TraCI and sumolib imports passed')"
sumo --version
netconvert --version
python -m experiments.traci_smoke
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of `python`; do not change the machine-wide execution policy.

Install one PyTorch build for the DQN. For a CPU-only machine:

~~~powershell
python -m pip install -r requirements-cpu.txt
~~~

For a machine with an NVIDIA GPU:

~~~powershell
python -m pip install -r requirements-gpu-cu128.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
~~~

SUMO traffic simulation remains CPU-based; CUDA accelerates only the small DQN network. Measure local update speed before choosing the GPU:

~~~powershell
python -m experiments.benchmark_devices
~~~

## Train and evaluate the synthetic high-demand pilot

Run the model checks and SUMO integration smoke run:

~~~powershell
python -m unittest discover -s tests -v
python -m experiments.traci_smoke
~~~

The current profile uses four straight-through flows at 900 vehicles/hour per approach, a 300-second episode, and a 15-second decision interval. These are synthetic generated flows, not calibrated local traffic counts. Both state representations train for 160 episodes on paired SUMO seeds 42–201; evaluation uses 10 distinct shared seeds (300–309) and includes fixed-time and seeded-random controllers:

~~~powershell
python -m experiments.train
python -m experiments.evaluate
python -m analysis.summarize_evaluation
python -m analysis.plot_results
~~~

For the complete train → evaluate → summarize acceptance run in one command:

~~~powershell
python -m experiments.run_pilot --device cpu
~~~

The runner stops if a step fails. Optional flags include --episodes, --seed-start, and --evaluation-seeds.

Matplotlib figures for the current profile are saved as PNG and PDF under results/figures_high_demand/. Rerun analysis.plot_results after you update the CSV results.

The run writes results/high_demand_train_episodes.csv, results/high_demand_evaluation.csv, and results/high_demand_evaluation_summary.csv. Figures go to results/figures_high_demand/ in PNG and PDF formats. Earlier balanced-demand pilot files remain in results/ and results/figures/ for comparison. The `.py` files contain Python source, `plt` is the usual in-code alias for `matplotlib.pyplot`, and `.pt` files are PyTorch model checkpoints; none of those is a Matplotlib figure format.

For a fast calibration run that does not replace the 160-episode results, use `python -m experiments.train --episodes 1 --output results/calibration_train.csv`. This writes a temporary CSV and the current checkpoints; run a full training/evaluation only after confirming the scenario. One training run per state mode is still limited evidence and cannot establish convergence or that one observation is better. Temporary calibration CSVs, TripInfo XML files, and model checkpoints are ignored by Git.

Mean queue is averaged over one-second SUMO steps. Throughput counts vehicles that arrived before episode end. Mean waiting time averages SUMO TripInfo waitingTime for completed trips only; unfinished trips are excluded.
To keep the extra rich-state features on comparable numeric scales, the DQN divides each observation feature by the fixed divisor listed under state_scales in config/experiment.json. The shared queue and green-axis features use the same divisors for both agents.

## Current high-demand run

Recorded on 2026-11-19 with 900 generated vehicles/hour on each approach. Each DQN trained for 160 episodes on seeds 42–201. The final evaluation used 10 distinct shared seeds 300–309, separate from training. Values below are mean ± sample standard deviation across those seeds:

| Controller | Episode return | Mean queue (vehicles) | Completed-trip mean wait (s) | Arrivals per episode |
|---|---:|---:|---:|---:|
| DQN rich (9 features) | -238.120 ± 5.867 | 11.906 ± 0.293 | 13.551 ± 0.666 | 219.1 ± 2.7 |
| DQN simple (3 features) | -245.047 ± 7.706 | 12.252 ± 0.385 | 15.388 ± 0.561 | 210.2 ± 2.7 |
| Fixed time (15-second interval) | -245.047 ± 7.706 | 12.252 ± 0.385 | 15.388 ± 0.561 | 210.2 ± 2.7 |
| Random | -300.007 ± 21.682 | 15.000 ± 1.084 | 17.636 ± 2.865 | 213.9 ± 13.9 |

In this one training run, the richer observation had better averages than the simple observation on these metrics. The simple DQN matched the fixed-time controller on all 10 evaluation seeds. This result is descriptive only: one training run per state mode and 10 simulation seeds do not establish statistical significance or generalization. Waiting time includes completed trips only; vehicles still in SUMO at episode end are excluded. The generated traffic is a synthetic peak-load scenario, not a model calibrated with local traffic counts. Raw results and sample standard deviations are in results/high_demand_evaluation.csv and results/high_demand_evaluation_summary.csv; figures are in results/figures_high_demand/.

## Earlier balanced-demand pilot (separate from the current profile)

Run on 2026-11-19 with 300 generated vehicles/hour per approach, 20 training episodes per state mode, and three shared evaluation seeds. On each evaluation seed, both trained DQNs matched the fixed-time baseline's episode return, queue, completed-trip waiting time, throughput, and simulated duration. Across the three seeds the mean queue was 1.332 vehicles, completed-trip mean waiting time was 3.729 seconds, and throughput was 93.667 vehicles per 300-second episode. The seeded-random controller averaged 4.260 vehicles in queue, 12.267 seconds completed-trip waiting time, and 89.333 arrivals. The raw training rows, evaluation rows, summary, and figures are retained separately in results/.

This is a small engineering pilot, not a statistically powered result. The exact match with fixed-time shows that these checkpoints did not demonstrate an advantage over that baseline. Completed-trip waiting time excludes vehicles still in the network when an episode ends, so read it with queue and throughput.

## GitHub collaboration

Public repository: <https://github.com/nikshay01/traffic-dqn-state-complexity>

Branches:

- `main`: integration lead.
- `feature/sumo-environment`: SUMO/environment teammate.
- `feature/dqn-agent`: DQN teammate.
- `feature/research-paper`: paper and analysis teammate.

Clone once, then switch to the assigned branch:

```powershell
git clone https://github.com/nikshay01/traffic-dqn-state-complexity.git
cd traffic-dqn-state-complexity
git switch feature/dqn-agent
```

Replace the branch name with the teammate's assignment. The repository is public, so anyone can view and clone it; only the owner and invited collaborators can push. Invite teammates by their GitHub usernames when available, or have them submit pull requests from forks.

## Project layout

- `simulation/`: SUMO network, routes, configuration, and verified network manifest.
- `environment/`: TraCI environment adapter.
- `agents/`: DQN model, replay buffer, and agent.
- `experiments/`: training/evaluation entry points and the TraCI smoke run.
- `config/`: shared experiment settings.
- `results/`: generated raw results; do not hand-edit or fabricate values.
- `analysis/`: scripts that read raw results.
- `paper/`: paper draft and references.

## Reporting rule

Keep actual run output. A working environment or short pilot run does not establish that a DQN learned or that one state representation is better.

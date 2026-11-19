# Traffic Signal DQN State Complexity Pilot

A single-intersection SUMO pilot comparing compact and richer DQN observations. This is an integration prototype, not a validated research result.

## Verified on the lead laptop

- Python 3.11.9; Git; Eclipse SUMO 1.28.0, TraCI 1.28.0, and sumolib 1.28.0 in `.venv`.
- One SUMO CLI run completed the 300-second, 300-vehicles/hour-per-approach scenario with seed 42.
- The TraCI smoke run returned state lengths 3 and 9, switched safely from phase 0 to phase 2, and held phase 2 on action 0.
- The generated signal and lane IDs are recorded in `simulation/network_manifest.json` and were checked against the generated network and the TraCI run.
- No teammate DQN or paper implementation files were present. No DQN training result is claimed.

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

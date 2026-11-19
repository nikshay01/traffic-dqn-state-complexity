# Traffic Signal DQN State Complexity Pilot

This repository is the integration workspace for a single-intersection pilot comparing a compact DQN observation with a richer observation. It is a prototype, not a validated research result.

## Current status

- No teammate implementation files were present in the supplied project mirror.
- The supplied project folder was not a Git repository.
- Python 3.11.9 and Git are available on the lead laptop.
- SUMO, TraCI, and sumolib 1.28.0 are installed and verified in this project's `.venv`.
- Public GitHub repository: https://github.com/nikshay01/traffic-dqn-state-complexity.
- The shared API and experiment contract are in [INTERFACE.md](INTERFACE.md).
- Actual network IDs, signal phases, and decision timing remain pending inspection of a generated SUMO network.

## Windows setup

Run these commands in PowerShell from the repository folder:

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
```

If PowerShell blocks virtual-environment activation, run `.\.venv\Scripts\python.exe` in place of `python`; do not change the machine-wide execution policy.

## Project layout

- `simulation/`: SUMO network, routes, configuration, and verified network manifest.
- `environment/`: TraCI environment adapter.
- `agents/`: DQN model, replay buffer, and agent.
- `experiments/`: training and evaluation entry points.
- `config/`: shared experiment settings.
- `results/`: generated raw results; do not hand-edit or fabricate values.
- `analysis/`: scripts that read raw results.
- `paper/`: paper draft and references.

## Rule for reporting

Report a run as successful only after executing it and preserving its output. A working environment or a short pilot run does not by itself establish that the DQN learned or that one state representation is better.


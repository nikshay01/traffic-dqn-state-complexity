# Shared integration contract

Use this contract across the environment, DQN, experiment, and analysis work. If an actual teammate deliverable conflicts with it, record the conflict and resolve it before merging; do not guess which side is correct.

## Environment API

`environment/sumo_env.py` will provide `SumoEnvironment`:

```python
env = SumoEnvironment(config_path="simulation/config.sumocfg")
env.reset(seed=42)
state = env.get_state(mode="simple")
next_state, reward, done, info = env.step(action, mode="simple")
env.close()
```

- `reset(seed: int | None = None) -> None` starts a fresh episode using the requested seed.
- `get_state(mode: str) -> list[float]` accepts only `"simple"` or `"rich"`.
- `step(action: int, mode: str = "simple") -> tuple[list[float], float, bool, dict]` accepts only actions `0` and `1`, advances by the configured 15-second pilot decision interval and returns the observation in the requested mode at a legal green decision point.
- `close() -> None` closes the TraCI connection and SUMO process.
- The environment owns all SUMO-specific IDs and phase handling. The DQN receives only numeric observations and returns an action.
- The environment must use the network's verified signal program and its clearance phases. It must not invent lane IDs, signal IDs, phase indices, or signal-state strings.

## Action meaning

- `0`: keep the currently active north-south or east-west green axis.
- `1`: request the other axis at the next legal decision point.
- SUMO's verified yellow clearance phase is handled by the environment. The agent never sets a raw signal string.

## State meaning

Features use incoming lanes grouped by the verified north-south and east-west approaches in `simulation/network_manifest.json`.

| Mode | Length | Ordered features |
| --- | ---: | --- |
| `simple` | 3 | `ns_queue_vehicles`, `ew_queue_vehicles`, `green_axis` |
| `rich` | 9 | `ns_queue_vehicles`, `ew_queue_vehicles`, `green_axis`, `ns_wait_s`, `ew_wait_s`, `ns_mean_speed_mps`, `ew_mean_speed_mps`, `ns_mean_occupancy_fraction`, `ew_mean_occupancy_fraction` |

Definitions:

- Queue is the sum of halting vehicles across the verified incoming lanes for that axis.
- Waiting time is the sum of lane waiting-time readings across those incoming lanes.
- Mean speed is the arithmetic mean across the incoming lanes for that axis. Convert each lane occupancy percentage to a 0-1 fraction by dividing by 100, then average; use `0.0` when an axis has no usable lane reading.
- `green_axis` is `0.0` for north-south and `1.0` for east-west. States are returned only at legal decision points with a known active green axis.
- Return finite Python floats in the listed order. The DQN may convert the list to its tensor type.

The previous planning notes called the rich state 10 features, but the accompanying feature list contains only nine. This pilot freezes the list above at nine; do not add an unspecified tenth feature.

## DQN API

`agents/dqn_agent.py` will provide `DQNAgent`:

```python
agent = DQNAgent(state_dim=3, action_dim=2, seed=42)
action = agent.select_action(state, training=True)
agent.remember(state, action, reward, next_state, done)
agent.train_step()
agent.save(path)
agent.load(path)
```

- `select_action` returns the integer `0` or `1`.
- The simple model uses `state_dim=3`; the rich model uses `state_dim=9`.
- Use the same DQN hyperparameters, seeds, traffic demand, episode length, reward, training budget, and evaluation procedure for both modes. State dimension is the planned difference.

## Reward and run records

- Per-step reward is the negative mean of total north-south plus east-west queue count over the simulation steps covered by that environment step.
- Each completed episode is recorded as one CSV row with at least: `seed,agent,state_mode,episode,episode_return,mean_wait_s,mean_queue_vehicles,throughput_vehicles,simulated_seconds,wall_time_seconds`.
- The environment owner must document the exact SUMO-derived calculation used for every reported metric.
- Keep raw run output. Never fill result rows with examples or expected values.

## Network facts and re-verification

The lead generated and inspected `simulation/intersection.net.xml` and checked the scenario with SUMO 1.28.0. The observed IDs and phases are recorded in `simulation/network_manifest.json`. Re-verify them if the network or signal program changes. The environment must use those observed phases and never replace the yellow clearance with a guessed signal string.

## Pilot run additions

The environment reset method also accepts an optional TripInfo output path:

    env.reset(seed=42, tripinfo_path="results/tripinfo_example.xml")

After the episode, close SUMO before reading the finalized metrics:

    env.close()
    metrics = env.get_episode_metrics()

Mean queue is the average total halted-vehicle count across every one-second simulation step. Throughput is the accumulated SUMO arrived-vehicle count. Mean waiting time is the average waitingTime value in completed-trip TripInfo records; vehicles still in the network at episode end are excluded. If no trips completed, mean_wait_s is null.

The engineering pilot trains each state mode for 20 episodes on matching seeds 42–61. Evaluation uses the same three demand seeds for each controller: 100, 101, and 102. The fixed-time baseline switches at each decision interval (15 seconds including the network's 3-second verified yellow clearance); the random baseline samples seeded actions. This budget is an integration check and does not establish policy convergence or a statistically significant difference.

DQN inputs are divided by the fixed feature scales in config/experiment.json. Both state modes use the same divisor for queue and green-axis features. Rich-state waiting time uses the 300-second episode horizon as a scale, speed uses the generated network's 13.89 m/s lane speed limit, and occupancy and green-axis fractions are unchanged. These divisors are scaling references, not clipping limits.



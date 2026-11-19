from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from agents import DQNAgent, DQNNetwork, ReplayBuffer


class DQNTests(unittest.TestCase):
    def test_network_supports_both_observation_dimensions(self) -> None:
        for state_dim in (3, 9):
            network = DQNNetwork(state_dim=state_dim, action_dim=2)
            values = network(torch.zeros((4, state_dim)))
            self.assertEqual(tuple(values.shape), (4, 2))

    def test_network_rejects_unexpected_dimension(self) -> None:
        with self.assertRaises(ValueError):
            DQNNetwork(state_dim=3)(torch.zeros((1, 9)))

    def test_replay_buffer_is_bounded_and_sampled(self) -> None:
        buffer = ReplayBuffer(capacity=3, seed=7)
        for index in range(4):
            buffer.add([index], index % 2, float(index), [index + 1], False)
        self.assertEqual(len(buffer), 3)
        self.assertEqual(len(buffer.sample(2)), 2)
        with self.assertRaises(ValueError):
            buffer.sample(4)

    def test_agent_actions_training_checkpoint_and_dimension_guard(self) -> None:
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as temp_dir:
            for state_dim in (3, 9):
                agent = DQNAgent(
                    state_dim=state_dim,
                    seed=17,
                    hidden_dims=(16, 16),
                    batch_size=2,
                    replay_capacity=8,
                    target_update_interval=1,
                    device="cpu",
                )
                state = [0.0] * state_dim
                action = agent.select_action(state, training=False)
                self.assertIn(action, (0, 1))
                agent.remember(state, action, -1.0, state, False)
                self.assertIsNone(agent.train_step())
                agent.remember(state, 1 - action, -0.5, state, True)
                loss = agent.train_step()
                self.assertIsNotNone(loss)
                self.assertGreaterEqual(float(loss), 0.0)
                self.assertEqual(agent.train_steps, 1)
                checkpoint = Path(temp_dir) / f"dqn_{state_dim}.pt"
                agent.save(checkpoint)
                restored = DQNAgent(
                    state_dim=state_dim,
                    seed=99,
                    hidden_dims=(16, 16),
                    batch_size=2,
                    replay_capacity=8,
                    target_update_interval=1,
                    device="cpu",
                )
                restored.load(checkpoint)
                self.assertEqual(restored.train_steps, 1)
                self.assertEqual(restored.config["state_scales"], [1.0] * state_dim)
                self.assertEqual(
                    restored.select_action(state, training=False),
                    agent.select_action(state, training=False),
                )
            incompatible = DQNAgent(state_dim=3, device="cpu")
            with self.assertRaises(ValueError):
                incompatible.load(Path(temp_dir) / "dqn_9.pt")

    def test_agent_applies_configured_feature_divisors(self) -> None:
        agent = DQNAgent(state_dim=3, state_scales=[20.0, 20.0, 1.0], device="cpu")
        self.assertEqual(agent._validate_state([20.0, 10.0, 1.0]), [1.0, 0.5, 1.0])


if __name__ == "__main__":
    unittest.main()

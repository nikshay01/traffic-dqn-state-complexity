"""Small fully connected Q-network for the project's state representations."""

from __future__ import annotations

import torch
from torch import nn


class DQNNetwork(nn.Module):
    """Map a numeric observation to one Q-value per signal action."""

    def __init__(
        self,
        state_dim: int,
        action_dim: int = 2,
        hidden_dims: tuple[int, ...] | list[int] = (64, 64),
    ) -> None:
        super().__init__()
        if state_dim < 1 or action_dim < 1:
            raise ValueError("state_dim and action_dim must be positive")
        if not hidden_dims or any(width < 1 for width in hidden_dims):
            raise ValueError("hidden_dims must contain positive layer widths")

        layers: list[nn.Module] = []
        previous_width = state_dim
        for width in hidden_dims:
            layers.extend((nn.Linear(previous_width, int(width)), nn.ReLU()))
            previous_width = int(width)
        layers.append(nn.Linear(previous_width, action_dim))
        self.network = nn.Sequential(*layers)
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)

    def forward(self, states: torch.Tensor) -> torch.Tensor:
        if states.shape[-1] != self.state_dim:
            raise ValueError(
                f"Expected observations with {self.state_dim} features, "
                f"received shape {tuple(states.shape)}"
            )
        return self.network(states)

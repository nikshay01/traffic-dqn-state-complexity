"""Bounded experience replay for one-step DQN transitions."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Transition:
    state: tuple[float, ...]
    action: int
    reward: float
    next_state: tuple[float, ...]
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int, seed: int | None = None) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._items: deque[Transition] = deque(maxlen=capacity)
        self._rng = random.Random(seed)

    def add(
        self,
        state: list[float] | tuple[float, ...],
        action: int,
        reward: float,
        next_state: list[float] | tuple[float, ...],
        done: bool,
    ) -> None:
        self._items.append(
            Transition(
                state=tuple(float(value) for value in state),
                action=int(action),
                reward=float(reward),
                next_state=tuple(float(value) for value in next_state),
                done=bool(done),
            )
        )

    def sample(self, batch_size: int) -> list[Transition]:
        if batch_size < 1 or batch_size > len(self._items):
            raise ValueError(
                f"batch_size must be between 1 and current size ({len(self._items)})"
            )
        return self._rng.sample(list(self._items), batch_size)

    def __len__(self) -> int:
        return len(self._items)

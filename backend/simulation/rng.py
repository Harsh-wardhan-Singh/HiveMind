"""HIVEMIND Deterministic Seeded Pseudo-Random Number Generator Manager."""

import random


class SeededRNG:
    """
    Manages deterministic pseudo-random number generation for the simulation.
    Supports isolated subsystem child streams to prevent cross-contamination.
    """

    def __init__(self, master_seed: int):
        self.master_seed: int = master_seed
        self._master_prng: random.Random = random.Random(master_seed)
        self._child_streams: dict[str, random.Random] = {}

    def get_stream(self, subsystem_name: str) -> random.Random:
        """
        Retrieve or deterministically initialize an isolated child stream for a subsystem.
        """
        if subsystem_name not in self._child_streams:
            # Deterministically derive child seed from master PRNG
            child_seed = self._master_prng.randint(0, 2**31 - 1)
            self._child_streams[subsystem_name] = random.Random(child_seed)
        return self._child_streams[subsystem_name]

    def reset(self, new_seed: int | None = None) -> None:
        """Reset the master seed and clear all child streams."""
        if new_seed is not None:
            self.master_seed = new_seed
        self._master_prng = random.Random(self.master_seed)
        self._child_streams.clear()

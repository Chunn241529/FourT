"""
Input Humanizer Service
Provides human-like randomization for input timings to avoid anti-cheat detection.
Uses Gaussian (Normal) distribution for natural variance.
"""

import random
import time


class InputHumanizer:
    """
    Generates human-like delays for input simulation.
    """

    @staticmethod
    def get_click_delay(
        target_ms: float = 50, variance_ms: float = 10, min_ms: float = 20
    ) -> float:
        """
        Get a randomized delay for key click duration (hold time).

        Args:
            target_ms: Target duration in milliseconds (default 50ms)
            variance_ms: Standard deviation in milliseconds (default 10ms)
            min_ms: Minimum allowable duration in milliseconds

        Returns:
            Float seconds to sleep
        """
        # Use simple triangular distribution for speed and "good enough" randomness
        # or gauss for more natural curve. Gauss is better for anti-cheat.
        ms = random.gauss(target_ms, variance_ms)

        # Clamp values
        if ms < min_ms:
            ms = min_ms

        # Convert to seconds
        return ms / 1000.0

    @staticmethod
    def get_action_delay(target_ms: float = 50, variance_ms: float = 15) -> float:
        """
        Get a randomized delay between actions (e.g. between skills).

        Args:
            target_ms: Target delay in milliseconds
            variance_ms: Standard deviation

        Returns:
            Float seconds to sleep
        """
        ms = random.gauss(target_ms, variance_ms)
        if ms < 10:  # Minimum 10ms between actions
            ms = 10

        return ms / 1000.0

    @staticmethod
    def apply_jitter(base_value_sec: float, percentage: float = 0.1) -> float:
        """
        Apply percentage-based jitter to a value (seconds).

        Args:
            base_value_sec: Base value in seconds
            percentage: Max percentage variance (0.1 = 10%)

        Returns:
            Randomized value in seconds
        """
        if base_value_sec <= 0:
            return 0

        variance = base_value_sec * percentage
        return random.uniform(base_value_sec - variance, base_value_sec + variance)


# Global singleton
humanizer = InputHumanizer()

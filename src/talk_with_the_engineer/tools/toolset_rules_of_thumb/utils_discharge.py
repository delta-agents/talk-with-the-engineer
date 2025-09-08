"""
Utility functions for the Talk with the engineer.

Provides centralized utils for rainfall statistics & conversion to flow rate
 needed in multiple tools.
"""

import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
)


def get_discharge(input: RainfallInput, rainfall_per_day: np.ndarray) -> np.ndarray:
    discharge_curve = _get_discharge_curve(days_to_discharge=input.days_to_discharge)
    MODEL_DAY_LENGTH = 7  # by then all water as left

    length_rainfall_days = int(input.length_event_hrs / 24)

    # bouw matrix op (HKV PR4991.10 :Tabel 39: Neerslag-afvoerrelatie, 3 mogelijkheden)
    model_matrix = np.zeros((MODEL_DAY_LENGTH, length_rainfall_days))
    for column in range(length_rainfall_days):
        for row, value in enumerate(discharge_curve):
            model_matrix[row + column, column] = value
    # final computation:
    flow_per_day: np.ndarray = (model_matrix * rainfall_per_day).sum(axis=1)
    return flow_per_day, model_matrix


def _get_discharge_curve(days_to_discharge) -> list:
    """From HKV PR4991.10 • september 2024: Tabel 39
    Neerslag-afvoerrelatie,
    3 mogelijkheden,
    vertaling van de dagneerslag
    uit een vierdaags neerslagpatroon
    naar regionale afvoer over 2, 3 of 4 dagen.
    """
    data = {
        2: [0.35, 0.65],
        3: [0.25, 0.5, 0.25],
        4: [0.25, 0.25, 0.25, 0.25],
    }
    return data[days_to_discharge]

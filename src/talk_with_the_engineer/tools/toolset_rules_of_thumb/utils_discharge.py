"""
Utility functions for the Talk with the engineer.

Provides centralized utils for rainfall statistics & conversion to flow rate
 needed in multiple tools.
"""

import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.hold import HoldInput


def get_discharge(input: RainfallInput, rainfall_per_day: np.ndarray) -> np.ndarray:
    """Get the discharge for a given rainfall input, used for Store and Discharge tool."""
    discharge_curve = _get_discharge_curve(days_to_discharge=input.days_to_discharge)
    flow_per_day, model_matrix = _get_model_matrix(
        input, rainfall_per_day, discharge_curve
    )
    return flow_per_day, model_matrix


def get_held_discharge(input: HoldInput, rainfall_per_day: np.ndarray) -> np.ndarray:
    """Similar to get_discharge but for Hold tool, with extra days to hold the water.
    Calls _get_model_matrix twice to get normal and delayed discharge curves."""
    discharge_curve = _get_discharge_curve(days_to_discharge=input.days_to_discharge)
    discharge_curve_delayed = _get_discharge_curve(
        days_to_discharge=input.days_to_discharge + input.days_to_hold_discharge
    )

    flow_per_day, model_matrix = _get_model_matrix(
        input, rainfall_per_day, discharge_curve, 7 + input.days_to_hold_discharge
    )
    flow_per_day_delayed, model_matrix_delayed = _get_model_matrix(
        input,
        rainfall_per_day,
        discharge_curve_delayed,
        model_day_length=7 + input.days_to_hold_discharge,
    )

    return flow_per_day, flow_per_day_delayed, model_matrix, model_matrix_delayed


def _get_model_matrix(
    input: RainfallInput, rainfall_per_day, discharge_curve: list, model_day_length=7
) -> np.ndarray:
    # by then all water as left
    length_rainfall_days = int(input.length_event_hrs / 24)

    # bouw matrix op (HKV PR4991.10 :Tabel 39: Neerslag-afvoerrelatie, 3 mogelijkheden)
    model_matrix = np.zeros((model_day_length, length_rainfall_days))
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
    if days_to_discharge < 2 or days_to_discharge > 10:
        raise ValueError("days_to_discharge must be between 2 and 10")
    data = {
        2: [0.35, 0.65],
        3: [0.25, 0.5, 0.25],
        4: [0.25, 0.25, 0.25, 0.25],
        5: [0.2, 0.2, 0.2, 0.2, 0.2],
        6: [0.2, 0.2, 0.2, 0.2, 0.1, 0.1],
        7: [0.15, 0.15, 0.15, 0.15, 0.1, 0.15, 0.15],
        8: [0.15, 0.15, 0.15, 0.1, 0.1, 0.15, 0.1, 0.1],
        9: [0.1, 0.1, 0.1, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1],
        10: [0.1] * 10,
    }
    return data[days_to_discharge]

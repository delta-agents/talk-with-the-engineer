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
    """Get the discharge for a given rainfall input, used for Store and Discharge tool."""
    discharge_curve = _get_discharge_curve(days_to_discharge=input.days_to_discharge)
    flow_per_day, model_matrix = _get_model_matrix(
        input, rainfall_per_day, discharge_curve
    )
    flow_mm_h = flow_per_day / 24  # mm/d / 24 = mm/h
    flow_l_s_ha = flow_mm_h * 10 / 3.6  # mm/h to l/s/ha
    flow_per_hour_l_s_ha = np.repeat(flow_l_s_ha, 24)  # Convert days to hours

    return flow_per_hour_l_s_ha, model_matrix


def _get_model_matrix(
    input: RainfallInput,
    rainfall_per_day,
    discharge_curve: list,
    model_day_length: int | None = None,
) -> np.ndarray:
    length_rainfall_days = int(input.length_event_hrs / 24)

    # De laatste regendag begint pas af te voeren op dag `length_rainfall_days`, en doet
    # daar `len(discharge_curve)` dagen over. Een vaste lengte van 7 dagen liep stuk op
    # een 8-daagse bui (IndexError); zie PLAN_TOOLS_REFACTOR.md D2.
    required_days = length_rainfall_days + len(discharge_curve) - 1
    if model_day_length is None:
        model_day_length = required_days
    elif model_day_length < required_days:
        raise ValueError(
            f"model_day_length {model_day_length} is te klein voor een bui van "
            f"{length_rainfall_days} dagen met een afvoerduur van "
            f"{len(discharge_curve)} dagen; minimaal {required_days} nodig"
        )

    # bouw matrix op (HKV PR4991.10 :Tabel 39: Neerslag-afvoerrelatie, 3 mogelijkheden)
    model_matrix = np.zeros((model_day_length, length_rainfall_days))
    for column in range(length_rainfall_days):
        for row, value in enumerate(discharge_curve):
            model_matrix[row + column, column] = value
    # final computation:
    flow_per_day: np.ndarray = (model_matrix * rainfall_per_day).sum(axis=1)
    return flow_per_day, model_matrix


def _get_discharge_curve(days_to_discharge) -> list:
    """From HKV PR4991.10 - september 2024: Tabel 39

    Neerslag-afvoerrelatie,
    3 mogelijkheden,
    vertaling van de dagneerslag
    uit een vierdaags neerslagpatroon
    naar regionale afvoer over 2, 3 of 4 dagen.

    Het rapport geeft alleen deze drie mogelijkheden. Eerdere versies van deze functie
    hadden ook curves voor 5 t/m 10 dagen; die stonden niet in het rapport, waren met de
    hand verzonnen en werden door de validator nooit toegelaten. Zie
    PLAN_TOOLS_REFACTOR.md D12.
    """
    data = {
        2: [0.35, 0.65],
        3: [0.25, 0.5, 0.25],
        4: [0.25, 0.25, 0.25, 0.25],
    }
    if days_to_discharge not in data:
        raise ValueError(
            f"days_to_discharge must be one of {sorted(data)}, got {days_to_discharge}"
        )
    return data[days_to_discharge]

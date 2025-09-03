"""
Utility functions for the Talk with the engineer.

Provides centralized utils for rainfall statistics & conversion to flow rate
 needed in multiple tools.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
)


def get_rainfall(input: RainfallInput):
    volume_rain_mm = get_sum_rainfall_stats(
        return_period=input.return_period,
        time_of_year=input.time_of_year,
        length_event_hrs=input.length_event_hrs,
        rainfall_regime=input.rainfall_regime,
    )

    disposal_curve = _get_disposal_curve(days_to_dispose=input.days_to_dispose)

    length_rainfall_days = int(input.length_event_hrs / 24)
    MODEL_DAY_LENGTH = 7  # by then all water as left

    # bouw matrix op (HKV PR4991.10 :Tabel 39: Neerslag-afvoerrelatie, 3 mogelijkheden)
    model_matrix = np.zeros((MODEL_DAY_LENGTH, length_rainfall_days))
    for column in range(length_rainfall_days):
        for row, value in enumerate(disposal_curve):
            model_matrix[row + column, column] = value

    rainfall_pattern = get_rainfall_pattern(
        time_of_year=input.time_of_year,
        length_event_hrs=input.length_event_hrs,
        name_rainfall_pattern=input.name_rainfall_pattern,
    )
    # TODO: later we can also return the Bui in hours: for modelling purposes this can be useful
    #       remove the summing and change the model matrix, small change later on

    # reshape (always 8 days) and sum the rainfall pattern to daily values
    rainfall_pattern_day: np.ndarray = (
        rainfall_pattern.to_numpy().reshape(8, 24).sum(axis=1)
    )
    # the fault length is 8 days, we can ignore the trailling zeros.
    rainfall_pattern_day = rainfall_pattern_day[:length_rainfall_days]
    rainfall_per_day = rainfall_pattern_day * volume_rain_mm

    # reduction of rainfall due to infiltration and evaporation = neerslagverliezen: only in summer
    if input.time_of_year == "summer":
        # See E.3 from HKV PR4991.10
        # Het neerslagverlies wordt in
        # mindering gebracht op de neerslag die valt op de eerste twee dagen van het neerslagpatroon. De
        # neerslag op beide dagen wordt met eenzelfde percentage verminderd. Dit percentage wordt
        # berekend door 20 mm te delen door de som van de neerslag op beide dagen
        # TODO: make adjustable later by user
        available_storage_phreatic_layer = 300  # mm
        storage_coefficient = 0.04  # [-]
        storage_phreatic_layer = available_storage_phreatic_layer * storage_coefficient
        evaporation = 8  # mm
        loss_rainfall = storage_phreatic_layer + evaporation
        # only loss in the first two days
        rain_first_two_days = sum(rainfall_per_day[:2])
        reduction_factor = loss_rainfall / rain_first_two_days
        rainfall_per_day[:2] = [
            x * (1 - reduction_factor) for x in rainfall_per_day[:2]
        ]

    # final computation:
    flow_per_day: np.ndarray = (model_matrix * rainfall_per_day).sum(axis=1)
    return flow_per_day, rainfall_per_day, model_matrix, volume_rain_mm


def _get_disposal_curve(days_to_dispose) -> list:
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
    return data[days_to_dispose]


def get_sum_rainfall_stats(
    return_period: int,
    time_of_year: str,
    length_event_hrs: int,
    rainfall_regime: str,
) -> dict:
    """Get sum rainfall statistics for a specific return period and time of year."""
    # Placeholder implementation
    if time_of_year == "summer":
        data = _get_sum_summer_dict()
    elif time_of_year == "winter":
        data = _get_sum_winter_dict()
    else:
        raise ValueError("time_of_year must be 'summer' or 'winter'")

    rainfall_regimes_correction_factor = _get_rainfall_regime_correction_factor(
        time_of_year, rainfall_regime
    )

    # df has return periods on the x-axis and length on the y-axis
    df_stats = pd.DataFrame(data)
    volume = (
        df_stats.loc[return_period, length_event_hrs]
        * rainfall_regimes_correction_factor
    )
    return volume


def get_rainfall_pattern(
    time_of_year: str,
    length_event_hrs: int,
    name_rainfall_pattern: str,
) -> dict:
    """Get sum rainfall statistics for a specific return period and time of year."""
    # Placeholder implementation

    data = _get_pattern_dict(length_event_hrs, time_of_year)

    # df has return periods on the x-axis and length on the y-axis
    df_patterns = pd.DataFrame(data).T
    rainfall_pattern = df_patterns.loc[name_rainfall_pattern]
    return rainfall_pattern


def _get_rainfall_regime_correction_factor(time_of_year: str, regime: str) -> dict:
    """Get correction factors for rainfall regimes.

    From HKV PR4991.10 • september 2024:  Tabel 3
    'Correctiefactoren van de neerslagregimes voor het
    winter- en zomerhalfjaar (gehele jaar). Bron: STOWA 2019.'
    """
    # If updated: ensure to fix the model_validators & constants in base_rule_of_thumb.py
    data = {
        "winter": {"LL": 0.82, "L": 0.9, "R": 1, "H": 1.08},
        # voor de zomer gelden de factoren voor het gehele jaar,
        # voor regionale spreiding is de zomer dominant (lokale onweer systemen)
        "summer": {"LL": 1, "L": 0.92, "R": 1, "H": 1.09},  #
    }
    return data[time_of_year][regime]


def _get_sum_winter_dict() -> dict:
    """From HKV PR4991.10 • september 2024: Tabel 38

    'Extremen gebiedsneerslag (mm) gedurende het gehele jaar en het winterhalfjaar voor duren van 2
    t/m 8 dagen, die gemiddeld 2 maal per jaar tot gemiddeld eens per 1000 jaar worden
    overschreden. (bewerking van Tabel 36 met in de zomer het neerslagverlies van 20 mm en de
    reductiefactoren van Tabel 6 uit deel 4 STOWA, 2019).'
    """
    # If updated: ensure to fix the model_validators & constants in base_rule_of_thumb.py
    return {
        48.0: {
            0.5: 29.0,
            1.0: 34.4,
            2.0: 40.1,
            5.0: 48.0,
            10.0: 54.2,
            20.0: 60.7,
            25.0: 62.9,
            50.0: 69.7,
            100.0: 76.8,
            200.0: 84.1,
            250.0: 86.6,
            500.0: 94.3,
            1000.0: 102.4,
        },
        96.0: {
            0.5: 39.5,
            1.0: 47.0,
            2.0: 54.7,
            5.0: 65.1,
            10.0: 73.0,
            20.0: 81.1,
            25.0: 83.8,
            50.0: 92.0,
            100.0: 100.4,
            200.0: 108.9,
            250.0: 111.7,
            500.0: 120.4,
            1000.0: 129.2,
        },
        192.0: {
            0.5: 54.8,
            1.0: 65.6,
            2.0: 76.0,
            5.0: 89.4,
            10.0: 99.1,
            20.0: 108.5,
            25.0: 111.5,
            50.0: 120.5,
            100.0: 129.3,
            200.0: 137.7,
            250.0: 140.4,
            500.0: 148.5,
            1000.0: 156.4,
        },
    }


def _get_sum_summer_dict() -> dict:
    """From HKV PR4991.10 • september 2024: Tabel 38

    'Extremen gebiedsneerslag (mm) gedurende het gehele jaar en het winterhalfjaar voor duren van 2
    t/m 8 dagen, die gemiddeld 2 maal per jaar tot gemiddeld eens per 1000 jaar worden
    overschreden. (bewerking van Tabel 36 met in de zomer het neerslagverlies van 20 mm en de
    reductiefactoren van Tabel 6 uit deel 4 STOWA, 2019).'

    """
    # If updated: ensure to fix the model_validators & constants in base_rule_of_thumb.py
    return {
        48.0: {
            0.5: 16.0,
            1.0: 22.0,
            2.0: 28.0,
            5.0: 36.0,
            10.0: 43.0,
            20.0: 50.0,
            25.0: 53.0,
            50.0: 61.0,
            100.0: 70.7,
            200.0: 81.1,
            250.0: 84.6,
            500.0: 96.0,
            1000.0: 108.2,
        },
        96.0: {
            0.5: 29.0,
            1.0: 35.0,
            2.0: 42.0,
            5.0: 51.0,
            10.0: 59.0,
            20.0: 66.0,
            25.0: 69.0,
            50.0: 77.0,
            100.0: 86.6,
            200.0: 96.5,
            250.0: 99.7,
            500.0: 110.1,
            1000.0: 120.9,
        },
        192.0: {
            0.5: 47.0,
            1.0: 55.0,
            2.0: 63.0,
            5.0: 73.0,
            10.0: 81.0,
            20.0: 89.0,
            25.0: 92.0,
            50.0: 99.0,
            100.0: 108.1,
            200.0: 117.2,
            250.0: 120.2,
            500.0: 129.3,
            1000.0: 138.4,
        },
    }


def _load_rainfall_patterns() -> dict:
    file_dir = Path(__file__).parent
    with open(file_dir / "rainfall_patterns.json", "r") as f:
        data = json.load(f)
    return data


def _get_pattern_dict(length_event_hrs, time_of_year) -> dict:
    data = _load_rainfall_patterns()
    return data[time_of_year][str(int(length_event_hrs))]

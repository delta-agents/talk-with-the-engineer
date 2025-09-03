"""
Utility functions for the Talk with the engineer.

Provides utils for rainfall statistics needed in multiple tools.
"""

import pandas as pd


def get_rainfall_stats(
    return_period: int,
    time_of_year: str,
    length_event_hrs: int,
    rainfall_regime: str,
) -> dict:
    """Get rainfall statistics for a specific return period and time of year."""
    # Placeholder implementation
    if time_of_year == "summer":
        data = _get_summer_dict()
    elif time_of_year == "winter":
        data = _get_winter_dict()
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


def _get_rainfall_regime_correction_factor(time_of_year: str, regime: str) -> dict:
    """Get correction factors for rainfall regimes.

    From HKV PR4991.10 • september 2024:  Tabel 3
    'Correctiefactoren van de neerslagregimes voor het
    winter- en zomerhalfjaar (gehele jaar). Bron: STOWA 2019.'
    """
    data = {
        "winter": {"LL": 0.82, "L": 0.9, "R": 1, "H": 1.08},
        # voor de zomer gelden de factoren voor het gehele jaar, 
        # voor regionale spreiding is de zomer dominant (lokale onweer systemen)
        "summer": {"LL": 1, "L": 0.92, "R": 1, "H": 1.09}, #
    }
    return data[time_of_year][regime]


def _get_winter_dict() -> dict:
    """From HKV PR4991.10 • september 2024: Tabel 38

    'Extremen gebiedsneerslag (mm) gedurende het gehele jaar en het winterhalfjaar voor duren van 2
    t/m 8 dagen, die gemiddeld 2 maal per jaar tot gemiddeld eens per 1000 jaar worden
    overschreden. (bewerking van Tabel 36 met in de zomer het neerslagverlies van 20 mm en de
    reductiefactoren van Tabel 6 uit deel 4 STOWA, 2019).'
    """
    # If updated: ensure to fix the model_validators
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


def _get_summer_dict() -> dict:
    """From HKV PR4991.10 • september 2024: Tabel 38

    'Extremen gebiedsneerslag (mm) gedurende het gehele jaar en het winterhalfjaar voor duren van 2
    t/m 8 dagen, die gemiddeld 2 maal per jaar tot gemiddeld eens per 1000 jaar worden
    overschreden. (bewerking van Tabel 36 met in de zomer het neerslagverlies van 20 mm en de
    reductiefactoren van Tabel 6 uit deel 4 STOWA, 2019).'

    """
    # If updated: ensure to fix the model_validators
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

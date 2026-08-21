"""Waterbalans van een polder: de rekenkern van de vuistregels.

Drie stappen, elk gevectoriseerd:

1. `delay_daily`  - vertraag de afvoer van een deel van het gebied (maatregel vasthouden)
2. `water_level_series` - de waterbalans zelf
3. `max_water_level` - de maximale waterstandstijging, waar de vuistregels op sturen

De uitkomsten zijn gevalideerd tegen `scripts/scripts_Ton/TttE_v03.xlsx`; zie
tests/src/tools/test_reference_ton.py.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    _get_discharge_curve,
    _get_model_matrix,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)

HOURS_PER_DAY = 24
M3_PER_SEC_PER_L_PER_SEC_PER_HA = (
    1e-3  # l/s/ha maal ha geeft l/s, gedeeld door 1000 m3/s
)
SQUARE_METRES_PER_HECTARE = 1e4
SECONDS_PER_HOUR = 3600


def water_level_series(
    drainage_l_s_ha: np.ndarray,
    area_open_water_ha: float,
    area_land_ha: float,
    pump_capacity_m3_per_sec: float,
    inflow_m3_per_sec: np.ndarray | None = None,
    direct_precipitation_m: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Waterstandstijging boven streefpeil [m] en werkelijk verplaatst debiet [m3/s].

    De onderliggende recursie is

        h[0] = 0,  h[t] = max(h[t-1] + d[t], 0)

    met `d[t]` de peilverandering per uur als het gemaal op capaciteit draait. Dat is een
    gereflecteerde random walk, en daarvoor geldt exact

        h[t] = S[t] - min(S[0..t])   met   S = cumsum(d)

    Het gemaal draait alleen als er water is. De toenames van `min(S[0..t])` zijn precies
    de ongebruikte gemaalcapaciteit, en dus is het werkelijk verplaatste debiet af te
    leiden uit dezelfde grootheid. Dat tweede is nodig zodra polders in een cascade staan:
    wat de een wegpompt is de aanvoer van de ander.

    Het rekenblad gebruikt `Q[t-1]` waar deze functie `Q[t]` gebruikt. De reeks is daarmee
    een tijdstap verschoven; het maximum is identiek en alleen het maximum wordt gebruikt.
    """
    if area_open_water_ha <= 0:
        raise ValueError("area_open_water_ha moet groter dan nul zijn")

    inflow = np.asarray(drainage_l_s_ha, dtype=float) * area_land_ha
    inflow *= M3_PER_SEC_PER_L_PER_SEC_PER_HA
    if inflow_m3_per_sec is not None:
        inflow = inflow + np.asarray(inflow_m3_per_sec, dtype=float)

    # peilverandering per uur bij een gemaal dat op capaciteit draait
    metres_per_m3_per_sec = SECONDS_PER_HOUR / (
        area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )
    delta = (inflow - pump_capacity_m3_per_sec) * metres_per_m3_per_sec
    if direct_precipitation_m is not None:
        delta = delta + np.asarray(direct_precipitation_m, dtype=float)

    cumulative = np.concatenate([[0.0], np.cumsum(delta)])
    running_minimum = np.minimum.accumulate(cumulative)

    water_level_m = cumulative - running_minimum
    unused_capacity_m = np.diff(running_minimum)  # <= 0
    pumped_m3_per_sec = (
        pump_capacity_m3_per_sec + unused_capacity_m / metres_per_m3_per_sec
    )
    return water_level_m[1:], pumped_m3_per_sec


def max_water_level(
    drainage_l_s_ha: np.ndarray,
    area_open_water_ha: float,
    area_land_ha: float,
    pump_capacity_m3_per_sec: float,
    inflow_m3_per_sec: np.ndarray | None = None,
) -> float:
    """De maximale waterstandstijging [m]; de grootheid waar de vuistregels op sturen."""
    water_level_m, _ = water_level_series(
        drainage_l_s_ha,
        area_open_water_ha,
        area_land_ha,
        pump_capacity_m3_per_sec,
        inflow_m3_per_sec,
    )
    return float(water_level_m.max())


def delay_daily(daily: np.ndarray, days_to_retain: int) -> np.ndarray:
    """Spreid elke dagafvoer uit over `1 + days_to_retain` dagen.

    Massaconserverend per constructie: de kernel telt op tot 1, dus het totale volume
    verandert niet. De uitvoer is `days_to_retain` dagen langer dan de invoer, want de
    staart schuift door.

    Dit vervangt een schema van negen hardgecodeerde 24-uursblokken dat een vast venster
    van drie dagen gebruikte met een factor `1/(1 + days_to_retain)`. Massa bleef daarmee
    alleen behouden bij `days_to_retain = 2`, en het schema indexeerde hard tot uur 216
    waardoor het op kortere reeksen omviel. Bij `days_to_retain = 2` geeft deze
    convolutie dezelfde waarden als dat schema.
    """
    if days_to_retain < 0:
        raise ValueError("days_to_retain kan niet negatief zijn")
    window = 1 + days_to_retain
    return np.convolve(np.asarray(daily, dtype=float), np.ones(window) / window)


def to_daily(hourly: np.ndarray) -> np.ndarray:
    """Sample een uurreeks die per dag constant is terug naar dagwaarden."""
    hourly = np.asarray(hourly, dtype=float)
    if len(hourly) % HOURS_PER_DAY:
        raise ValueError(f"uurreeks van {len(hourly)} uur is geen heel aantal dagen")
    return hourly.reshape(-1, HOURS_PER_DAY)[:, 0]


def to_hourly(daily: np.ndarray) -> np.ndarray:
    """Herhaal dagwaarden naar uurwaarden."""
    return np.repeat(np.asarray(daily, dtype=float), HOURS_PER_DAY)


def blend_retention(
    drainage_daily: np.ndarray, days_to_retain: int, retention_fraction: float
) -> np.ndarray:
    """Meng de onvertraagde en de vertraagde afvoer naar rato van het retentie-areaal.

    `retention_fraction` is de fractie van het LANDoppervlak waarvan de afvoer wordt
    vertraagd; de rest van het gebied voert onvertraagd af.
    """
    if not 0.0 <= retention_fraction <= 1.0:
        raise ValueError(
            f"retention_fraction moet tussen 0 en 1 liggen, kreeg {retention_fraction}"
        )
    if retention_fraction == 0.0:
        return np.asarray(drainage_daily, dtype=float)

    delayed = delay_daily(drainage_daily, days_to_retain)
    undelayed = np.zeros_like(delayed)
    undelayed[: len(drainage_daily)] = drainage_daily
    return (1.0 - retention_fraction) * undelayed + retention_fraction * delayed


@dataclass
class SimulationResult:
    """Uitkomst van een doorrekening; `dh_max_m` is waar de vuistregels op sturen."""

    dh_max_m: float
    water_level_m: np.ndarray
    pumped_m3_per_sec: np.ndarray
    drainage_l_s_ha: np.ndarray
    rainfall_per_day_mm: np.ndarray
    """Neerslag op het land, dus na aftrek van het zomerse neerslagverlies."""
    rainfall_on_water_per_day_mm: np.ndarray
    """Neerslag op het open water, zonder aftrek; in de winter gelijk aan de vorige."""
    volume_rain_mm: float


def drainage_per_day(storm, rainfall_per_day_mm: np.ndarray) -> np.ndarray:
    """Neerslag-afvoerrelatie: dagneerslag [mm] naar dagafvoer [mm]."""
    discharge_curve = _get_discharge_curve(storm.days_to_discharge)
    flow_per_day, _ = _get_model_matrix(storm, rainfall_per_day_mm, discharge_curve)
    return flow_per_day


@lru_cache(maxsize=None)
def _drainage_daily_for_storm(
    return_period,
    time_of_year,
    length_event_hrs,
    rainfall_regime,
    name_rainfall_pattern,
    days_to_discharge,
    apply_summer_loss,
):
    """Dagafvoer en neerslag voor een bui, met en zonder neerslagverlies.

    Het zomerse neerslagverlies is een bodemproces - infiltratie in het freatisch pakket
    plus verdamping - en geldt dus alleen voor de neerslag die op het land valt. De
    neerslag die direct op het open water valt gaat er ongereduceerd in: er is geen bodem
    om in te zakken. Bevestigd door Ton Botterhuis, augustus 2026. Daarom twee reeksen.

    Gecacht om dezelfde reden als `_rainfall_for_storm`: de inverse tools rekenen een bui
    tientallen keren door en de bui verandert daarbij niet, alleen de toestand.
    """
    storm = _StormKey(
        return_period,
        time_of_year,
        length_event_hrs,
        rainfall_regime,
        name_rainfall_pattern,
        days_to_discharge,
    )
    # neerslag op land: met verlies, want daar zakt het in de bodem
    rainfall_on_land_mm, volume_rain_mm = get_rainfall(
        storm, apply_summer_loss=apply_summer_loss
    )
    # neerslag op open water: zonder verlies. In de winter zijn beide gelijk.
    rainfall_on_water_mm, _ = get_rainfall(storm, apply_summer_loss=False)
    return (
        drainage_per_day(storm, rainfall_on_land_mm),
        rainfall_on_land_mm,
        rainfall_on_water_mm,
        volume_rain_mm,
    )


@dataclass(frozen=True)
class _StormKey:
    """Minimale bui-representatie; wat `get_rainfall` en de modelmatrix nodig hebben."""

    return_period: int
    time_of_year: str
    length_event_hrs: float
    rainfall_regime: str
    name_rainfall_pattern: str
    days_to_discharge: int


def simulate(
    state: PolderState,
    storm,
    inflow_m3_per_sec: np.ndarray | None = None,
    apply_summer_loss: bool = True,
) -> SimulationResult:
    """Reken een bui door op een polder-toestand.

    Dit is de transitie `f(s, w)`. Maatregelen zitten niet in deze functie: die veranderen
    de toestand die erin gaat (zie `models/modelset_rules_of_thumb/actions.py`).
    """
    (
        drainage_daily_mm,
        rainfall_per_day_mm,
        rainfall_on_water_per_day_mm,
        volume_rain_mm,
    ) = _drainage_daily_for_storm(
        storm.return_period,
        storm.time_of_year,
        storm.length_event_hrs,
        storm.rainfall_regime,
        storm.name_rainfall_pattern,
        storm.days_to_discharge,
        apply_summer_loss,
    )

    if state.retention_fraction > 0:
        drainage_daily_mm = blend_retention(
            drainage_daily_mm, state.days_to_retain, state.retention_fraction
        )

    # mm/dag -> mm/uur -> l/s/ha
    drainage_l_s_ha = to_hourly(drainage_daily_mm / HOURS_PER_DAY * 10 / 3.6)

    # Neerslag die direct op het open water valt, verhoogt de stand met exact de
    # neerslagdiepte: het volume is P/1000 maal het oppervlak, en gedeeld door datzelfde
    # oppervlak blijft P/1000 m over. Onvertraagd, want er is geen bodem om door te
    # sijpelen, en zonder neerslagverlies om dezelfde reden. Het rekenblad laat deze term
    # weg; zie WaterBalanceMode.
    direct_precipitation_m = None
    if state.includes_direct_precipitation:
        per_hour_m = to_hourly(rainfall_on_water_per_day_mm / HOURS_PER_DAY) / 1000.0
        direct_precipitation_m = np.zeros(len(drainage_l_s_ha))
        overlap = min(len(per_hour_m), len(direct_precipitation_m))
        direct_precipitation_m[:overlap] = per_hour_m[:overlap]

    water_level_m, pumped_m3_per_sec = water_level_series(
        drainage_l_s_ha,
        state.area_open_water_ha,
        state.area_land_ha,
        state.pump_capacity_m3_per_sec,
        inflow_m3_per_sec,
        direct_precipitation_m,
    )
    return SimulationResult(
        dh_max_m=float(water_level_m.max()),
        water_level_m=water_level_m,
        pumped_m3_per_sec=pumped_m3_per_sec,
        drainage_l_s_ha=drainage_l_s_ha,
        rainfall_per_day_mm=rainfall_per_day_mm,
        rainfall_on_water_per_day_mm=rainfall_on_water_per_day_mm,
        volume_rain_mm=float(volume_rain_mm),
    )

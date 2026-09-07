"""De neerslagstatistiek: de bron waaruit een bui wordt getrokken.

STOWA-2019, deelrapport 3 - de som per buiduur en het patroon erbinnen.

De trekking zelf is een `Storm`; deze module weet hoe je hem opzoekt en verder niets. Alles
achter `get_rainfall` rekent met losse getallen, want een bui is volledig bepaald door zeven
waarden en dat maakt de opzoeking cachebaar.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from talk_with_the_engineer.core.exogenous import Storm


logger = logging.getLogger("AI_agent")


def get_rainfall(storm: Storm, apply_summer_loss: bool = True):
    """Neerslag per dag [mm] en het totaalvolume [mm] voor een bui.

    `apply_summer_loss` bestaat omdat nog niet vaststaat of het neerslagverlies al in
    Tabel 38 verwerkt zit; met False kan de andere interpretatie doorgerekend worden.
    """
    rainfall_per_day, volume_rain_mm = _rainfall_for_storm(
        storm.return_period,
        storm.time_of_year,
        storm.length_event_hrs,
        storm.rainfall_regime,
        storm.name_rainfall_pattern,
        apply_summer_loss,
        storm.rain_volume_mm,
    )
    # de cache levert steeds hetzelfde array; aanroepers mogen erin schrijven
    return rainfall_per_day.copy(), volume_rain_mm


@lru_cache(maxsize=None)
def _rainfall_for_storm(
    return_period: int | None,
    time_of_year: str,
    length_event_hrs: float,
    rainfall_regime: str,
    name_rainfall_pattern: str,
    apply_summer_loss: bool,
    rain_volume_mm: float | None = None,
):
    """Neerslag per dag voor een bui. Gecacht: een bui is volledig bepaald door deze zeven
    waarden, en de inverse tools rekenen dezelfde bui tientallen keren door.

    Twee wegen naar de neerslagsom, en verder verandert er niets. Met `rain_volume_mm` komt
    de som van de beller en wordt de tabel niet geraadpleegd; de duur, het patroon en de
    zomerverliesregel gelden onverkort. Dat is dezelfde vorm als op de droge kant, waar het
    droogtetripel alleen `deficit_mm_per_day` invult en de rest van de som laat staan.

    Het regime hoort bij de OPZOEKING - `get_sum_rainfall_stats` vermenigvuldigt de
    tabelwaarde ermee - dus bij een eigen som doet hij niets. Het invoermodel weigert de
    combinatie, zodat dat geen stille wijziging kan worden.
    """
    if rain_volume_mm is not None:
        volume_rain_mm = float(rain_volume_mm)
    else:
        volume_rain_mm = get_sum_rainfall_stats(
            return_period=return_period,
            time_of_year=time_of_year,
            length_event_hrs=length_event_hrs,
            rainfall_regime=rainfall_regime,
        )

    length_rainfall_days = int(length_event_hrs / 24)

    rainfall_pattern = get_rainfall_pattern(
        time_of_year=time_of_year,
        length_event_hrs=length_event_hrs,
        name_rainfall_pattern=name_rainfall_pattern,
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
    if time_of_year == "summer" and apply_summer_loss:
        rainfall_per_day = _subtract_summer_loss(rainfall_per_day)

    return rainfall_per_day, volume_rain_mm


# Neerslagverlies in de zomer [mm]. Van elke bui is 20 mm niet terug te vinden in het open
# water: dat blijft in het gebied hangen. Zie E.3 van Waterveiligheidsperspectief IJsselmeer.
#
# **Dit is een eigenschap van het GEBIED en niet van de neerslag.** Het getal staat in deze
# module omdat het hier op de neerslagreeks in mindering wordt gebracht, maar het beschrijft
# wat het oppervlak van dit gebied vasthoudt - berging in de onverzadigde zone, plassen,
# interceptie, verdamping tijdens de bui - en niet iets wat de bui doet. Een andere bui in
# hetzelfde gebied verliest dezelfde 20 mm; hetzelfde neerslagpatroon in een ander gebied
# niet. Dat onderscheid stuurt hoe de tools het terugkoppelen: het hoort bij de
# gebiedskarakterisering, naast `percentage_open_water`, en niet bij de buikeuze.
#
# Vandaag is het een landelijke vuistregel en geen gebiedsafhankelijke waarde: 20 mm voor
# elk gebied. Dat is een modelleringskeuze en geen berekening, en het is precies de plek
# waar een gebiedseigen getal hoort te komen zodra dat er is.
#
# **Los van de bergingscoefficient.** De bergingscoefficient is de GRONDWATERcomponent - hoe
# veel voorraad een meter grondwaterstandsdaling vrijmaakt - en die zit in dit model
# helemaal niet. Deze 20 mm is oppervlaktewater dat niet tot afvoer komt.
#
# Ze door elkaar halen zou dubbeltellen, en de verleiding is er: 300 mm freatische berging
# maal een bergingscoefficient van 0,04 plus 8 mm verdamping komt ook rond de 20 mm uit.
# Dat is een andere grootheid met bijna hetzelfde getal, en die afleiding hoort hier niet.
#
# Bevestigd door Ton Botterhuis, augustus 2026.
SUMMER_LOSS_MM = 20.0


def _subtract_summer_loss(rainfall_per_day: np.ndarray) -> np.ndarray:
    """Breng het neerslagverlies in mindering op de eerste twee dagen.

    De regel uit E.3 van Waterveiligheidsperspectief IJsselmeer: "Het neerslagverlies wordt in mindering gebracht
    op de neerslag die valt op de eerste twee dagen van het neerslagpatroon. De neerslag
    op beide dagen wordt met eenzelfde percentage verminderd. Dit percentage wordt
    berekend door 20 mm te delen door de som van de neerslag op beide dagen."

    Het verlies blijft op die eerste twee dagen en wordt niet doorgeschoven: neerslag die
    op de derde dag valt komt volledig ten goede aan de afstroming. Valt er in de eerste
    twee dagen minder dan 20 mm - bij een achtdaags patroon dragen dag 1 en 2 samen maar
    12 % van de bui - dan wordt er dus minder dan 20 mm afgehaald, en nooit meer dan er
    valt. Dat voorkomt de negatieve neerslag die er eerder uitkwam.

    Bevestigd door Ton Botterhuis, augustus 2026.
    """
    rainfall_per_day = rainfall_per_day.astype(float).copy()
    rain_first_two_days = float(rainfall_per_day[:2].sum())
    if rain_first_two_days <= 0:
        return rainfall_per_day

    loss_mm = min(SUMMER_LOSS_MM, rain_first_two_days)
    reduction_factor = loss_mm / rain_first_two_days
    rainfall_per_day[:2] = rainfall_per_day[:2] * (1 - reduction_factor)
    return rainfall_per_day


@lru_cache(maxsize=None)
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


@lru_cache(maxsize=None)
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


@lru_cache(maxsize=None)
def _get_rainfall_regime_correction_factor(time_of_year: str, regime: str) -> dict:
    """Get correction factors for rainfall regimes.

    From Waterveiligheidsperspectief IJsselmeer (HKV, september 2024): Tabel 3
    'Correctiefactoren van de neerslagregimes voor het
    winter- en zomerhalfjaar (gehele jaar). Bron: STOWA 2019.'

    Deze getallen komen rechtstreeks uit de STOWA-tabel en zijn geen keuze van ons.
    Dat de jaarrondrij niet monotoon is - LL staat op 1,00 en dus boven L op 0,92 -
    zit in de bron. Bevestigd door Ton Botterhuis, augustus 2026.
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
    """From Waterveiligheidsperspectief IJsselmeer (HKV, september 2024): Tabel 38

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
    """Jaarrondstatistiek, gebruikt als benadering van de zomer.

    Tabel 38 heeft twee kolommen - gehele jaar en winterhalfjaar - en geen
    zomerhalfjaarkolom. Wat hier "summer" heet is dus de **jaarrondstatistiek**. Dat is
    verdedigbaar omdat de zomer dominant is in de puntstatistiek van de weerstations: de
    extremere neerslagen komen uit zomerse onweersbuien. Bevestigd door Ton Botterhuis,
    augustus 2026.

    Gevolg voor de uitvoer: een "zomerbui eens per 100 jaar" is strikt genomen een
    jaarrondbui eens per 100 jaar. Voor lange duren is dat een wezenlijk verschil, want
    dan domineert de winter - bij 192 uur en T=100 staat hier 108,1 mm tegen 129,3 mm voor
    het winterhalfjaar.

    From Waterveiligheidsperspectief IJsselmeer (HKV, september 2024): Tabel 38

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


@lru_cache(maxsize=None)
def _load_rainfall_patterns() -> dict:
    file_dir = Path(__file__).parent
    with open(file_dir / "rainfall_patterns.json", "r") as f:
        data = json.load(f)
    return data


@lru_cache(maxsize=None)
def _get_pattern_dict(length_event_hrs, time_of_year) -> dict:
    data = _load_rainfall_patterns()
    return data[time_of_year][str(int(length_event_hrs))]

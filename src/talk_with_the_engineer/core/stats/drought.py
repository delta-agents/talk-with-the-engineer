"""Toegang tot de droogtestatistiek uit STOWA 2025-23.

`drought_statistics.json` bevat, per waterschap en per KNMI'23-scenario, het maximaal
cumulatief neerslagtekort [mm] bij een set herhaaltijden, en daarnaast de
beschikbaarheidsfractie van de Rijn en de Maas bij diezelfde herhaaltijden - de vraag en het
aanbod op dezelfde as. Zie het `meta`-blok in dat bestand voor bron, eenheid, seizoen en de
aannames. De data is opgebouwd met
`scratchpad/build_drought_statistics.py` uit de per-waterschap Excels; dit bestand is de
enige toegang ertoe in de code, gespiegeld op `load_rainfall_patterns` in `utils_rainfall`.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple


@lru_cache(maxsize=None)
def load_drought_statistics() -> dict:
    file_dir = Path(__file__).parent
    with open(file_dir / "drought_statistics.json", "r") as f:
        data = json.load(f)
    return data


def available_regions() -> list[str]:
    """De waterschappen waarvoor droogtestatistiek beschikbaar is."""
    return sorted(load_drought_statistics()["regions"])


def available_scenarios(region: str) -> list[str]:
    """De KNMI'23-scenario's (incl. Referentie) voor dit waterschap."""
    return sorted(load_drought_statistics()["regions"][region])


def available_return_periods() -> tuple[int, ...]:
    """De herhaaltijden waarvoor het bestand een waarde bijhoudt."""
    data = load_drought_statistics()
    any_region = next(iter(data["regions"].values()))
    any_scenario = next(iter(any_region.values()))
    return tuple(int(key) for key in any_scenario["return_periods"])


def cumulative_deficit_mm(
    region: str, scenario: str, return_period: int
) -> float | None:
    """Het maximaal cumulatief neerslagtekort [mm] bij deze herhaaltijd.

    Drie uitkomsten, en het verschil doet ertoe:

    * een **getal**: het tekort bij deze herhaaltijd, afgelezen op de GEV-fit;
    * **`None`**: deze herhaaltijd valt buiten de 240-jarige RACMO-reeks van dít scenario.
      Dat komt voor - bij de natste scenario's is T100 niet bereikt en bij de droogste ligt
      T2 onder de reeks - en extrapoleren zou een getal verzinnen waar het rapport er geen
      heeft;
    * een **`KeyError`**: onbekende regio, scenario of herhaaltijd. Dat is een fout in de
      aanroep en geen ontbrekende statistiek, en die twee horen niet op dezelfde manier
      terug te komen.
    """
    data = load_drought_statistics()
    try:
        table = data["regions"][region][scenario]["return_periods"]
    except KeyError as exc:
        raise KeyError(
            f"onbekende regio/scenario ({region!r}, {scenario!r}); "
            f"zie available_regions() en available_scenarios()"
        ) from exc
    key = str(int(return_period))
    if key not in table:
        raise KeyError(
            f"herhaaltijd {return_period} wordt niet bijgehouden; "
            f"beschikbaar zijn {available_return_periods()}"
        )
    return table[key]


class SourceAvailability(NamedTuple):
    """Het aanbod bij een droogte van deze zeldzaamheid, ten opzichte van een normaal jaar.

    Vier getallen en niet een, want de fractie alleen zou hier meer beloven dan de statistiek
    draagt: `fit_r` ligt rond -0,3, dus de spreiding is geen detail maar de helft van het
    antwoord.
    """

    fraction: float
    """Het aanbod als fractie van een normaal jaar; 1 is een normaal jaar, 0,6 is 40 % minder."""
    spread_low: float
    """De p10-rand van de fit, als FACTOR op de fractie - dus 0,80 betekent 20 % minder."""
    spread_high: float
    """De p90-rand, als factor op de fractie."""
    fit_r: float
    """De correlatie van de fit in log-log; dichter bij nul is minder verband."""


def available_rivers() -> tuple[str, ...]:
    """De rivieren waarvoor het bestand een beschikbaarheidsfractie bijhoudt."""
    data = load_drought_statistics()
    any_region = next(iter(data["regions"].values()))
    any_scenario = next(iter(any_region.values()))
    return tuple(sorted(any_scenario["source_availability"]))


def normal_year_discharge_m3_per_sec(river: str) -> float:
    """De minimale 7-daagse afvoer in een normaal jaar [m3/s], waarop de fractie slaat.

    Landelijk en niet per waterschap: de rivier is voor iedereen dezelfde rivier. Alleen de
    KOPPELING tussen droogte en rivier is regionaal, want de herhaaltijd van het tekort is dat.
    """
    table = load_drought_statistics()["meta"]["source_availability"][
        "normal_year_m3_per_sec"
    ]
    try:
        return table[river]
    except KeyError as exc:
        raise KeyError(f"onbekende rivier ({river!r}); zie available_rivers()") from exc


def source_availability(
    region: str, scenario: str, return_period: int, river: str
) -> SourceAvailability | None:
    """Het aanbod bij deze droogte, als fractie van een normaal jaar.

    Dezelfde drie uitkomsten als `cumulative_deficit_mm`, en om dezelfde redenen:

    * een **`SourceAvailability`**: de fractie bij deze herhaaltijd, plus de spreiding en de
      sterkte van het verband;
    * **`None`**: deze herhaaltijd valt buiten de reeks van dit scenario. Dat loopt gelijk op
      met het tekort - waar geen droogte staat, staat ook geen aanbod;
    * een **`KeyError`**: onbekende regio, scenario, herhaaltijd of rivier.

    Let op wat dit getal WEL en NIET is. Het is een index van de rivier, conditioneel op een
    droogte van deze zeldzaamheid in dit waterschap. Het is niet het volume bij een inlaat:
    daartussen zitten het verdeelnetwerk, het Distributiemodel en de verdringingsreeks, en die
    zitten hier niet in.
    """
    data = load_drought_statistics()
    try:
        block = data["regions"][region][scenario]["source_availability"]
    except KeyError as exc:
        raise KeyError(
            f"onbekende regio/scenario ({region!r}, {scenario!r}); "
            f"zie available_regions() en available_scenarios()"
        ) from exc
    try:
        river_block = block[river]
    except KeyError as exc:
        raise KeyError(f"onbekende rivier ({river!r}); zie available_rivers()") from exc
    key = str(int(return_period))
    if key not in river_block["return_periods"]:
        raise KeyError(
            f"herhaaltijd {return_period} wordt niet bijgehouden; "
            f"beschikbaar zijn {available_return_periods()}"
        )
    fraction = river_block["return_periods"][key]
    if fraction is None:
        return None
    low, high = river_block["spread_factor"]
    return SourceAvailability(
        fraction=fraction,
        spread_low=low,
        spread_high=high,
        fit_r=river_block["fit_r"],
    )

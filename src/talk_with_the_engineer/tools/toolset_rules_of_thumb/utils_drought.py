"""Toegang tot de droogtestatistiek uit STOWA 2025-23.

`drought_statistics.json` bevat, per waterschap en per KNMI'23-scenario, het maximaal
cumulatief neerslagtekort [mm] bij een set herhaaltijden. Zie het `meta`-blok in dat bestand
voor bron, eenheid, seizoen en de aannames. De data is opgebouwd met
`scratchpad/build_drought_statistics.py` uit de per-waterschap Excels; dit bestand is de
enige toegang ertoe in de code, gespiegeld op `_load_rainfall_patterns` in `utils_rainfall`.
"""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def _load_drought_statistics() -> dict:
    file_dir = Path(__file__).parent
    with open(file_dir / "drought_statistics.json", "r") as f:
        data = json.load(f)
    return data


def available_regions() -> list[str]:
    """De waterschappen waarvoor droogtestatistiek beschikbaar is."""
    return sorted(_load_drought_statistics()["regions"])


def available_scenarios(region: str) -> list[str]:
    """De KNMI'23-scenario's (incl. Referentie) voor dit waterschap."""
    return sorted(_load_drought_statistics()["regions"][region])


def available_return_periods() -> tuple[int, ...]:
    """De herhaaltijden waarvoor het bestand een waarde bijhoudt."""
    data = _load_drought_statistics()
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
    data = _load_drought_statistics()
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

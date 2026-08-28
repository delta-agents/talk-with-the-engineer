"""Toegang tot de vraagpostverdeling uit de werkopgave 2025 (Deltaprogramma Zoetwater).

`demand_posts.json` bevat, per DPZW-regio, scenario en herhaaltijd, het AANDEEL van vier
watervraagposten - doorspoeling boezem, doorspoeling polders, peilbeheer en beregening - in
de totale watervraag, plus per post hoeveel van die vraag geleverd wordt en welk deel van het
tekort erbij hoort. Zie het `meta`-blok in dat bestand voor bron, status en methode.

**Alles hier is dimensieloos.** De bron staat in Mm3 per zomer en dit model in mm over een
gebied; zonder een tabel met regio-oppervlakken is dat niet om te rekenen. Verhoudingen zijn
dat wel, en daarom komen alleen verhoudingen deze kant op. Dit bestand is de enige toegang
tot de data, gespiegeld op `utils_drought` voor de droogtestatistiek.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

DEMAND_POST_NAMES = (
    "doorspoeling_boezem",
    "doorspoeling_polders",
    "peilbeheer",
    "beregening",
)
"""De vier posten, in de volgorde waarin ze in de uitvoer verschijnen.

`doorspoeling` als geheel is de som van de eerste twee en staat er niet als vijfde bij; die
zou in een aandelensom dubbel meetellen.
"""

COARSE_SHARE_RESOLUTION = 0.02
"""Vanaf welke stapgrootte de aandelen van een regio grof genoeg zijn om te melden.

De bron is op hele Mm3 afgerond. In een regio met een vraag van 6 Mm3 ligt elk aandeel dus
in stappen van 17 procentpunt, en dan is het tweede cijfer ruis. Twee procentpunt is de
grens waarboven dat een lezer aangaat.
"""


@lru_cache(maxsize=None)
def _load_demand_posts() -> dict:
    file_dir = Path(__file__).parent
    with open(file_dir / "demand_posts.json", "r") as f:
        return json.load(f)


def available_demand_regions() -> list[str]:
    """De DPZW-regio's waarvoor een postverdeling beschikbaar is."""
    return sorted(_load_demand_posts()["regions"])


def available_demand_scenarios() -> list[str]:
    """De scenario's van de werkopgave; dit zijn niet de KNMI'23-scenario's."""
    any_region = next(iter(_load_demand_posts()["regions"].values()))
    return sorted(key for key in any_region)


def available_demand_return_periods() -> tuple[int, ...]:
    """De herhaaltijden die de werkopgave bijhoudt.

    Loopt tot T20 en niet verder, en dat is geen keuze van ons: de frequentiecurve is
    afgeleid uit de jaren van de reeks zelf en T20 is de bovengrens van wat die reeks draagt.
    """
    any_region = next(iter(_load_demand_posts()["regions"].values()))
    any_scenario = next(iter(any_region.values()))
    return tuple(sorted(int(key) for key in any_scenario["return_periods"]))


def region_code(region: str) -> str:
    """De DPZW-code van deze regio: H1 tot H6 voor de hoofdregio's, S1 tot S21 voor de deelregio's."""
    body = _load_demand_posts()["regions"][region]
    return next(iter(body.values()))["region_code"]


class DemandPosts(NamedTuple):
    """De vraagverdeling van een regio bij een scenario en een herhaaltijd.

    Drie blokken die elk een andere vraag beantwoorden: waar de vraag zit, wat ervan geleverd
    wordt, en waar het tekort valt. Die drie lopen niet gelijk - in West is doorspoeling de
    grootste vraagpost en beregening de post die als eerste tekortkomt.
    """

    demand_share: dict
    """Het aandeel van elke post in de totale watervraag; sommeert tot 1."""
    coverage: dict
    """Levering gedeeld door vraag, per post; `None` waar de post geen vraag heeft."""
    shortfall_share: dict
    """Het aandeel van elke post in het totale tekort; alles `None` als er geen tekort is."""
    total_coverage: float | None
    """Levering gedeeld door vraag over alle posten samen."""
    share_resolution: float | None
    """De stapgrootte waarin een aandeel in deze regio kan liggen, door de afronding op hele Mm3."""

    @property
    def is_coarse(self) -> bool:
        """Zijn de aandelen van deze regio zo grof dat het tweede cijfer ruis is?"""
        return (
            self.share_resolution is not None
            and self.share_resolution > COARSE_SHARE_RESOLUTION
        )


def demand_posts(region: str, scenario: str, return_period: int) -> DemandPosts | None:
    """De vraagverdeling bij deze keuze, of `None` als de regio hier geen vraag heeft.

    Drie uitkomsten, en het verschil doet ertoe - dezelfde vorm als `cumulative_deficit_mm`:

    * een **`DemandPosts`**: de aandelen, de dekking en de tekortverdeling;
    * **`None`**: deze regio heeft in dit scenario bij deze herhaaltijd geen watervraag, en
      dan is er ook geen verdeling. Nul zou daar een aandeel suggereren;
    * een **`KeyError`**: onbekende regio, scenario of herhaaltijd. Dat is een fout in de
      aanroep en geen ontbrekende data.
    """
    data = _load_demand_posts()
    try:
        block = data["regions"][region][scenario]
    except KeyError as exc:
        raise KeyError(
            f"onbekende regio/scenario ({region!r}, {scenario!r}); zie "
            f"available_demand_regions() en available_demand_scenarios()"
        ) from exc
    key = str(int(return_period))
    if key not in block["return_periods"]:
        raise KeyError(
            f"herhaaltijd {return_period} wordt niet bijgehouden; beschikbaar zijn "
            f"{available_demand_return_periods()}"
        )
    body = block["return_periods"][key]
    if all(value is None for value in body["demand_share"].values()):
        return None
    return DemandPosts(
        demand_share=body["demand_share"],
        coverage=body["coverage"],
        shortfall_share=body["shortfall_share"],
        total_coverage=body["total_coverage"],
        share_resolution=body["share_resolution"],
    )


def demand_posts_source() -> dict:
    """Het `meta`-blok: bron, status, methode en de caveats van de werkopgave."""
    return _load_demand_posts()["meta"]

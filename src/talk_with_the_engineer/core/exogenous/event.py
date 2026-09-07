"""Exogene gebeurtenissen: een trekking uit een statistiek waar de transitie binnen loopt.

Dit is `E`, en dan de eerste van drie soorten; zie `__init__.py` voor waarom het er drie
zijn en niet een.

Een gebeurtenis heeft een DUUR en een vorm: het weer over uren of weken, waar de
waterbalans doorheen rekent. Wat de buitenwereld tijdens die gebeurtenis levert is iets
anders - dat is een `BoundaryCondition` in `boundary.py` - en wat er over decennia met de
polder gebeurt weer iets anders; dat is een `Trend` in `trend.py`.

**Frozen dataclasses en geen pydantic**, om dezelfde reden die `state.py` voor `S`
opschrijft: een toolinvoermodel draagt een taalveld en een `input`-afpeller, en die horen
bij een aanroep en niet bij het weer. De omzetting van invoer naar deze vorm staat aan de
toolgrens, als `to_storm()` en `to_deficit()` op de invoermodellen.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExogenousEvent(Protocol):
    """Wat elke gebeurtenis gemeen heeft: hij duurt iets.

    Een protocol en geen basisklasse, want de twee gebeurtenissen delen geen enkel veld -
    een bui wordt in uren beschreven en een tekort in dagen - en een gedeelde basisklasse
    zou een verwantschap suggereren die er niet is. Wat ze wel delen is dat de transitie
    over hun duur heen rekent.
    """

    @property
    def duration_days(self) -> float:
        """Hoeveel dagen deze gebeurtenis beslaat."""
        ...


@dataclass(frozen=True)
class Storm:
    """Een bui: een trekking uit de neerslagstatistiek.

    Precies de velden die de kern uitleest. `RainfallInput` draagt daarnaast een taal, een
    boekhouding van welke velden zijn aangenomen, en de validator die de twee ingangen naar
    de neerslagsom tegen elkaar afzet; dat hoort bij een aanroep en reist niet mee.

    **De som komt langs een van twee wegen, en nooit langs beide.** `return_period` laat de
    kern hem in de STOWA-tabel opzoeken; `rain_volume_mm` is de som die de beller zelf
    meebrengt. `__post_init__` weigert de combinatie, zodat een aanroeper die de kern
    direct gebruikt dezelfde fout krijgt als een aanroeper over MCP en niet stil de ene weg
    neemt.

    **Wat hier niet in zit, is hoe snel het gebied afvoert.** De neerslag-afvoerrelatie is
    een eigenschap van bodem en drainage, dus van de polder: dezelfde bui geeft op een traag
    gebied een lagere piek. Dat is `PolderState.days_to_discharge`, en daardoor kan een
    cascade knopen met verschillende afvoerkarakteristieken hebben onder een bui.
    """

    time_of_year: str
    length_event_hrs: float
    name_rainfall_pattern: str
    rainfall_regime: str | None = None
    return_period: float | None = None
    rain_volume_mm: float | None = None

    def __post_init__(self):
        if (self.return_period is None) == (self.rain_volume_mm is None):
            raise ValueError(
                "Een bui heeft precies een bron voor zijn neerslagsom: `return_period` om "
                "hem in de statistiek op te zoeken, of `rain_volume_mm` om hem zelf op te "
                f"geven. Gekregen: return_period={self.return_period!r}, "
                f"rain_volume_mm={self.rain_volume_mm!r}."
            )

    @property
    def duration_days(self) -> float:
        return self.length_event_hrs / 24.0


@dataclass(frozen=True)
class Deficit:
    """Een neerslagtekort: een droogteperiode als vraag per dag maal een duur.

    Twee getallen en geen reeks, en dat is bewust. Tabel 39 beschrijft hoe neerslag tot
    *afvoer* komt; een tekort is geen negatieve afvoer maar een *vraag* - capillaire
    opstijging, gewasverdamping, wegzijging - en die komt onvertraagd uit het
    oppervlaktewater. `days_to_discharge` en `retention_fraction` doen aan de droge kant
    dus niets.

    Wat de bron over die periode kan leveren hoort hier niet bij: dat is geen eigenschap
    van de droogte maar van de rivier ernaast, en het staat als `BoundaryCondition`.
    """

    deficit_mm_per_day: float
    length_days: int

    @property
    def duration_days(self) -> float:
        return float(self.length_days)

"""Het exogene deel van het model: `E`.

Wat de strateeg niet kiest. Dit is het lid van de tuple waar de polder doorheen moet, en
het valt in DRIE soorten uiteen die niet dezelfde vorm hebben:

| soort | wat het is | duur | wat het raakt |
|---|---|---|---|
| gebeurtenis | een trekking uit een statistiek waar de transitie binnen loopt | uren tot weken | de forcering |
| randvoorwaarde | de stand van de buitenwereld tijdens die gebeurtenis | een waarde | de uitwisseling aan de rand |
| trend | een langzame driver | jaren tot decennia | de toestand zelf |

**Waarom drie en niet een.** Een bui en een neerslagtekort zijn gebeurtenissen: ze hebben
een duur, en na afloop is de polder weer wat hij was. Hoeveel de rivier tijdens die droogte
kan leveren is geen gebeurtenis maar een getal aan de rand - en het staat op het scherm ook
als tweede rij naast het tekort. En zeespiegelstijging of bodemdaling verschuift de
toestand zelf, tussen twee beslissingen; dat vraagt een tempo en geen duur. Een enkele
dataclass voor alle drie zou die verschillen wegpoetsen op precies het moment dat er een
vierde bij komt.

De statistieken waaruit een gebeurtenis wordt getrokken staan in `core/stats/`.
"""

from talk_with_the_engineer.core.exogenous.boundary import (
    UNLIMITED,
    BoundaryCondition,
)
from talk_with_the_engineer.core.exogenous.event import (
    Deficit,
    ExogenousEvent,
    Storm,
)
from talk_with_the_engineer.core.exogenous.trend import Trend

__all__ = [
    "UNLIMITED",
    "BoundaryCondition",
    "Deficit",
    "ExogenousEvent",
    "Storm",
    "Trend",
]

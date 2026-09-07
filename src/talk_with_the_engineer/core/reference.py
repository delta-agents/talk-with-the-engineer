"""De referentiecasus: een polder en een bui, één keer opgeschreven.

Twee soorten referentie, en ze zijn niet uitwisselbaar.

**De VALIDATIECASUS** is de polder en de bui waarvan Ton's rekenblad
(`scripts/scripts_Ton/TttE_v03.xlsx`) de uitkomst geeft: 4000 ha, 3,5 % open water, gemaal
5 m3/s, en een winterbui van T=1000 over 96 uur met patroon p1a en afvoer over 4 dagen.
Daar hangt `test_reference_ton.py` aan, en die getallen mogen dus niet bewegen zonder dat
het rekenblad meebeweegt.

**De DEMOPOLDER** is de polder waarmee de figuren en de presentatie rekenen: 1000 ha, 5 %
open water, gemaal 1,5 m3/s, met een zomerbui van T=10 over 192 uur. Kleiner en met meer
open water, want dat is wat een gemiddelde Nederlandse polder eerder benadert - en de
figuren moeten uitleggen en niet valideren.

Ze staan hier en niet in `scripts/` omdat een referentie die op acht plekken staat geen
referentie is: verschuift er een, dan verschuift een figuur mee zonder dat iemand het ziet.
"""

from talk_with_the_engineer.core.connection import single_pump_connection
from talk_with_the_engineer.core.exogenous import Storm
from talk_with_the_engineer.core.state import PolderState

# --- De demopolder: waar de figuren en de presentatie mee rekenen --------------------

REFERENCE_POLDER = PolderState(
    area_ha=1000,
    pct_open_water=5.0,
    connections=single_pump_connection(1.5),
    days_to_discharge=2,
)
"""Duizend hectare, 5 % open water, een gemaal van 1,5 m3/s, afvoer over twee dagen.

Zonder maatregel: geen vertraagde afvoer, geen peilopzet, geen peilmarge. Elke figuur die
een maatregel laat zien, zet hem op deze toestand.

`days_to_discharge=2` en niet de 3 van het invoerschema: de figuren zijn hierop gemaakt en
de voetnoot eronder zegt wat vier dagen zou doen. Het is een eigenschap van dit GEBIED, dus
hij staat hier en niet bij de bui - en wie hem verandert, verandert elke terugkeertijd in de
figuren.
"""

REFERENCE_STORM = Storm(
    return_period=10.0,
    time_of_year="summer",
    length_event_hrs=192.0,
    rainfall_regime="R",
    name_rainfall_pattern="p1c",
)
"""Een zomerbui die gemiddeld eens per tien jaar voorkomt, over acht dagen."""


def storm_with(**changes) -> Storm:
    """De referentiebui met een paar velden anders - één bedreiging dus.

    Dit is wat een rooster over de statistiek nodig heeft: dezelfde bui, één veld verschoven.
    `dataclasses.replace` op een frozen dataclass, dus de referentie zelf blijft staan en
    een script kan hem niet per ongeluk muteren.
    """
    from dataclasses import replace

    return replace(REFERENCE_STORM, **changes)


# --- De validatiecasus: waar `test_reference_ton.py` aan hangt ------------------------

VALIDATION_POLDER = PolderState(
    area_ha=4000,
    pct_open_water=3.5,
    connections=single_pump_connection(5.0),
    days_to_discharge=4,
)
"""Vierduizend hectare, 3,5 % open water, gemaal 5 m3/s, afvoer over vier dagen.

De polder uit het rekenblad. Vier dagen en niet de drie van het invoerschema; wie hem
verandert, verandert waar het model tegen gevalideerd is.
"""

VALIDATION_STORM = Storm(
    return_period=1000.0,
    time_of_year="winter",
    length_event_hrs=96.0,
    rainfall_regime="R",
    name_rainfall_pattern="p1a",
)
"""De bui waarvan de afvoerreeks in het rekenblad de uitkomst is.

Let op: dit is NIET de standaardbui van `RainfallInput`, die op p1c staat.
"""

VALIDATION_DH_M = 1.7023330857142858
"""De waterstandstijging zonder maatregel op de validatiecasus, uit het rekenblad."""

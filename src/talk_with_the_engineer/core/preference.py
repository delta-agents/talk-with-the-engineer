"""De voorkeursvolgorde: welke maatregel je vrijwel altijd nodig hebt.

De pakketzoeker levert één pakket bij één bedreiging. Dat is de vraag "wat moet ik doen bij
DEZE bui", en het antwoord is een punt in een ruimte waarvan de strateeg de coordinaten niet
kiest: het weer ligt niet vast, hij komt uit een statistiek.

Deze module stelt de andere vraag. Leg dezelfde eis langs elke bedreiging die de statistiek
kan trekken - elke terugkeertijd, elk buiduur, beide seizoenen, elk regime - en tel in
hoeveel van de antwoorden elke maatregel voorkomt. Dan komt er een VOORKEUR uit in plaats
van een pakket: een maatregel die in vrijwel elk antwoord staat is robuust tegen wat je niet
weet, en een maatregel die komt en gaat is een keuze die aan de bui hangt.

Dat verschil is niet cosmetisch. Een pakket bij één bui vertelt niet of het pakket bij een
zwaardere bui nog hetzelfde is; een maatregel die er bij T=10 in zit en bij T=100 uit valt,
is een verkeerde eerste stap. Deze telling maakt dat zichtbaar zonder dat er een aanname
over de bui in hoeft.

**De prijs is doorrekentijd.** Het volledige rooster is 312 bedreigingen, en elke bedreiging
kost de pakketzoeker een enumeratie over de mixen. Dat is minuten en geen milliseconden, dus
dit is geen tool maar een analyse: `over_the_grid` neemt daarom een expliciet rooster in
plaats van er stil een te kiezen.
"""

from collections import Counter
from dataclasses import dataclass
from itertools import product

from talk_with_the_engineer.core.exogenous import Storm
from talk_with_the_engineer.core.package import Constraints, optimize
from talk_with_the_engineer.core.state import PolderState

QUANTITY_FLOOR = 1e-9
"""Onder deze maatvoering staat een maatregel niet in het pakket.

De optimalisatie levert continue hoeveelheden, dus een maatregel die niet meedoet komt eruit
als een getal van de orde 1e-12 en niet als nul. Meetellen zou elke maatregel in elk pakket
zetten en de telling zinloos maken.
"""


@dataclass(frozen=True)
class Preference:
    """Hoe vaak elke maatregel in het goedkoopste pakket voorkomt over een rooster.

    `share_of` is de leesbare vorm: het deel van de bedreigingen WAARBIJ EEN MAATREGEL NODIG
    IS waarin deze maatregel voorkomt. De noemer is bewust niet het hele rooster - een lichte
    bui waarbij niets hoeft, zegt niets over de voorkeur en zou elke maatregel verdunnen.
    """

    counts: dict[str, int]
    """Per maatregel: in hoeveel pakketten hij voorkomt."""

    threats: int
    """Hoeveel bedreigingen er zijn doorgerekend."""

    threats_needing_a_measure: int
    """Bij hoeveel daarvan er iets moest gebeuren."""

    def share_of(self, measure_nl: str) -> float:
        """Het deel van de pakketten waarin deze maatregel voorkomt, tussen 0 en 1."""
        if not self.threats_needing_a_measure:
            return 0.0
        return self.counts.get(measure_nl, 0) / self.threats_needing_a_measure

    @property
    def ordered(self) -> list[tuple[str, int]]:
        """De maatregelen van meest naar minst voorkomend."""
        return Counter(self.counts).most_common()


def measures_in_the_cheapest_package(
    state: PolderState,
    storm: Storm,
    constraints: Constraints,
) -> dict[str, float]:
    """Welke maatregelen het goedkoopste pakket bij deze bedreiging gebruikt.

    Leeg als er niets hoeft. Dat is een antwoord en geen ontbrekend antwoord: bij een lichte
    bui haalt de polder de eis zonder ingreep.
    """
    best = optimize(state, storm, constraints).best
    if best is None:
        return {}
    return {
        name: quantity
        for name, quantity in best.quantities.items()
        if quantity > QUANTITY_FLOOR
    }


def storm_grid(
    reference: Storm,
    return_periods,
    length_event_hrs,
    times_of_year,
    rainfall_regimes,
):
    """Elke bedreiging die deze vier assen samen opspannen.

    Vier assen en geen willekeurige steekproef: de statistiek is discreet - dit zijn de
    waarden die STOWA bijhoudt - dus het rooster IS de verzameling en niet een benadering
    ervan. Wat er niet in zit, is de bui die de tabel niet kent.
    """
    from dataclasses import replace

    for period, hours, season, regime in product(
        return_periods, length_event_hrs, times_of_year, rainfall_regimes
    ):
        yield replace(
            reference,
            return_period=float(period),
            length_event_hrs=float(hours),
            time_of_year=season,
            rainfall_regime=regime,
        )


def over_the_grid(
    state: PolderState,
    constraints: Constraints,
    storms,
) -> Preference:
    """Tel per maatregel in hoeveel van de goedkoopste pakketten hij voorkomt.

    `storms` is een expliciete verzameling en geen roosterspecificatie, zodat de aanroeper
    ziet - en kiest - hoeveel doorrekeningen hij vraagt. Het volledige rooster is er een
    van; een enkele as ook.
    """
    counts: Counter[str] = Counter()
    threats = 0
    needing = 0
    for storm in storms:
        threats += 1
        measures = measures_in_the_cheapest_package(state, storm, constraints)
        if not measures:
            continue
        needing += 1
        counts.update(measures.keys())
    return Preference(
        counts=dict(counts),
        threats=threats,
        threats_needing_a_measure=needing,
    )

"""Uitkomst van een inverse berekening: hoeveel maatregel is er nodig?

De statusvelden bestaan omdat er een haalbaar bereik is, en de randen daarvan zijn een
ANTWOORD en geen randgeval. Interpoleren in een raster klemt daar stil: een doel onder het
haalbare levert dan "0 ha nodig" en een doel erboven "100 %", zonder enige melding dat de
vraag buiten het bereik lag.
"""

from enum import Enum
from math import floor, isfinite, log10
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from talk_with_the_engineer.core.state import PolderState


SIGNIFICANT_DIGITS = 4
"""Aantal significante cijfers in de tooluitvoer.

Deze tools zijn vuistregels, en de oplosser is een bisectie: die levert zestien cijfers
waarvan er hooguit drie iets betekenen. Ze allemaal doorgeven suggereert precisie die er
niet is en kost de lezer - mens of model - alleen maar moeite. Vier cijfers houdt 1,806 m
op millimeters, 111,2 ha op are en 15,01 miljoen euro op tienduizend euro nauwkeurig.

Significante cijfers en geen vast aantal decimalen, want de uitvoer loopt van 0,086 m tot
383 miljoen euro; een vaste komma is voor het ene eind onzin en voor het andere ruis.
Alleen de uitvoer wordt afgerond - de rekenkern rekent onverkort door, en de gouden
regressietest tegen het rekenblad staat nog steeds op 1e-12.
"""


def round_significant(value: float, digits: int = SIGNIFICANT_DIGITS) -> float:
    """Rond af op `digits` significante cijfers; 0 en niet-eindige waarden blijven zoals ze zijn."""
    if value == 0 or not isfinite(value):
        return value
    return round(value, -int(floor(log10(abs(value)))) + (digits - 1))


def round_floats(value: Any) -> Any:
    """Rond elke float in een geneste structuur af. Ints blijven int: dagen zijn dagen."""
    if isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        return round_significant(value)
    if isinstance(value, dict):
        return {k: round_floats(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(round_floats(v) for v in value)
    return value


class SolveStatus(str, Enum):
    EXACT = "exact"
    """Het doel is haalbaar en de maatvoering is bepaald."""

    NO_MEASURE_NEEDED = "no_measure_needed"
    """De waterstand blijft al zonder maatregel onder het doel."""

    ACTION_INFEASIBLE = "action_infeasible"
    """Deze maatregel kan het doel niet halen. Een andere, of een combinatie, misschien wel.

    Het onderscheid met `problem_infeasible` bestaat omdat een agent anders uit een
    antwoord over een losse maatregel concludeert dat het probleem onoplosbaar is. Bergen
    kan de inundatienorm niet halen en bergen plus peilopzet wel; dat is precies het
    verschil tussen doorzoeken en opgeven, en één naam voor beide houdt ze niet uit elkaar.
    """

    PROBLEM_INFEASIBLE = "problem_infeasible"
    """Geen enkel pakket kan het doel halen.

    Wordt door `solve` nooit geleverd - die kijkt naar een maatregel per keer. Dit is de
    status van de pakketzoeker, en hij staat hier zodat het onderscheid met
    `action_infeasible` in het schema staat waar een agent hem leest.
    """


class LimitReason(str, Enum):
    NONE = "none"
    MEASURE_OPTIMUM = "measure_optimum"
    """De maatregel heeft een optimum; verder uitbreiden maakt het slechter."""

    PHYSICAL_UPPER_BOUND = "physical_upper_bound"
    """De maatvoering loopt tegen een fysieke grens aan."""

    PAST_OPTIMUM = "past_optimum"
    """De opgegeven maatvoering ligt VOORBIJ het optimum van de maatregel.

    Alleen bij een voorwaartse vraag, en alleen bij een binnenoptimum. Het antwoord is dan
    nog steeds exact - de vraag was "wat doet deze maatvoering", en dat is precies wat er
    staat - maar het is duurder EN slechter dan een kleinere maatvoering. Op de
    referentiecasus (4000 ha, 3,5 % open water, gemaal 5 m3/s) betaalt 3800 ha
    vasthouden 44 % meer dan 2645 ha voor een 5 cm hogere stijging.

    Zonder deze vlag is dat alleen af te leiden door `magnitude_optimum_kind: "interior"`
    naast `magnitude_at_optimum_ha` < `measure.after` te leggen - twee velden die nergens
    als paar worden geintroduceerd. En juist het binnenoptimum bij vasthouden is het meest
    contra-intuitieve resultaat dat dit model produceert, dus daar is een expliciete vlag
    het meeste waard.
    """


class MeasureRole(str, Enum):
    """Wat een maatregel doet in het BIJNA-OPTIMALE GEBIED, niet in één pakket.

    Een optimum is alleen optimaal voor wat er gemodelleerd is. Wat een beslisser daarnaast
    heeft - draagvlak, uitvoerbaarheid, een prijs die eigenlijk een trap is, een buur die we
    nog niet kennen - leeft náást dat punt, en het enige wat wij daarover kunnen zeggen is
    hoeveel ruimte er is. Deze drie waarden zijn die uitspraak.

    Bewust op de RANGORDE en niet op de maatvoering. Gemeten over 162 invoercombinaties
    draait de rangorde van bergen en afvoeren in geen enkele om, terwijl de hectares een
    factor honderd bewegen; de robuuste uitspraak is dus "welke maatregel", niet "hoeveel".

    Wordt gedeeld door de pakketzoeker (een maatregel in een pakket) en door de toewijzing op
    de droge kant (een afnemer in een verdeling): zelfde discipline, andere operator.
    """

    FORCED = "forced"
    """Zit in ELK pakket dat binnen de marge even goed is. Hier is geen keuze."""

    OPTIONAL = "optional"
    """Zit in sommige en niet in andere. Hier is wél een keuze, en die is niet van ons."""

    ABSENT = "absent"
    """Zit in geen enkel pakket in het gebied.

    De rol zelf draagt geen reden, want die is uit het gebied niet af te lezen: een
    maatregel kan ontbreken omdat hij niet bijdraagt aan de gestelde eisen, of omdat elke
    inzet buiten de prijsband van het beste pakket valt. De reden wordt daarom apart
    GEMETEN aan het beste pakket - zie `can_improve_a_requirement` - en meegegeven waar
    deze rol wordt gerapporteerd.
    """


class OptimumKind(str, Enum):
    """Wat voor punt `magnitude_at_optimum` is.

    De naam "optimum" suggereert bij elke maatregel hetzelfde, en dat klopt niet. Bij
    vasthouden is het een echt optimum: verder uitbreiden maakt de waterstand weer hoger.
    Bij afvoeren is het het punt waar de stijging zijn ondergrens raakt en daarna vlak
    blijft; meer pompcapaciteit is daar verspilling, maar niet schadelijk. Zonder dit
    onderscheid leest een lezer - mens of model - "meer dan 11,88 m3/s is contraproductief",
    en dat staat er niet.
    """

    INTERIOR = "interior"
    """Voorbij dit punt wordt de waterstandstijging weer groter."""

    PLATEAU = "plateau"
    """Voorbij dit punt verandert de waterstandstijging niet meer.

    De maatregel heeft zijn eigen ondergrens bereikt: bij afvoeren is de stijging niet
    verder te verlagen omdat er niets meer te verlagen valt.
    """

    SATURATED = "saturated"
    """Voorbij dit punt verandert er niets meer, maar door een ANDERE grootheid.

    Het verschil met `plateau` is wie de klem is. Bij voorbemaling stopt de winst op
    10,5 cm niet omdat de waterstand niet lager kan, maar omdat het gemaal niet sneller
    leegmaalt. Meer marge *afspreken* helpt dan niet; een groter gemaal wel. Dat is een
    ander advies dan "hier is niets meer te halen", en het is uit het getal alleen niet
    af te lezen.
    """

    UPPER_BOUND = "upper_bound"
    """De maatvoering zit tegen zijn fysieke bovengrens; groter kan niet."""


class SolveResult(BaseModel):
    """Wat er nodig is, wat het oplevert, en of het kan."""

    model_config = ConfigDict(frozen=True)

    status: SolveStatus = Field(
        ...,
        description=(
            "exact = doel haalbaar en maatvoering bepaald; no_measure_needed = de "
            "waterstand blijft er al onder; action_infeasible = het doel ligt onder wat "
            "deze maatregel kan bereiken, maar een andere of een combinatie kan het "
            "misschien wel"
        ),
    )
    limit_reason: LimitReason = Field(
        LimitReason.NONE,
        description=(
            "Bij action_infeasible: measure_optimum als de maatregel zijn eigen optimum "
            "bereikt, physical_upper_bound als de maatvoering tegen een fysieke grens "
            "aanloopt"
        ),
    )

    magnitude: float = Field(..., description="Benodigde maatvoering, in `unit`")
    share_delta_pp: float | None = Field(
        None,
        description=(
            "De verschuiving in procentpunten, of `None` als deze grootheid geen aandeel "
            "is; komt uit `Action.area_share_delta`"
        ),
    )
    share_of_nl: str | None = Field(
        None,
        description="Waarvan `share_delta_pp` een percentage is; komt uit `Action.share_of_nl`",
    )
    magnitude_before: float = Field(
        0.0,
        description=(
            "De waarde van dezelfde grootheid VOOR de maatregel, in `unit`; komt uit "
            "`Action.current_magnitude`. Samen met `magnitude` is dit wat `MeasureChange` "
            "naar buiten brengt"
        ),
    )
    unit: str
    measure_nl: str
    cost: float | None = Field(
        None, description="Investeringskosten [EUR], werkwaarde; geen exploitatie"
    )
    cost_range: tuple[float, float] | None = Field(
        None,
        description=(
            "Onder- en bovengrens van de investeringskosten [EUR]. De bandbreedte staat "
            "erbij omdat een enkel getal valse precisie zou zijn"
        ),
    )

    state_before: PolderState
    state_after: PolderState

    target_dh_m: float | None = Field(
        None, description="Doelwaterstand; None bij een voorwaartse berekening"
    )
    dh_reference_m: float = Field(
        ..., description="Waterstandstijging zonder maatregel"
    )
    dh_with_measure_m: float = Field(
        ..., description="Waterstandstijging met maatregel"
    )

    feasible_dh_min_m: float = Field(
        ..., description="Laagste haalbare waterstandstijging met deze maatregel"
    )
    feasible_dh_max_m: float = Field(
        ..., description="Hoogste, oftewel de referentie zonder maatregel"
    )
    magnitude_at_optimum: float = Field(
        ..., description="Maatvoering waarbij feasible_dh_min_m wordt gehaald"
    )
    magnitude_optimum_kind: OptimumKind = Field(
        ...,
        description=(
            "Wat er gebeurt voorbij magnitude_at_optimum: interior = het wordt weer "
            "slechter, plateau = er verandert niets meer, saturated = er verandert niets "
            "meer omdat een andere grootheid de klem is, upper_bound = verder kan niet"
        ),
    )
    dh_tolerance_m: float | None = Field(
        None,
        description=(
            "Hoe scherp `dh_with_measure_m` de doelwaterstand raakt [m]. Alleen gevuld bij "
            "een INVERSE berekening met status `exact`: dan is de maatvoering gezocht tot "
            "de waterstand binnen deze marge van `target_dh_m` lag. Bij een voorwaartse "
            "berekening is er niets te raken en staat hij op null"
        ),
    )
    """De marge waarbinnen de omkering het doel raakt.

    Waarom dit veld bestaat: `status: exact` is een woord, en dit is het getal dat het
    verdedigt. De omkering wordt niet in gesloten vorm opgelost maar gezocht - een grof
    raster, dan de gulden snede naar het optimum, dan bisectie op de dalende tak - en dat is
    wat "exact" hier betekent: een deterministische zoektocht met een gemelde marge, niet
    een sweep waarin geinterpoleerd wordt.

    Deze codebase laat alles wat een antwoord kwalificeert mee reizen met dat antwoord: de
    aannames in `assumptions`, de spreiding in `sensitivity`, de grenzen in `caveats`, de
    prijzen als band. De scherpte van de omkering hoorde in dat rijtje, en niet in een
    constante die de module niet verlaat.

    Zet het naast `sensitivity`, niet ertegenover. Deze marge is de NUMERIEKE scherpte en
    ligt op tienden van millimeters; de parametrische spreiding op dezelfde vraag loopt in
    de tientallen procenten. Wie deze marge als de nauwkeurigheid van het antwoord
    rapporteert, meldt de kleinste onzekerheid en laat de grootste weg.
    """

    @property
    def dh_reduction_m(self) -> float:
        """De verlaging ten opzichte van de situatie zonder maatregel."""
        return self.dh_reference_m - self.dh_with_measure_m

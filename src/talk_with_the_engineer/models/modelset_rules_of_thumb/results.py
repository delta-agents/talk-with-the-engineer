"""Uitkomst van een inverse berekening: hoeveel maatregel is er nodig?

De statusvelden bestaan omdat er een haalbaar bereik is. Voorheen werd met `np.interp`
geinterpoleerd, en die klemt stil op de randen: een doel onder het haalbare leverde
"0 ha nodig" op en een doel erboven "100 %", zonder enige melding. Zie
PLAN_TOOLS_REFACTOR.md D7.
"""

from enum import Enum
from math import floor, isfinite, log10
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    Sensitivity,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState


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
    verschil tussen doorzoeken en opgeven. Heette eerder `infeasible`, wat die twee
    dingen niet uit elkaar hield.
    """

    PROBLEM_INFEASIBLE = "problem_infeasible"
    """Geen enkel pakket kan het doel halen.

    Wordt door `solve` nooit geleverd - die kijkt naar een maatregel per keer. Bestaat voor
    de pakketzoeker uit WP11, en staat hier zodat het onderscheid nu al in het schema staat
    en een agent er niet later door verrast wordt.
    """


class LimitReason(str, Enum):
    NONE = "none"
    MEASURE_OPTIMUM = "measure_optimum"
    """De maatregel heeft een optimum; verder uitbreiden maakt het slechter."""

    PHYSICAL_UPPER_BOUND = "physical_upper_bound"
    """De maatvoering loopt tegen een fysieke grens aan."""


class MeasureRole(str, Enum):
    """Wat een maatregel doet in het BIJNA-OPTIMALE GEBIED, niet in één pakket.

    Een optimum is alleen optimaal voor wat er gemodelleerd is. Wat een beslisser daarnaast
    heeft - draagvlak, uitvoerbaarheid, een prijs die eigenlijk een trap is, een buur die we
    nog niet kennen - leeft náást dat punt, en het enige wat wij daarover kunnen zeggen is
    hoeveel ruimte er is. Deze drie waarden zijn die uitspraak.

    Bewust op de RANGORDE en niet op de maatvoering. WP12 mat dat de rangorde van bergen en
    afvoeren in 0 van 162 invoercombinaties omdraait terwijl de hectares een factor honderd
    bewegen; de robuuste uitspraak is dus "welke maatregel", niet "hoeveel".

    Wordt gedeeld door de pakketzoeker (een maatregel in een pakket) en straks door de
    toewijzing op de droge kant (een afnemer in een verdeling). Zelfde discipline, andere
    operator - zie issue #30 en #31.
    """

    FORCED = "forced"
    """Zit in ELK pakket dat binnen de marge even goed is. Hier is geen keuze."""

    OPTIONAL = "optional"
    """Zit in sommige en niet in andere. Hier is wél een keuze, en die is niet van ons."""

    ABSENT = "absent"
    """Zit in geen enkel pakket in het gebied. Niet "te duur" maar "draagt niet bij"."""


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

    @property
    def dh_reduction_m(self) -> float:
        """De verlaging ten opzichte van de situatie zonder maatregel."""
        return self.dh_reference_m - self.dh_with_measure_m


class MeasureOutput(EngineerBaseModel):
    """Gedeelde uitvoer van de zes vuistregeltools.

    `state_before` en `state_after` maken de uitvoer van hetzelfde type als de invoer: het
    antwoord op "wat als ik dit doe" is een nieuwe toestand, niet alleen een getal. Het
    haalbare bereik en de status staan erbij omdat een doel buiten dat bereik geen getal
    verdient maar een uitleg.
    """

    data: Dict[str, Any] = Field(..., description="Ruwe uitkomsten en tussenresultaten")
    description: str = Field(
        ...,
        description=(
            "Twee uitlegbare zinnen, plus een derde met de aangenomen standaardwaarden "
            "als de beller er een heeft weggelaten"
        ),
    )

    status: SolveStatus = Field(
        ...,
        description=(
            "exact = doel haalbaar; no_measure_needed = niet nodig; action_infeasible = "
            "niet haalbaar met DEZE maatregel - een andere of een combinatie kan het "
            "misschien wel, dus dit is geen uitspraak over het probleem"
        ),
    )
    limit_reason: LimitReason = Field(
        LimitReason.NONE,
        description="Waarom het doel niet haalbaar was, indien van toepassing",
    )
    magnitude_optimum_kind: OptimumKind = Field(
        ...,
        description=(
            "Hoort bij magnitude_at_optimum_* in `data` en zegt wat er gebeurt als de "
            "maatregel groter wordt gemaakt dan die maatvoering: interior = de "
            "waterstandstijging wordt weer groter (vasthouden), plateau = er verandert "
            "niets meer (afvoeren), upper_bound = groter kan fysiek niet (bergen). Dit "
            "gaat dus over de maatvoering en niet over de waterstand: welke stijging "
            "haalbaar is staat in feasible_dh_min_m en feasible_dh_max_m"
        ),
    )
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description=(
            "Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven. Leeg als "
            "de beller alles heeft ingevuld; anders is dit precies wat er nog aan het "
            "antwoord kan schuiven"
        ),
    )
    sensitivity: list[Sensitivity] = Field(
        default_factory=list,
        description=(
            "Per aangenomen veld het antwoord aan de uiteinden van zijn plausibele bereik. "
            "Dit is de spreiding van DIT antwoord en geen algemene uitspraak: het model is "
            "sterk over haalbaarheid en rangorde en zwak over maatvoering, en hier staat "
            "hoeveel. Geef het bereik door aan de gebruiker en niet alleen het getal"
        ),
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description=(
            "Structurele beperkingen die op dit antwoord van toepassing zijn: termen die "
            "niet in het model zitten of vragen die openstaan, met de richting waarin ze "
            "het antwoord kunnen schuiven. Bewust geen foutmarge - parametrische "
            "onzekerheid staat berekend in `sensitivity`, en een percentage op structurele "
            "modelfout zou verzonnen zijn"
        ),
    )

    state_before: PolderState = Field(
        ..., description="De toestand van de polder voor de maatregel"
    )
    state_after: PolderState = Field(
        ..., description="De toestand na de maatregel; zelfde type als state_before"
    )

    dh_reference_m: float = Field(
        ..., description="Maximale waterstandstijging zonder maatregel [m]"
    )
    dh_with_measure_m: float = Field(
        ..., description="Maximale waterstandstijging met maatregel [m]"
    )
    dh_reduction_m: float = Field(
        ..., description="Verlaging ten opzichte van de situatie zonder maatregel [m]"
    )
    feasible_dh_min_m: float = Field(
        ...,
        description=(
            "Laagst haalbare waterstandstijging met deze maatregel [m]; een doel "
            "hieronder is action_infeasible"
        ),
    )
    feasible_dh_max_m: float = Field(
        ...,
        description=(
            "Hoogst mogelijke waterstandstijging [m], oftewel de referentie zonder "
            "maatregel; een doel hierboven vraagt geen maatregel"
        ),
    )

    cost: float | None = Field(
        None, description="Investeringskosten [EUR], werkwaarde; geen exploitatie"
    )
    cost_range: tuple[float, float] | None = Field(
        None, description="Onder- en bovengrens van de investeringskosten [EUR]"
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS."""
        return round_floats(handler(self))

    @classmethod
    def from_solve_result(
        cls,
        result,
        data,
        description,
        assumptions=(),
        sensitivity=(),
        caveats=(),
        **extra,
    ):
        return cls(
            data=data,
            description=description,
            sensitivity=list(sensitivity),
            caveats=list(caveats),
            status=result.status,
            limit_reason=result.limit_reason,
            magnitude_optimum_kind=result.magnitude_optimum_kind,
            assumptions=list(assumptions),
            state_before=result.state_before,
            state_after=result.state_after,
            dh_reference_m=result.dh_reference_m,
            dh_with_measure_m=result.dh_with_measure_m,
            dh_reduction_m=result.dh_reduction_m,
            feasible_dh_min_m=result.feasible_dh_min_m,
            feasible_dh_max_m=result.feasible_dh_max_m,
            cost=result.cost,
            cost_range=result.cost_range,
            **extra,
        )

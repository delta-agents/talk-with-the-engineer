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

    INFEASIBLE = "infeasible"
    """Het doel ligt onder wat deze maatregel kan bereiken."""


class LimitReason(str, Enum):
    NONE = "none"
    MEASURE_OPTIMUM = "measure_optimum"
    """De maatregel heeft een optimum; verder uitbreiden maakt het slechter."""

    PHYSICAL_UPPER_BOUND = "physical_upper_bound"
    """De maatvoering loopt tegen een fysieke grens aan."""


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
    """Voorbij dit punt verandert de waterstandstijging niet meer."""

    UPPER_BOUND = "upper_bound"
    """De maatvoering zit tegen zijn fysieke bovengrens; groter kan niet."""


class SolveResult(BaseModel):
    """Wat er nodig is, wat het oplevert, en of het kan."""

    model_config = ConfigDict(frozen=True)

    status: SolveStatus = Field(
        ...,
        description=(
            "exact = doel haalbaar en maatvoering bepaald; no_measure_needed = de "
            "waterstand blijft er al onder; infeasible = het doel ligt onder wat deze "
            "maatregel kan bereiken"
        ),
    )
    limit_reason: LimitReason = Field(
        LimitReason.NONE,
        description=(
            "Bij infeasible: measure_optimum als de maatregel zijn eigen optimum "
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
            "slechter, plateau = er verandert niets meer, upper_bound = verder kan niet"
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
            "exact = doel haalbaar; no_measure_needed = niet nodig; infeasible = niet "
            "haalbaar met deze maatregel"
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
            "hieronder is infeasible"
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
    def from_solve_result(cls, result, data, description, assumptions=(), **extra):
        return cls(
            data=data,
            description=description,
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

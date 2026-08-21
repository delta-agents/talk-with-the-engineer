"""Uitkomst van een inverse berekening: hoeveel maatregel is er nodig?

De statusvelden bestaan omdat er een haalbaar bereik is. Voorheen werd met `np.interp`
geinterpoleerd, en die klemt stil op de randen: een doel onder het haalbare leverde
"0 ha nodig" op en een doel erboven "100 %", zonder enige melding. Zie
PLAN_TOOLS_REFACTOR.md D7.
"""

from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState


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
    description: str = Field(..., description="Twee uitlegbare zinnen")

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
        ..., description="Laagst haalbare waterstandstijging met deze maatregel [m]"
    )
    feasible_dh_max_m: float = Field(
        ..., description="Hoogste, oftewel de referentie zonder maatregel [m]"
    )

    cost: float | None = Field(
        None, description="Investeringskosten [EUR], werkwaarde; geen exploitatie"
    )
    cost_range: tuple[float, float] | None = Field(
        None, description="Onder- en bovengrens van de investeringskosten [EUR]"
    )

    @classmethod
    def from_solve_result(cls, result, data, description, **extra):
        return cls(
            data=data,
            description=description,
            status=result.status,
            limit_reason=result.limit_reason,
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

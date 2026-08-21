"""Maatregelen als getypeerde acties op de polder-toestand.

Dit is het `a` uit `s' = f(s, a, w)`. Elke maatregel raakt precies een toestandsveld, en
draagt zijn eigen eenheid en prijs. De eenheden zijn niet uitwisselbaar: bij bergen wordt
land gekocht, bij vasthouden het recht om het af en toe onder water te zetten.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState

# Afvoeren heeft geen harde fysieke bovengrens. Dit plafond bestaat zodat een onhaalbaar
# doel in een eindige zoekruimte blijft en als `physical_upper_bound` gemeld wordt.
MAX_PUMP_FACTOR = 20.0


class Action(BaseModel, ABC):
    """Een maatregel met maatvoering."""

    model_config = ConfigDict(frozen=True)

    name_nl: ClassVar[str]
    name_en: ClassVar[str]
    unit: ClassVar[str]

    cost_per_unit: float | None = Field(
        None, description="Investeringskosten per eenheid maatvoering [EUR]"
    )

    @property
    @abstractmethod
    def magnitude(self) -> float:
        """De maatvoering, in `unit`."""

    @abstractmethod
    def at(self, magnitude: float) -> "Action":
        """Dezelfde maatregel met een andere maatvoering."""

    @abstractmethod
    def apply(self, state: PolderState) -> PolderState:
        """De toestand na uitvoering van deze maatregel."""

    @abstractmethod
    def upper_bound(self, state: PolderState) -> float:
        """De grootste maatvoering die in deze toestand mogelijk is."""

    def cost(self) -> float | None:
        if self.cost_per_unit is None:
            return None
        return self.cost_per_unit * self.magnitude


class BergenAction(Action):
    """Bergen: land wordt open water. Verhoogt `pct_open_water`."""

    name_nl: ClassVar[str] = "bergen"
    name_en: ClassVar[str] = "store"
    unit: ClassVar[str] = "ha open water"

    delta_open_water_ha: float = Field(0.0, ge=0.0)

    @property
    def magnitude(self) -> float:
        return self.delta_open_water_ha

    def at(self, magnitude: float) -> "BergenAction":
        return BergenAction(
            delta_open_water_ha=magnitude, cost_per_unit=self.cost_per_unit
        )

    def apply(self, state: PolderState) -> PolderState:
        new_open_water_ha = state.area_open_water_ha + self.delta_open_water_ha
        return state.replace(pct_open_water=new_open_water_ha / state.area_ha * 100.0)

    def upper_bound(self, state: PolderState) -> float:
        # al het resterende land kan in principe open water worden
        return max(state.area_ha - state.area_open_water_ha, 0.0)


class AfvoerenAction(Action):
    """Afvoeren: meer gemaalcapaciteit. Verhoogt `pump_capacity_m3_per_sec`."""

    name_nl: ClassVar[str] = "afvoeren"
    name_en: ClassVar[str] = "discharge"
    unit: ClassVar[str] = "m3/s"

    delta_pump_capacity_m3_per_sec: float = Field(0.0, ge=0.0)

    @property
    def magnitude(self) -> float:
        return self.delta_pump_capacity_m3_per_sec

    def at(self, magnitude: float) -> "AfvoerenAction":
        return AfvoerenAction(
            delta_pump_capacity_m3_per_sec=magnitude, cost_per_unit=self.cost_per_unit
        )

    def apply(self, state: PolderState) -> PolderState:
        return state.replace(
            pump_capacity_m3_per_sec=(
                state.pump_capacity_m3_per_sec + self.delta_pump_capacity_m3_per_sec
            )
        )

    def upper_bound(self, state: PolderState) -> float:
        return state.pump_capacity_m3_per_sec * (MAX_PUMP_FACTOR - 1.0)


class VasthoudenAction(Action):
    """Vasthouden: de afvoer van een deel van het land wordt vertraagd.

    Verhoogt `retention_fraction`. Het aantal dagen vertraging is een ontwerpconstante van
    de polder en dus een eigenschap van de toestand, niet van de maatregel: anders is
    administratie per perceel nodig zodra er in twee stappen retentie wordt gebouwd met
    verschillende vertraging.
    """

    name_nl: ClassVar[str] = "vasthouden"
    name_en: ClassVar[str] = "retention"
    unit: ClassVar[str] = "ha land"

    delta_retention_ha: float = Field(0.0, ge=0.0)

    @property
    def magnitude(self) -> float:
        return self.delta_retention_ha

    def at(self, magnitude: float) -> "VasthoudenAction":
        return VasthoudenAction(
            delta_retention_ha=magnitude, cost_per_unit=self.cost_per_unit
        )

    def apply(self, state: PolderState) -> PolderState:
        added_fraction = self.delta_retention_ha / state.area_land_ha
        return state.replace(
            retention_fraction=min(state.retention_fraction + added_fraction, 1.0)
        )

    def upper_bound(self, state: PolderState) -> float:
        return state.area_land_ha * (1.0 - state.retention_fraction)

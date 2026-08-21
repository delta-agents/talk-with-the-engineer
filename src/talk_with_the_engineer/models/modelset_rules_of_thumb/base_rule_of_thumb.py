import warnings
from typing import Literal

from pydantic import Field, model_validator

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerBaseModel

# as defined in talk_with_the_engineer/models/modelset_rules_of_thumb/utils_rainfall_stats.py
# Alle gegeven zijn overgenomen uit tabel 6 en 7 in deelrapport 3 (regionale statistiek voor extreme neerslag) van STOWA-2019

RETURN_PERIODS = [
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    25.0,
    50.0,
    100.0,
    200.0,
    250.0,
    500.0,
    1000.0,
]

LENGTH_EVENT_HRS = [
    48.0,
    96.0,
    192.0,
]

TIME_OF_YEAR = [
    "winter",
    "summer",
]

RAINFALL_REGIMES = ["LL", "L", "R", "H"]

NAME_RAINFALL_PATTERN = ["p_0", "p1a", "p1b", "p1c", "p1d", "p2a", "p2b"]

# Tabel 39 van HKV PR4991.10 geeft alleen deze drie mogelijkheden.
DAYS_TO_DISCHARGE = [2, 3, 4]


class RainfallInput(EngineerBaseModel):
    """De bui: het exogene deel van de invoer.

    De toegestane waarden staan als `Literal` in het type en dus als `enum` in het
    JSON-schema, met de constantenlijsten hierboven als enige bron. Eerder stonden ze
    alleen als tekst in de veldbeschrijvingen en werden ze door validators afgedwongen;
    een MCP-client kon ze daardoor niet valideren en een model dat op het schema gestuurd
    wordt kon nog steeds een ongeldige waarde genereren.
    """

    return_period: Literal[*RETURN_PERIODS] = Field(
        ...,
        description=(
            "Terugkeertijd van de bui in jaren. 0.5 betekent gemiddeld twee keer per jaar."
        ),
    )
    time_of_year: Literal[*TIME_OF_YEAR] = Field(
        "summer",
        description=(
            "Halfjaar waarvoor de neerslagstatistiek geldt. Let op: 'summer' gebruikt de "
            "jaarrondstatistiek als benadering van de zomer"
        ),
    )
    length_event_hrs: Literal[*LENGTH_EVENT_HRS] = Field(
        96.0, description="Duur van de bui in uren"
    )
    rainfall_regime: Literal[*RAINFALL_REGIMES] = Field(
        "R",
        description=(
            "Neerslagregime van het gebied: LL en L voor weinig regionale spreiding, "
            "R als referentie, H voor veel spreiding"
        ),
    )
    name_rainfall_pattern: Literal[*NAME_RAINFALL_PATTERN] = Field(
        "p1c", description="Naam van het neerslagpatroon binnen de bui"
    )
    days_to_discharge: Literal[*DAYS_TO_DISCHARGE] = Field(
        3,
        description=(
            "Aantal dagen waarover de dagneerslag tot regionale afvoer komt "
            "(neerslag-afvoerrelatie, Tabel 39 van HKV PR4991.10)"
        ),
    )


class WaterSystemInput(EngineerBaseModel):
    """
    Input model containing all the parameters for water systems.
    """

    discharge_capacity_m3_per_sec: float | None = Field(
        None,
        description="discharge capacity of pumps in m3/s, typically between 0.1 and 0.5 m3/s per 100ha",
    )
    discharge_capacity_m3_per_min: float | None = Field(
        None,
        description="discharge capacity of pumps in m3/min, typically between 6 and 15 m3/min per 100ha",
    )
    discharge_capacity_m3_per_day: float | None = Field(
        None,
        description="discharge capacity of pumps in m3/day, typically between 9000 and 40000 m3/day per 100ha",
    )
    discharge_capacity_mm_d: float | None = Field(
        None,
        description="discharge capacity in mm/day, typically between 1 and 5 mm/day",
    )

    area_m2: float | None = Field(
        None, description="Area in m2, typically in the order magnitude 100000m2"
    )
    area_ha: float | None = Field(
        None, description="Area in hectares, typically in the order magnitude 10ha"
    )

    percentage_open_water: float = Field(
        2.0,
        gt=0,
        le=100,
        description=(
            "Percentage open water in het gebied, doorgaans tussen 0 en 10. Moet groter "
            "dan 0 zijn: zonder open water is er geen berging"
        ),
    )

    @model_validator(mode="after")
    def warn_on_unusual_percentage_open_water(self):
        # De grenzen zitten in het veld zelf en dus in het schema; dit is alleen nog een
        # signaal bij een ongebruikelijke maar geldige waarde.
        if self.percentage_open_water > 10:
            warnings.warn(
                "percentage_open_water is often be between 0 and 10, consider checking your input"
            )
        return self

    @model_validator(mode="after")
    def validate_area(self):
        if self.area_ha is not None:
            self.area_m2 = self.area_ha * 10000
        elif self.area_m2 is not None:
            self.area_ha = self.area_m2 / 10000
        else:
            raise ModelRetry("One of area_m2 or area_ha must be provided.")
        return self

    @model_validator(mode="after")
    def validate_discharge_capacity(self):
        if self.discharge_capacity_m3_per_sec is not None:
            self.discharge_capacity_m3_per_min = self.discharge_capacity_m3_per_sec * 60
            self.discharge_capacity_m3_per_day = (
                self.discharge_capacity_m3_per_sec * 60 * 60 * 24
            )
        elif self.discharge_capacity_m3_per_min is not None:
            self.discharge_capacity_m3_per_sec = self.discharge_capacity_m3_per_min / 60
            self.discharge_capacity_m3_per_day = (
                self.discharge_capacity_m3_per_min * 60 * 24
            )
        elif self.discharge_capacity_m3_per_day is not None:
            self.discharge_capacity_m3_per_sec = self.discharge_capacity_m3_per_day / (
                60 * 60 * 24
            )
            self.discharge_capacity_m3_per_min = self.discharge_capacity_m3_per_day / (
                60 * 24
            )

        # the previous code ensures that if any of the m3/{t} is provided, all are calculated
        # this focuses on the mm/d calculation
        # in case m3/{t} is provided, calculate the mm/d
        if self.discharge_capacity_mm_d is None:
            self.discharge_capacity_mm_d = (
                self.discharge_capacity_m3_per_day / self.area_m2 * 1000
            )

        # In case mm/d is provided, calculate the others
        elif self.discharge_capacity_mm_d is not None:
            self.discharge_capacity_m3_per_day = (
                self.discharge_capacity_mm_d / 1000 * self.area_m2
            )
            self.discharge_capacity_m3_per_min = self.discharge_capacity_m3_per_day / (
                60 * 24
            )
            self.discharge_capacity_m3_per_sec = self.discharge_capacity_m3_per_day / (
                60 * 60 * 24
            )
        else:
            raise ModelRetry(
                "One of discharge_capacity_m3_per_sec, discharge_capacity_m3_per_min, or discharge_capacity_m3_per_day must be provided."
            )
        return self


class BaseInput(RainfallInput, WaterSystemInput):
    """
    Base input model for rules of thumb tools.
    Requires return periods to be specified.
    """

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput

from pydantic import Field, model_validator
from typing import Any, Dict

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
)


class DischargeInputGivenH(RainfallInput, WaterSystemInput):
    """
    Input model for Discharge tool.
    Currently, no parameters are required, but this can be extended in the future.

    Discharge = Afvoeren
    """

    delta_h_available: float = Field(
        ..., description="Maximum increase in water level available in meters."
    )

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput


class DischargeInputGivenDischarge(RainfallInput, WaterSystemInput):
    """
    Input model for Discharge tool.
    Currently, no parameters are required, but this can be extended in the future.

    Discharge = Afvoeren
    """

    delta_discharge_capacity_m3_per_sec: float | None = Field(
        None,
        description="Additional discharge capacity of pumps in m3/s, typically between 0.1 and 0.5 m3/s per 100ha",
    )
    delta_discharge_capacity_m3_per_min: float | None = Field(
        None,
        description="Additional discharge capacity of pumps in m3/min, typically between 6 and 15 m3/min per 100ha",
    )
    delta_discharge_capacity_m3_per_day: float | None = Field(
        None,
        description="Additional discharge capacity of pumps in m3/day, typically between 9000 and 40000 m3/day per 100ha",
    )
    delta_discharge_capacity_mm_d: float | None = Field(
        None,
        description="Additional discharge capacity in mm/day, typically between 1 and 5 mm/day",
    )

    @model_validator(mode="after")
    def validate_delta_discharge_capacity(cls, values):
        if values.delta_discharge_capacity_m3_per_sec is not None:
            values.delta_discharge_capacity_m3_per_min = (
                values.delta_discharge_capacity_m3_per_sec * 60
            )
            values.delta_discharge_capacity_m3_per_day = (
                values.delta_discharge_capacity_m3_per_sec * 60 * 60 * 24
            )
        elif values.delta_discharge_capacity_m3_per_min is not None:
            values.delta_discharge_capacity_m3_per_sec = (
                values.delta_discharge_capacity_m3_per_min / 60
            )
            values.delta_discharge_capacity_m3_per_day = (
                values.delta_discharge_capacity_m3_per_min * 60 * 24
            )
        elif values.delta_discharge_capacity_m3_per_day is not None:
            values.delta_discharge_capacity_m3_per_sec = (
                values.delta_discharge_capacity_m3_per_day / (60 * 60 * 24)
            )
            values.delta_discharge_capacity_m3_per_min = (
                values.delta_discharge_capacity_m3_per_day / (60 * 24)
            )

        # the previous code ensures that if any of the m3/{t} is provided, all are calculated
        # this focuses on the mm/d calculation
        # in case m3/{t} is provided, calculate the mm/d
        if values.delta_discharge_capacity_mm_d is None:
            values.delta_discharge_capacity_mm_d = (
                values.delta_discharge_capacity_m3_per_day / values.area_m2 * 1000
            )

        # In case mm/d is provided, calculate the others
        elif values.delta_discharge_capacity_mm_d is not None:
            values.delta_discharge_capacity_m3_per_day = (
                values.delta_discharge_capacity_mm_d / 1000 * values.area_m2
            )
            values.delta_discharge_capacity_m3_per_min = (
                values.delta_discharge_capacity_m3_per_day / (60 * 24)
            )
            values.delta_discharge_capacity_m3_per_sec = (
                values.delta_discharge_capacity_m3_per_day / (60 * 60 * 24)
            )
        else:
            raise ModelRetry(
                "One of delta_discharge_capacity_m3_per_sec, delta_discharge_capacity_m3_per_min, or delta_discharge_capacity_m3_per_day must be provided."
            )
        return values


class DischargeOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

from pydantic import Field
from typing import Any, Dict


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

    delta_discharge_capacity_m3_per_min: float = Field(
        ...,
        description="Change in discharge capacity in m3/min (positive for increase, negative for decrease).",
    )


class DischargeOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

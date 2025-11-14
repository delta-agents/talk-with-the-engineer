from pydantic import Field
from typing import Dict, Any, Union


from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
)


class RetentionInputGivenH(RainfallInput, WaterSystemInput):
    """
    Input model for Retention tool.
    Requires return periods to be specified.

    Retention = Vasthouden
    """

    # Everything for rainfall is inherited from RainfallInput
    # Rest of the calculation:
    days_to_retain_discharge: int = Field(
        2,
        description="Number of extra days the water is retained in the polder",
    )
    delta_h_available: float = Field(
        ..., description="Maximum increase in water level available in meters."
    )


class RetentionInputGivenArea(RainfallInput, WaterSystemInput):
    """
    Input model for Retention tool.
    Requires return periods to be specified.

    Retention = Vasthouden
    """

    days_to_retain_discharge: int = Field(
        2,
        description="Number of extra days the water is retained in the polder",
    )
    delta_area_ha: float = Field(
        ...,
        description="Change in area in hectares for retaining water on land (positive for increase, negative for decrease).",
    )


class RetentionOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Table relationships")


# Type alias for utility functions
RetentionInput = Union[RetentionInputGivenH, RetentionInputGivenArea]

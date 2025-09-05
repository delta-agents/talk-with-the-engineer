from pydantic import Field
from typing import Any, Dict

from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
)


class StoreInput(RainfallInput, WaterSystemInput):
    """
    Input model for Store tool.

    Store = Bergen
    """

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput
    delta_h_available: float = Field(
        ..., description="Maximum increase in water level available in meters."
    )


class StoreOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

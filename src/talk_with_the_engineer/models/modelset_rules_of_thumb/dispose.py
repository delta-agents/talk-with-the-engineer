from pydantic import Field
from typing import Any, Dict


from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,WaterSystemInput
)


class DisposeInput(RainfallInput, WaterSystemInput):
    """
    Input model for Dispose tool.
    Currently, no parameters are required, but this can be extended in the future.

    Dispose = Afvoeren
    """
    delta_h_available: float = Field(0.1, description="Maximum increase in water level available in meters.")


    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput

class DisposeOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

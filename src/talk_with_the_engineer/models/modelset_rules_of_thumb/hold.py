from pydantic import Field
from typing import Dict, Any


from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
)


class HoldInput(RainfallInput):
    """
    Input model for Hold tool.
    Requires return periods to be specified.

    Hold = Vasthouden
    """

    # Everything for rainfall is inherited from RainfallInput
    # Rest of the calculation:


class HoldOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Table relationships")

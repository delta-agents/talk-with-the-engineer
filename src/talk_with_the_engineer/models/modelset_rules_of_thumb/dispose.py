from pydantic import Field
from typing import Any, Dict

from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
)


class DisposeInput(RainfallInput):
    """
    Input model for Dispose tool.
    Currently, no parameters are required, but this can be extended in the future.

    Dispose = Afvoeren
    """

    # Everything for rainfall is inherited from RainfallInput
    # Rest of the calculation:


class DisposeOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

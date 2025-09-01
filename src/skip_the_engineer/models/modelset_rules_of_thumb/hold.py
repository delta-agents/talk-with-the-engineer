from pydantic import BaseModel, Field
from typing import Dict

from skip_the_engineer.models.base import EngineerBaseModel


class HoldInput(EngineerBaseModel):
    """
    Input model for Vasthouden tool.
    Currently, no parameters are required, but this can be extended in the future.
    """

    return_period: int = Field(
        ..., description="Return period for the Vasthouden tool."
    )


class HoldOutput(BaseModel):
    data: Dict[str, int] = Field(..., description="data dictionary")
    description: str = Field(..., description="Table relationships")

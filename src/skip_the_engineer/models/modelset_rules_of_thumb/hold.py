from pydantic import BaseModel, Field
from typing import Dict

from skip_the_engineer.models.base import EngineerBaseModel


class HoldInput(EngineerBaseModel):
    """
    Input model for Hold tool.
    Requires return periods to be specified.
    """

    return_period: int = Field(..., description="Return period for the Hold tool.")


class HoldOutput(BaseModel):
    data: Dict[str, int] = Field(..., description="data dictionary")
    description: str = Field(..., description="Table relationships")

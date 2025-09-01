from pydantic import BaseModel, Field
from typing import Dict

from skip_the_engineer.models.base import EngineerBaseModel


class Example2Input(EngineerBaseModel):
    """
    Input model for Example2Input tool.
    Currently, no parameters are required, but this can be extended in the future.
    """

    factor: int = Field(..., description="A factor for the example2 tool")


class Example2Output(EngineerBaseModel):
    data: Dict[str, int] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the example2 output")

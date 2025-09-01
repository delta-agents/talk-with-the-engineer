from pydantic import BaseModel, Field
from typing import Dict

from AI_agents_template.models.base import ExampleBaseModel


class Example1Input(ExampleBaseModel):
    """
    Input model for Example1Input tool.
    Currently, no parameters are required, but this can be extended in the future.
    """

    index: int = Field(
        ..., description="Index to use in the example tool. smaller than 5"
    )


class Example1Output(BaseModel):
    data: Dict[str, int] = Field(..., description="data dictionary")
    description: str = Field(..., description="Table relationships")

from pydantic import BaseModel, Field
from typing import Dict

from skip_the_engineer.models.base import EngineerBaseModel


class StoreInput(EngineerBaseModel):
    """
    Input model for Store tool.
    Currently, no parameters are required, but this can be extended in the future.
    """

    return_period: int = Field(
        ..., description="Return period for the Store tool."
    )


class StoreOutput(BaseModel):
    data: Dict[str, int] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

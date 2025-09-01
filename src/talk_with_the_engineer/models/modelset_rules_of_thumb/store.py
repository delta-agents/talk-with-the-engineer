from pydantic import BaseModel, Field
from typing import Dict

from talk_with_the_engineer.models.base import EngineerBaseModel


class StoreInput(EngineerBaseModel):
    """
    Input model for Store tool.
    Currently, no parameters are required, but this can be extended in the future.

    Store = Bergen
    """

    return_period: int = Field(..., description="Return period for the Store tool.")
    area: int = Field(..., description="Area in square meters.")


class StoreOutput(BaseModel):
    data: Dict[str, int] = Field(..., description="data dictionary")
    description: str = Field(..., description="Description of the data")

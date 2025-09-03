from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerBaseModel

# as defined in talk_with_the_engineer/models/modelset_rules_of_thumb/utils_rainfall_stats.py
# Alle gegeven zijn overgenomen uit tabel 6 en 7 in deelrapport 3 (regionale statistiek voor extreme neerslag) van STOWA-2019
RETURN_PERIODS = [
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    25.0,
    50.0,
    100.0,
    200.0,
    250.0,
    500.0,
    1000.0,
]

LENGTH_EVENT_HRS = [
    48.0,
    96.0,
    192.0,
]

TIME_OF_YEAR = [
    "winter",
    "summer",
]

DAYS_TO_DISPOSE = [2, 3, 4]
RAINFALL_REGIMES = ["LL", "L", "R", "H"]


class HoldInput(EngineerBaseModel):
    """
    Input model for Hold tool.
    Requires return periods to be specified.

    Hold = Vasthouden
    """

    # Everything for rainfall
    return_period: int = Field(
        ...,
        description=f"Return period for the Hold tool: must be one of {RETURN_PERIODS}",
    )
    time_of_year: str = Field(
        "summer",
        description=f"Time of year for the Hold tool, default summer. Must be one of {TIME_OF_YEAR}.",
    )
    length_event_hrs: float = Field(
        96.0,
        description=f"Length of the event in hours for the Hold tool, default 96. Must be one of {LENGTH_EVENT_HRS}.",
    )
    rainfall_regime: str = Field(
        "R",
        description=f"Rainfall regime for the Hold tool: must be one of {RAINFALL_REGIMES}",
    )

    # Everything for the rest of the calculation
    days_to_dispose: int = Field(
        3,
        description=f"Number of days to dispose of the water, default 3. Must be one of {DAYS_TO_DISPOSE}",
    )

    # validate the rainfall stats
    @model_validator(mode="after")
    def validate_length_event_hrs(cls, values):
        if (
            values.length_event_hrs is not None
            and values.length_event_hrs not in LENGTH_EVENT_HRS
        ):
            raise ModelRetry(f"length_event_hrs must be one of: {LENGTH_EVENT_HRS}.")
        return values

    @model_validator(mode="after")
    def validate_return_period(cls, values):
        if (
            values.return_period is not None
            and values.return_period not in RETURN_PERIODS
        ):
            raise ModelRetry(f"return_period must be one of: {RETURN_PERIODS}.")
        return values

    @model_validator(mode="after")
    def validate_time_of_year(cls, values):
        if values.time_of_year is not None and values.time_of_year not in TIME_OF_YEAR:
            raise ModelRetry(f"time_of_year must be one of: {TIME_OF_YEAR}.")
        return values


class HoldOutput(BaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Table relationships")

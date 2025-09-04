import warnings
from pydantic import Field, model_validator

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

RAINFALL_REGIMES = ["LL", "L", "R", "H"]

NAME_RAINFALL_PATTERN = ["p_0", "p1a", "p1b", "p1c", "p1d", "p2a", "p2b"]

DAYS_TO_DISPOSE = [2, 3, 4]


class RainfallInput(EngineerBaseModel):
    """
    Input model for Hold tool.
    Requires return periods to be specified.

    Hold = Vasthouden
    """

    # Everything for rainfall
    return_period: int = Field(
        ...,
        description=f"Return period used for the tool: must be one of {RETURN_PERIODS}",
    )
    time_of_year: str = Field(
        "summer",
        description=f"Time of year used for the tool, default summer. Must be one of {TIME_OF_YEAR}.",
    )
    length_event_hrs: float = Field(
        96.0,
        description=f"Length of the event in hours used for the tool, default 96. Must be one of {LENGTH_EVENT_HRS}.",
    )
    rainfall_regime: str = Field(
        "R",
        description=f"Rainfall regime used for the tool, default R. Must be one of {RAINFALL_REGIMES}",
    )
    name_rainfall_pattern: str = Field(
        "p1c",
        description=f"Name of the rainfall pattern used for the tool, default p1c. Must be one of {NAME_RAINFALL_PATTERN}",
    )

    days_to_dispose: int = Field(
        3,
        description=f"Number of days to dispose of the water, default 3. Must be one of {DAYS_TO_DISPOSE}",
    )

    # validate the rainfall stats
    @model_validator(mode="after")
    def validate_length_event_hrs(cls, values):
        if values.length_event_hrs not in LENGTH_EVENT_HRS:
            raise ModelRetry(f"length_event_hrs must be one of: {LENGTH_EVENT_HRS}.")
        return values

    @model_validator(mode="after")
    def validate_return_period(cls, values):
        if values.return_period not in RETURN_PERIODS:
            raise ModelRetry(f"return_period must be one of: {RETURN_PERIODS}.")
        return values

    @model_validator(mode="after")
    def validate_time_of_year(cls, values):
        if values.time_of_year not in TIME_OF_YEAR:
            raise ModelRetry(f"time_of_year must be one of: {TIME_OF_YEAR}.")
        return values

    @model_validator(mode="after")
    def validate_rainfall_regime(cls, values):
        if values.rainfall_regime not in RAINFALL_REGIMES:
            raise ModelRetry(f"rainfall_regime must be one of: {RAINFALL_REGIMES}.")
        return values

    @model_validator(mode="after")
    def validate_name_rainfall_pattern(cls, values):
        if values.name_rainfall_pattern not in NAME_RAINFALL_PATTERN:
            raise ModelRetry(
                f"name_rainfall_pattern must be one of: {NAME_RAINFALL_PATTERN}."
            )
        return values

    @model_validator(mode="after")
    def validate_days_to_dispose(cls, values):
        if values.days_to_dispose not in DAYS_TO_DISPOSE:
            raise ModelRetry(f"days_to_dispose must be one of: {DAYS_TO_DISPOSE}.")
        return values


class WaterSystemInput(EngineerBaseModel):
    """
    Input model containing all the parameters for water systems.
    """

    disposal_capacity_m3_per_sec: float | None = Field(
        None,
        description="Disposal capacity of pumps in m3/s, typically between 0.1 and 0.5 m3/s per 100ha",
    )
    disposal_capacity_m3_per_min: float | None = Field(
        None,
        description="Disposal capacity of pumps in m3/min, typically between 6 and 15 m3/min per 100ha",
    )
    disposal_capacity_m3_per_day: float | None = Field(
        None,
        description="Disposal capacity of pumps in m3/day, typically between 9000 and 40000 m3/day per 100ha",
    )

    area_m2: float | None = Field(
        None, description="Area in m2, typically in the order magnitude 100000m2"
    )
    area_ha: float | None = Field(
        None, description="Area in hectares, typically in the order magnitude 10ha"
    )

    percentage_open_water: float = Field(
        2.0,
        description="Percentage of open water in the area, typically between 0 and 10%",
    )

    @model_validator(mode="after")
    def validate_percentage_open_water(cls, values):
        if values.percentage_open_water > 10:
            warnings.warn(
                "percentage_open_water is often be between 0 and 10, consider checking your input"
            )
        elif not (0 <= values.percentage_open_water <= 100):
            ModelRetry("percentage_open_water must be between 0 and 100")
        return values

    @model_validator(mode="after")
    def validate_area(cls, values):
        if values.area_ha is not None:
            values.area_m2 = values.area_ha * 10000
        elif values.area_m2 is not None:
            values.area_ha = values.area_m2 / 10000
        else:
            raise ModelRetry("One of area_m2 or area_ha must be provided.")
        return values

    @model_validator(mode="after")
    def validate_disposal_capacity(cls, values):
        if values.disposal_capacity_m3_per_sec is not None:
            values.disposal_capacity_m3_per_min = (
                values.disposal_capacity_m3_per_sec * 60
            )
            values.disposal_capacity_m3_per_day = (
                values.disposal_capacity_m3_per_sec * 60 * 60 * 24
            )
        elif values.disposal_capacity_m3_per_min is not None:
            values.disposal_capacity_m3_per_sec = (
                values.disposal_capacity_m3_per_min / 60
            )
            values.disposal_capacity_m3_per_day = (
                values.disposal_capacity_m3_per_min * 60 * 24
            )
        elif values.disposal_capacity_m3_per_day is not None:
            values.disposal_capacity_m3_per_sec = (
                values.disposal_capacity_m3_per_day / (60 * 60 * 24)
            )
            values.disposal_capacity_m3_per_min = (
                values.disposal_capacity_m3_per_day / (60 * 24)
            )
        else:
            raise ModelRetry(
                "One of disposal_capacity_m3_per_sec, disposal_capacity_m3_per_min, or disposal_capacity_m3_per_day must be provided."
            )
        return values

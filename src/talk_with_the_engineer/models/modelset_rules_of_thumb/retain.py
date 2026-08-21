from pydantic import ConfigDict, Field, model_validator
from typing import Union

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
)


class RetentionInputGivenH(RainfallInput, WaterSystemInput):
    """
    Input model for Retention tool.
    Requires return periods to be specified.

    Retention = Vasthouden
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "percentage_open_water": 3.5,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "time_of_year": "winter",
                "length_event_hrs": 96.0,
                "rainfall_regime": "R",
                "name_rainfall_pattern": "p1c",
                "days_to_discharge": 3,
                "delta_h_available": 1.0,
                "days_to_retain_discharge": 2,
            }
        }
    )

    # Everything for rainfall is inherited from RainfallInput
    # Rest of the calculation:
    days_to_retain_discharge: int = Field(
        2,
        description="Number of extra days the water is retained in the polder",
    )
    delta_h_available: float = Field(
        ..., description="Maximum increase in water level available in meters."
    )


class RetentionInputGivenArea(RainfallInput, WaterSystemInput):
    """
    Input model for Retention tool.
    Requires return periods to be specified.

    Retention = Vasthouden
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "percentage_open_water": 3.5,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "time_of_year": "winter",
                "length_event_hrs": 96.0,
                "rainfall_regime": "R",
                "name_rainfall_pattern": "p1c",
                "days_to_discharge": 3,
                "delta_area_ha": 1158,
                "days_to_retain_discharge": 2,
            }
        }
    )

    days_to_retain_discharge: int = Field(
        2,
        description="Number of extra days the water is retained in the polder",
    )
    delta_area_ha: float | None = Field(
        None,
        description="Change in area in hectares for retaining water on land (positive for increase, negative for decrease).",
    )
    delta_area_m2: float | None = Field(
        None,
        description="Change in area in square meters for retaining water on land (positive for increase, negative for decrease).",
    )

    @model_validator(mode="after")
    def validate_area_available(self):
        if self.delta_area_ha is not None:
            self.delta_area_m2 = self.delta_area_ha * 10000
        elif self.delta_area_m2 is not None:
            self.delta_area_ha = self.delta_area_m2 / 10000
        else:
            raise ModelRetry("One of delta_area_m2 or delta_area_ha must be provided.")
        return self


class RetentionOutput(MeasureOutput):
    """Uitvoer van de maatregel; velden komen uit MeasureOutput."""


# Type alias for utility functions
RetentionInput = Union[RetentionInputGivenH, RetentionInputGivenArea]

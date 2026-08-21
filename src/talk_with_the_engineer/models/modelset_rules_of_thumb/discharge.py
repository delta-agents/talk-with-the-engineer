from pydantic import ConfigDict, Field, model_validator

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
)


class DischargeInputGivenH(RainfallInput, WaterSystemInput):
    """
    Input model for Discharge tool.
    Currently, no parameters are required, but this can be extended in the future.

    Discharge = Afvoeren
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
            }
        }
    )

    delta_h_available: float = Field(
        ..., description="Maximum increase in water level available in meters."
    )

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput


class DischargeInputGivenDischarge(RainfallInput, WaterSystemInput):
    """
    Input model for Discharge tool.
    Currently, no parameters are required, but this can be extended in the future.

    Discharge = Afvoeren
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
                "delta_discharge_capacity_m3_per_sec": 2.5,
            }
        }
    )

    delta_discharge_capacity_m3_per_sec: float | None = Field(
        None,
        description="Additional discharge capacity of pumps in m3/s, typically between 0.1 and 0.5 m3/s per 100ha",
    )
    delta_discharge_capacity_m3_per_min: float | None = Field(
        None,
        description="Additional discharge capacity of pumps in m3/min, typically between 6 and 15 m3/min per 100ha",
    )
    delta_discharge_capacity_m3_per_day: float | None = Field(
        None,
        description="Additional discharge capacity of pumps in m3/day, typically between 9000 and 40000 m3/day per 100ha",
    )
    delta_discharge_capacity_mm_d: float | None = Field(
        None,
        description="Additional discharge capacity in mm/day, typically between 1 and 5 mm/day",
    )

    @model_validator(mode="after")
    def validate_delta_discharge_capacity(self):
        if self.delta_discharge_capacity_m3_per_sec is not None:
            self.delta_discharge_capacity_m3_per_min = (
                self.delta_discharge_capacity_m3_per_sec * 60
            )
            self.delta_discharge_capacity_m3_per_day = (
                self.delta_discharge_capacity_m3_per_sec * 60 * 60 * 24
            )
        elif self.delta_discharge_capacity_m3_per_min is not None:
            self.delta_discharge_capacity_m3_per_sec = (
                self.delta_discharge_capacity_m3_per_min / 60
            )
            self.delta_discharge_capacity_m3_per_day = (
                self.delta_discharge_capacity_m3_per_min * 60 * 24
            )
        elif self.delta_discharge_capacity_m3_per_day is not None:
            self.delta_discharge_capacity_m3_per_sec = (
                self.delta_discharge_capacity_m3_per_day / (60 * 60 * 24)
            )
            self.delta_discharge_capacity_m3_per_min = (
                self.delta_discharge_capacity_m3_per_day / (60 * 24)
            )

        # the previous code ensures that if any of the m3/{t} is provided, all are calculated
        # this focuses on the mm/d calculation
        # in case m3/{t} is provided, calculate the mm/d
        if self.delta_discharge_capacity_mm_d is None:
            self.delta_discharge_capacity_mm_d = (
                self.delta_discharge_capacity_m3_per_day / self.area_m2 * 1000
            )

        # In case mm/d is provided, calculate the others
        elif self.delta_discharge_capacity_mm_d is not None:
            self.delta_discharge_capacity_m3_per_day = (
                self.delta_discharge_capacity_mm_d / 1000 * self.area_m2
            )
            self.delta_discharge_capacity_m3_per_min = (
                self.delta_discharge_capacity_m3_per_day / (60 * 24)
            )
            self.delta_discharge_capacity_m3_per_sec = (
                self.delta_discharge_capacity_m3_per_day / (60 * 60 * 24)
            )
        else:
            raise ModelRetry(
                "One of delta_discharge_capacity_m3_per_sec, delta_discharge_capacity_m3_per_min, or delta_discharge_capacity_m3_per_day must be provided."
            )
        return self


class DischargeOutput(MeasureOutput):
    """Uitvoer van de maatregel; velden komen uit MeasureOutput."""

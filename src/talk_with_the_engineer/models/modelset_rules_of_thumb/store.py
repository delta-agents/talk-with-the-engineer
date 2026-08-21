from pydantic import Field, model_validator

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
)


class StoreInputGivenH(RainfallInput, WaterSystemInput):
    """
    Input model for Store tool.

    Store = Bergen
    """

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput
    delta_h_available: float = Field(
        ..., description="Maximum increase in water level available in meters."
    )


class StoreInputGivenArea(RainfallInput, WaterSystemInput):
    """
    Input model for Store tool.

    Store = Bergen
    """

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput
    area_available_m2: float | None = Field(
        None,
        description="Maximum increase in area of open water available in square meters.",
    )

    # TODO add option to choose between given ha or m2
    area_available_ha: float | None = Field(
        None,
        description="Maximum increase in area of open water available in hectares.",
    )

    @model_validator(mode="after")
    def validate_area_available(cls, values):
        if values.area_available_ha is not None:
            values.area_available_m2 = values.area_available_ha * 10000
        elif values.area_available_m2 is not None:
            values.area_available_ha = values.area_available_m2 / 10000
        else:
            raise ModelRetry("One of area_m2 or area_ha must be provided.")
        return values


class StoreOutput(MeasureOutput):
    """Uitvoer van de maatregel; velden komen uit MeasureOutput."""

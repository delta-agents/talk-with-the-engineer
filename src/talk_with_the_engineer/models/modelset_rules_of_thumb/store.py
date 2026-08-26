from pydantic import ConfigDict, Field, model_validator

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    LevelBandInput,
)


class StoreInputGivenH(RainfallInput, LevelBandInput):
    """
    Input model for Store tool.

    Store = Bergen
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "delta_h_available": 1.0,
            }
        }
    )

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from LevelBandInput
    delta_h_available: float = Field(
        ...,
        gt=0,
        description=(
            "Waterstandstijging die het gebied nog aankan [m]; het doel waarop de "
            "maatregel wordt gedimensioneerd. Dit is de drooglegging tot het maaiveld "
            "van het laagste te beschermen perceel, dus gebiedsspecifiek: er is bewust "
            "geen standaardwaarde. Ordegrootte 0,2 tot 1,0 m."
        ),
    )


class StoreInputGivenArea(RainfallInput, LevelBandInput):
    """
    Input model for Store tool.

    Store = Bergen
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "area_available_ha": 200,
            }
        }
    )

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from LevelBandInput
    area_available_m2: float | None = Field(
        None,
        ge=0,
        description="Extra open water dat beschikbaar is [m2]",
    )

    # TODO add option to choose between given ha or m2
    area_available_ha: float | None = Field(
        None,
        ge=0,
        description="Extra open water dat beschikbaar is [ha]",
    )

    @model_validator(mode="after")
    def validate_area_available(self):
        if self.area_available_ha is not None:
            self.area_available_m2 = self.area_available_ha * 10000
        elif self.area_available_m2 is not None:
            self.area_available_ha = self.area_available_m2 / 10000
        else:
            raise ModelRetry("One of area_m2 or area_ha must be provided.")
        return self


class StoreOutput(MeasureOutput):
    """Uitvoer van de maatregel; velden komen uit MeasureOutput."""

from pydantic import ConfigDict, Field, model_validator

from pydantic_ai import ModelRetry


from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    RainfallInput,
    WaterSystemInput,
    discharge_capacity_in_all_units,
    discharge_capacity_to_m3_per_sec,
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
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "delta_h_available": 1.0,
            }
        }
    )

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
                "discharge_capacity_m3_per_sec": 5,
                "return_period": 100,
                "delta_discharge_capacity_m3_per_sec": 2.5,
            }
        }
    )

    delta_discharge_capacity_m3_per_sec: float | None = Field(
        None,
        description=(
            "Extra gemaalcapaciteit [m3/s]. Ter vergelijking: de hele bestaande "
            "capaciteit is gangbaar 1 tot 5 l/s/ha, oftewel 0,1 tot 0,5 m3/s per 100 ha."
        ),
    )
    delta_discharge_capacity_m3_per_min: float | None = Field(
        None,
        description=(
            "Extra gemaalcapaciteit [m3/min]. Ter vergelijking: de hele bestaande "
            "capaciteit is gangbaar 1 tot 5 l/s/ha, oftewel 6 tot 30 m3/min per 100 ha."
        ),
    )
    delta_discharge_capacity_m3_per_day: float | None = Field(
        None,
        description=(
            "Extra gemaalcapaciteit [m3/dag]. Ter vergelijking: de hele bestaande "
            "capaciteit is gangbaar 1 tot 5 l/s/ha, oftewel 8600 tot 43000 m3/dag per "
            "100 ha."
        ),
    )
    delta_discharge_capacity_mm_d: float | None = Field(
        None,
        description=(
            "Extra gemaalcapaciteit [mm/dag]. Ter vergelijking: de hele bestaande "
            "capaciteit is gangbaar 1 tot 5 l/s/ha, oftewel 8,6 tot 43 mm/dag. Let op: "
            "in mm/dag is het getal ruim acht keer zo groot als in l/s/ha."
        ),
    )
    delta_discharge_capacity_l_s_ha: float | None = Field(
        None,
        description=(
            "Extra gemaalcapaciteit [l/s/ha]. Ter vergelijking: de hele bestaande "
            "capaciteit is gangbaar 1 tot 5 l/s/ha."
        ),
    )

    @model_validator(mode="after")
    def validate_delta_discharge_capacity(self):
        """Vul de vijf delta-velden uit de ene die is opgegeven.

        Zelfde conversie als de absolute capaciteit, maar zonder ondergrens: een negatieve
        delta is de vraag wat er gebeurt als er gemaalcapaciteit wegvalt.
        """
        delta_m3_per_sec = discharge_capacity_to_m3_per_sec(
            m3_per_sec=self.delta_discharge_capacity_m3_per_sec,
            m3_per_min=self.delta_discharge_capacity_m3_per_min,
            m3_per_day=self.delta_discharge_capacity_m3_per_day,
            mm_d=self.delta_discharge_capacity_mm_d,
            l_s_ha=self.delta_discharge_capacity_l_s_ha,
            area_m2=self.area_m2,
        )
        if delta_m3_per_sec is None:
            raise ModelRetry(
                "Geef de extra gemaalcapaciteit op in een van deze eenheden: "
                "delta_discharge_capacity_l_s_ha, delta_discharge_capacity_m3_per_sec, "
                "delta_discharge_capacity_m3_per_min, delta_discharge_capacity_m3_per_day "
                "of delta_discharge_capacity_mm_d."
            )

        units = discharge_capacity_in_all_units(delta_m3_per_sec, self.area_m2)
        self.delta_discharge_capacity_m3_per_sec = units["m3_per_sec"]
        self.delta_discharge_capacity_m3_per_min = units["m3_per_min"]
        self.delta_discharge_capacity_m3_per_day = units["m3_per_day"]
        self.delta_discharge_capacity_mm_d = units["mm_d"]
        self.delta_discharge_capacity_l_s_ha = units["l_s_ha"]
        return self


class DischargeOutput(MeasureOutput):
    """Uitvoer van de maatregel; velden komen uit MeasureOutput."""

"""De toestand van een polder.

Dit is het `s` uit `s' = f(s, a, w)`: alles wat je van het watersysteem moet weten om de
waterstand bij een bui te kunnen uitrekenen. Elke maatregel is een mutatie van precies
een van deze velden.

Bewust geen `EngineerBaseModel`: dat voegt een `language`-veld toe, en dat hoort bij een
toolaanroep en niet bij een toestand.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Het rekenblad TttE_v03.xlsx houdt het afvoerende landoppervlak vast op de beginwaarde,
# ook wanneer land in open water wordt omgezet. Zolang niet vaststaat of dat een bewuste
# conservatieve keuze is, is dat hier het default gedrag; zie PLAN_TOOLS_REFACTOR.md V1.
# Het effect loopt op tot ongeveer 10 cm bij 30 % open water.
LAND_AREA_FOLLOWS_OPEN_WATER = False


class PolderState(BaseModel):
    """Toestand van een polder. Onveranderlijk: maatregelen leveren een nieuwe toestand."""

    model_config = ConfigDict(frozen=True)

    area_ha: float = Field(..., gt=0, description="Totaal oppervlak van de polder [ha]")
    pct_open_water: float = Field(
        ..., gt=0, le=100, description="Percentage open water [%]"
    )
    pump_capacity_m3_per_sec: float = Field(
        ..., ge=0, description="Gemaalcapaciteit [m3/s]"
    )
    retention_fraction: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Fractie van het LANDoppervlak waarvan de afvoer wordt vertraagd",
    )
    days_to_retain: int = Field(
        2, ge=0, description="Aantal dagen waarmee de afvoer wordt vertraagd"
    )
    drainage_area_ha: float | None = Field(
        None,
        description=(
            "Afvoerend oppervlak [ha]. None betekent dat het het open water volgt "
            "(area_ha - area_open_water_ha). Een expliciete waarde pint het vast op de "
            "beginsituatie, zoals het rekenblad doet; zie V1."
        ),
    )

    @property
    def area_open_water_ha(self) -> float:
        return self.pct_open_water / 100.0 * self.area_ha

    @property
    def area_land_ha(self) -> float:
        """Het oppervlak dat neerslag afvoert naar het open water."""
        if self.drainage_area_ha is not None:
            return self.drainage_area_ha
        return self.area_ha - self.area_open_water_ha

    @property
    def retention_area_ha(self) -> float:
        return self.retention_fraction * self.area_land_ha

    @model_validator(mode="after")
    def validate_drainage_area(self):
        if self.drainage_area_ha is not None and self.drainage_area_ha < 0:
            raise ValueError("drainage_area_ha kan niet negatief zijn")
        return self

    def replace(self, **changes) -> "PolderState":
        return self.model_copy(update=changes)

    @classmethod
    def from_water_system_input(
        cls,
        input,
        land_area_follows_open_water: bool = LAND_AREA_FOLLOWS_OPEN_WATER,
        retention_fraction: float = 0.0,
        days_to_retain: int = 2,
    ) -> "PolderState":
        """Bouw een toestand uit een toolinvoermodel.

        `WaterSystemInput` houdt vier afvoercapaciteitsvelden en twee oppervlakvelden bij,
        zodat de LLM in willekeurige eenheden mag praten. Die conversie hoort aan de
        toolgrens; de toestand heeft er precies een van elk.
        """
        area_open_water_ha = input.percentage_open_water / 100.0 * input.area_ha
        return cls(
            area_ha=input.area_ha,
            pct_open_water=input.percentage_open_water,
            pump_capacity_m3_per_sec=input.discharge_capacity_m3_per_sec,
            retention_fraction=retention_fraction,
            days_to_retain=days_to_retain,
            drainage_area_ha=(
                None
                if land_area_follows_open_water
                else input.area_ha - area_open_water_ha
            ),
        )

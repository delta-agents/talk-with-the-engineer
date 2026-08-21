"""De toestand van een polder.

Dit is het `s` uit `s' = f(s, a, w)`: alles wat je van het watersysteem moet weten om de
waterstand bij een bui te kunnen uitrekenen. Elke maatregel is een mutatie van precies
een van deze velden.

Bewust geen `EngineerBaseModel`: dat voegt een `language`-veld toe, en dat hoort bij een
toolaanroep en niet bij een toestand.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WaterBalanceMode(str, Enum):
    """Welke termen de waterbalans meeneemt.

    `POLDER` is de balans zoals Ton Botterhuis hem formuleert: de waterstandverandering
    is de neerslag die direct op het open water valt, plus het water dat op het
    landoppervlak tot afvoer komt. Land dat in open water verandert voert dus niet meer
    af, maar de neerslag die erop valt verdwijnt niet.

    `SPREADSHEET` reproduceert `scripts/scripts_Ton/TttE_v03.xlsx`, dat beide dingen niet
    doet: het afvoerende oppervlak blijft vast op de beginwaarde en de neerslag die direct
    op het open water valt ontbreekt. Dat is geen fout van het rekenblad maar de grens van
    wat er in een blad past; deze modus bestaat om de gouden regressietest te kunnen
    blijven draaien.

    Het verschil is bij 3,5 % open water 10 cm op een stijging van 1,70 m, en de twee
    ontbrekende termen werken tegen elkaar in: krimpend land verlaagt de stand, directe
    neerslag verhoogt hem. Zie PLAN_TOOLS_REFACTOR.md V1.
    """

    POLDER = "polder"
    SPREADSHEET = "spreadsheet"


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
    target_level_rise_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilopzet: hoeveel het streefpeil is verhoogd ten opzichte van het "
            "oorspronkelijke peil [m]. Dit is de enige toestandsvariabele die water "
            "vasthoudt voor droge perioden, en hij kost een-op-een drooglegging"
        ),
    )
    water_balance: WaterBalanceMode = Field(
        WaterBalanceMode.POLDER,
        description="Welke termen de waterbalans meeneemt; zie WaterBalanceMode",
    )
    drainage_area_ha: float | None = Field(
        None,
        description=(
            "Afvoerend oppervlak [ha]. Alleen van toepassing in SPREADSHEET-modus, waar "
            "het vast blijft op de beginsituatie. In POLDER-modus volgt het het open "
            "water en wordt dit veld genegeerd."
        ),
    )

    @property
    def area_open_water_ha(self) -> float:
        return self.pct_open_water / 100.0 * self.area_ha

    @property
    def area_land_ha(self) -> float:
        """Het oppervlak dat neerslag afvoert naar het open water."""
        if (
            self.water_balance is WaterBalanceMode.SPREADSHEET
            and self.drainage_area_ha is not None
        ):
            return self.drainage_area_ha
        return self.area_ha - self.area_open_water_ha

    @property
    def includes_direct_precipitation(self) -> bool:
        """Valt de neerslag op het open water mee in de balans?"""
        return self.water_balance is WaterBalanceMode.POLDER

    @property
    def retention_area_ha(self) -> float:
        return self.retention_fraction * self.area_land_ha

    @property
    def retained_volume_mm(self) -> float:
        """Vastgehouden voorraad door peilopzet, uitgedrukt in mm over de hele polder.

        Dit is de droogte-uitlezing. Het gemaal pompt tot het streefpeil en niet verder -
        de afkap op nul in de waterbalans *is* dat streefpeil - dus alles wat erboven komt
        verdwijnt uiteindelijk, welke maatregel je ook neemt. Wat je overhoudt is precies
        de berging onder het streefpeil, en de enige manier om die te vergroten is het
        streefpeil optrekken of het open water uitbreiden.

        Zie PLAN_TOOLS_REFACTOR.md §8.2. Een uitlezing op basis van weggepompt volume
        werkt hier niet: die onderscheidt de maatregelen alleen zolang het rekenvenster te
        kort is om leeg te lopen, en convergeert daarna naar hetzelfde getal.
        """
        return (
            self.target_level_rise_m * (self.area_open_water_ha / self.area_ha) * 1000.0
        )

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
        water_balance: WaterBalanceMode = WaterBalanceMode.POLDER,
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
            water_balance=water_balance,
            drainage_area_ha=input.area_ha - area_open_water_ha,
        )

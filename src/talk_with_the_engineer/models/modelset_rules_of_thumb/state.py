"""De toestand van een polder.

Dit is het `s` uit `s' = f(s, a, w)`: alles wat je van het watersysteem moet weten om de
waterstand bij een bui te kunnen uitrekenen. Elke maatregel is een mutatie van precies
een van deze velden.

Bewust geen `EngineerBaseModel`: dat voegt een `language`-veld toe, en dat hoort bij een
toolaanroep en niet bij een toestand.
"""

from pydantic import ConfigDict, Field

from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    ConnectedState,
    single_pump_connection,
)


class PolderState(ConnectedState):
    """Toestand van een polder. Onveranderlijk: maatregelen leveren een nieuwe toestand.

    `target_level_rise_m` en `level_margin_m` vormen samen de peilband
    `[-level_margin_m, +target_level_rise_m]` rond het oorspronkelijke peil. Het zijn
    bewust twee velden en niet een grootheid met een teken, want ze gedragen zich
    verschillend:

    * peilopzet is lineair en onbegrensd - elke centimeter opzet is een centimeter minder
      marge tot de inundatienorm, en hij koopt evenveel voorraad;
    * peilmarge verzadigt - op de referentiebui levert 10 cm marge 10,0 cm lagere piek en
      levert 30 cm marge nog steeds 10,5 cm, omdat het gemaal 0,31 m per dag leegmaalt en
      de droge uren voor de piek op zijn.

    Peilverlaging koop je, voorbemaling voer je uit. Zie PLAN_UITWISSELING_EN_NETWERK.md
    Sec. 4.3.
    """

    model_config = ConfigDict(frozen=True)

    area_ha: float = Field(..., gt=0, description="Totaal oppervlak van de polder [ha]")
    pct_open_water: float = Field(
        ..., gt=0, le=100, description="Percentage open water [%]"
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
    level_margin_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilmarge: hoe diep onder het streefpeil het gemaal mag doormalen [m]. Nul "
            "is het klassieke gedrag, waarbij het gemaal op streefpeil stopt"
        ),
    )

    @property
    def area_open_water_ha(self) -> float:
        return self.pct_open_water / 100.0 * self.area_ha

    @property
    def area_land_ha(self) -> float:
        """Het oppervlak dat neerslag afvoert naar het open water.

        Land dat in open water verandert voert niet meer af; de neerslag die erop valt
        verdwijnt niet maar komt via `simulate` direct op het open water terecht.
        """
        return self.area_ha - self.area_open_water_ha

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

    def replace(self, **changes) -> "PolderState":
        return self.model_copy(update=changes)

    @classmethod
    def from_water_system_input(
        cls,
        input,
        retention_fraction: float = 0.0,
        days_to_retain: int = 2,
    ) -> "PolderState":
        """Bouw een toestand uit een toolinvoermodel.

        `WaterSystemInput` houdt vier afvoercapaciteitsvelden en twee oppervlakvelden bij,
        zodat de LLM in willekeurige eenheden mag praten. Die conversie hoort aan de
        toolgrens; de toestand heeft er precies een van elk.

        De peilband komt mee als CONTEXT: een polder die al is opgezet of die voormaalt,
        rekent vanaf die stand. `getattr` omdat de twee bandvelden op `LevelBandInput`
        staan en niet elk invoermodel daarvan erft - de aanvoertools bouwen hun eigen
        toestand, met de hele band in `drawdown_available_m` en dus in `level_margin_m`.
        """
        return cls(
            area_ha=input.area_ha,
            pct_open_water=input.percentage_open_water,
            connections=single_pump_connection(input.discharge_capacity_m3_per_sec),
            retention_fraction=retention_fraction,
            days_to_retain=days_to_retain,
            target_level_rise_m=getattr(input, "target_level_rise_m", 0.0) or 0.0,
            level_margin_m=getattr(input, "level_margin_m", 0.0) or 0.0,
        )

"""Maatregel aanvoeren: meer inlaatcapaciteit tegen een neerslagtekort.

Dezelfde transitie als afvoeren en dezelfde rekenkern, met de klem gespiegeld. Wat wél
eigen is, is alles eromheen - en dat is precies de reden dat dit een eigen bestand met
eigen modellen heeft in plaats van een vlag op de afvoertool:

| | afvoeren | aanvoeren |
|---|---|---|
| aandrijving | een bui van 48 tot 192 uur | een tekort van weken |
| exogene invoer | STOWA-neerslagstatistiek | tekort in mm/dag maal een aantal dagen |
| doel | de stijging onder een grens houden | het peil boven een ondergrens houden |
| kunstwerk | gemaal, 1 tot 5 l/s/ha | inlaat, 0,3 tot 0,4 l/s/ha |
| prijs | investering per m3/s | geen; wat aanvoer kost is het water |

Zie PLAN_UITWISSELING_EN_NETWERK.md Sec. 2: verenig de transitie, verenig de toestand,
verenig de tool niet.
"""

from pydantic import ConfigDict, Field, model_validator

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerBaseModel
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    Assumption,
    ModelCaveat,
    Sensitivity,
    AssumedDefaults,
    WaterSystemInput,
    discharge_capacity_in_all_units,
    discharge_capacity_to_m3_per_sec,
    hide_null_branch,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    SolveStatus,
    round_floats,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState

from pydantic import model_serializer


class DeficitInput(AssumedDefaults):
    """Het neerslagtekort: het exogene deel van de droogte-invoer.

    Twee getallen en geen statistiek. Welke droogtereeks hier thuishoort is een open vraag
    - de KNMI-neerslagtekortreeks met zijn referentielijnen, een jaar als 1976 of 2018, of
    de Deltascenario's als scenario-as - en een verkeerd gekozen statistiek is erger dan
    een expliciet getal. Zie PLAN_UITWISSELING_EN_NETWERK.md V7.
    """

    deficit_mm_per_day: float = Field(
        ...,
        gt=0,
        description=(
            "Netto neerslagtekort [mm/dag]: verdamping minus neerslag. Een warme zomerdag "
            "zonder regen zit rond 4 mm/dag. Dit is gebiedsspecifiek en seizoensgebonden, "
            "dus er is bewust geen standaardwaarde. Ordegrootte 2 tot 5 mm/dag."
        ),
    )
    length_days: int | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Hoeveel dagen het tekort aanhoudt. Weet je dit niet, laat het veld dan weg in "
            "plaats van het te schatten; de tool rekent met 30 dagen en meldt dat in "
            "`assumptions`."
        ),
    )

    available_source_volume_m3: float | None = Field(
        None,
        ge=0,
        json_schema_extra=hide_null_branch,
        description=(
            "Wat de bron over deze periode kan leveren [m3]. Laat weg als je dat niet weet - "
            "dan rekent de tool met een onbeperkte bron, en dat is een DRAGENDE aanname: hij "
            "veronderstelt dat het water bij de inlaat staat. Voor laag Nederland is dat "
            "vaak onschuldig, voor de zandgronden niet. Vul hem in en de aanname wordt een "
            "getal: dan staat er vanaf welke dag de inlaat droog staat"
        ),
    )

    @model_validator(mode="after")
    def fill_deficit_defaults(self):
        self._apply_fallbacks("length_days")
        return self


class SupplyWaterSystemInput(WaterSystemInput):
    """Het watersysteem plus de bruikbare diepte onder streefpeil.

    `drawdown_available_m` is verplicht en heeft bewust geen standaardwaarde, om dezelfde
    reden als `delta_h_available` op de natte kant: het is de gebiedsspecifieke grootheid
    waar het antwoord het hardst aan hangt. Met nul is er geen buffer en is elke
    niet-gedekte vraag onmiddellijk een tekort - dat is een geldig antwoord, maar het moet
    een keuze zijn en geen stilte.
    """

    drawdown_available_m: float = Field(
        ...,
        ge=0,
        description=(
            "Hoe diep het peil onder het streefpeil mag zakken [m] voordat er schade "
            "optreedt. Dit is de bruikbare berging in de sloten, en gebiedsspecifiek: er "
            "is bewust geen standaardwaarde. Dynamisch peilbeheer werkt in de praktijk met "
            "0,10 tot 0,35 m; 0,35 m bleek in een proef te groot om uit te voeren."
        ),
    )


class SupplyInputGivenH(DeficitInput, SupplyWaterSystemInput):
    """Invoer voor de inverse vraag: hoeveel inlaatcapaciteit is er nodig?

    Aanvoeren = supply.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_l_s_ha": 1.25,
                "deficit_mm_per_day": 4,
                "drawdown_available_m": 0.3,
            }
        }
    )


class SupplyInputGivenSupply(DeficitInput, SupplyWaterSystemInput):
    """Invoer voor de voorwaartse vraag: wat doet deze inlaatcapaciteit?

    Aanvoeren = supply.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "area_ha": 4000,
                "discharge_capacity_l_s_ha": 1.25,
                "deficit_mm_per_day": 4,
                "drawdown_available_m": 0.3,
                "supply_capacity_l_s_ha": 0.4,
            }
        }
    )

    supply_capacity_m3_per_sec: float | None = Field(
        None,
        ge=0,
        description=(
            "Inlaatcapaciteit [m3/s]. Gangbaar is de aanvoernorm van 0,3 tot 0,4 l/s/ha, "
            "oftewel 0,03 tot 0,04 m3/s per 100 ha - ruim een orde kleiner dan een gemaal."
        ),
    )
    supply_capacity_m3_per_min: float | None = Field(
        None,
        ge=0,
        description=(
            "Inlaatcapaciteit [m3/min]. Gangbaar is 0,3 tot 0,4 l/s/ha, oftewel 1,8 tot "
            "2,4 m3/min per 100 ha."
        ),
    )
    supply_capacity_m3_per_day: float | None = Field(
        None,
        ge=0,
        description=(
            "Inlaatcapaciteit [m3/dag]. Gangbaar is 0,3 tot 0,4 l/s/ha, oftewel 2600 tot "
            "3500 m3/dag per 100 ha."
        ),
    )
    supply_capacity_mm_d: float | None = Field(
        None,
        ge=0,
        description=(
            "Inlaatcapaciteit [mm/dag]. Gangbaar is 0,3 tot 0,4 l/s/ha, oftewel 2,6 tot "
            "3,5 mm/dag. Handig omdat het tekort in dezelfde eenheid staat: een inlaat van "
            "3,5 mm/dag dekt een tekort van 3,5 mm/dag."
        ),
    )
    supply_capacity_l_s_ha: float | None = Field(
        None,
        ge=0,
        description=(
            "Inlaatcapaciteit [l/s/ha]. De aanvoernorm is 0,3 tot 0,4 l/s/ha; dit is de "
            "eenheid waarin die norm wordt uitgedrukt, dus meestal de makkelijkste."
        ),
    )

    @model_validator(mode="after")
    def validate_supply_capacity(self):
        """Vul de vijf inlaatvelden uit de ene die is opgegeven.

        Zelfde conversie als de gemaalcapaciteit; een inlaat is per definitie
        niet-negatief, want de andere richting is het gemaal en dat is een eigen veld.
        """
        m3_per_sec = discharge_capacity_to_m3_per_sec(
            m3_per_sec=self.supply_capacity_m3_per_sec,
            m3_per_min=self.supply_capacity_m3_per_min,
            m3_per_day=self.supply_capacity_m3_per_day,
            mm_d=self.supply_capacity_mm_d,
            l_s_ha=self.supply_capacity_l_s_ha,
            area_m2=self.area_m2,
        )
        if m3_per_sec is None:
            raise ModelRetry(
                "Geef de inlaatcapaciteit op in een van deze eenheden: "
                "supply_capacity_l_s_ha, supply_capacity_m3_per_sec, "
                "supply_capacity_m3_per_min, supply_capacity_m3_per_day of "
                "supply_capacity_mm_d."
            )
        units = discharge_capacity_in_all_units(m3_per_sec, self.area_m2)
        self.supply_capacity_m3_per_sec = units["m3_per_sec"]
        self.supply_capacity_m3_per_min = units["m3_per_min"]
        self.supply_capacity_m3_per_day = units["m3_per_day"]
        self.supply_capacity_mm_d = units["mm_d"]
        self.supply_capacity_l_s_ha = units["l_s_ha"]
        return self


class SupplyOutput(EngineerBaseModel):
    """Uitvoer van de maatregel aanvoeren.

    Bewust géén `MeasureOutput`. Die is opgebouwd rond de maximale waterstand*stijging* en
    haar haalbare bereik, en op de droogtekant bestaan die grootheden niet: er is geen
    stijging, er is een uitzakking en een volume vraag dat onvervuld blijft. Een gedeeld
    uitvoermodel zou vier velden leeg laten en drie velden een andere betekenis geven, en
    dat is precies de soort dubbelzinnigheid die WP6 heeft opgeruimd.
    """

    data: dict = Field(..., description="Ruwe uitkomsten en tussenresultaten")
    description: str = Field(
        ...,
        description=(
            "Twee uitlegbare zinnen, plus een derde met de aangenomen standaardwaarden "
            "als de beller er een heeft weggelaten"
        ),
    )

    status: SolveStatus = Field(
        ...,
        description=(
            "exact = de benodigde capaciteit is bepaald; no_measure_needed = de eigen "
            "berging dekt het tekort al; action_infeasible = zelfs de maximale "
            "inlaatcapaciteit die deze tool onderzoekt dekt het niet"
        ),
    )
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description=(
            "Standaardwaarden waarmee gerekend is omdat ze niet zijn opgegeven. Leeg als "
            "de beller alles heeft ingevuld"
        ),
    )
    sensitivity: list[Sensitivity] = Field(
        default_factory=list,
        description=(
            "Per aangenomen veld het antwoord aan de uiteinden van zijn plausibele bereik"
        ),
    )
    caveats: list[ModelCaveat] = Field(
        default_factory=list,
        description=(
            "Structurele beperkingen die op dit antwoord van toepassing zijn. Voor "
            "aanvoeren is de belangrijkste dat dit een antwoord over CAPACITEIT is en dat "
            "de beschikbaarheid van het water buiten dit model valt"
        ),
    )

    state_before: PolderState = Field(
        ..., description="De toestand van de polder voor de maatregel"
    )
    state_after: PolderState = Field(
        ..., description="De toestand na de maatregel; zelfde type als state_before"
    )

    supply_capacity_m3_per_sec: float = Field(
        ..., description="De inlaatcapaciteit waar dit antwoord bij hoort [m3/s]"
    )
    demand_mm: float = Field(
        ...,
        description=(
            "Totale watervraag over de periode [mm over de polder]: het tekort per dag "
            "maal het aantal dagen"
        ),
    )
    supplied_mm: float = Field(
        ..., description="Wat de inlaat over de periode heeft geleverd [mm]"
    )
    buffer_mm: float = Field(
        ...,
        description=(
            "Wat uit de eigen berging onder streefpeil is gekomen [mm]. Dit is de "
            "drooglegging die je inzet: peilmarge maal het aandeel open water"
        ),
    )
    shortfall_mm: float = Field(
        ...,
        description=(
            "Vraag die noch de inlaat noch de berging kon dekken [mm]. Nul betekent dat "
            "het streefpeil de hele periode gehouden wordt"
        ),
    )
    drawdown_m: float = Field(
        ...,
        description=(
            "Hoe diep het peil onder het streefpeil is gezakt [m], positief gerekend. "
            "Begrensd door drawdown_available_m"
        ),
    )
    days_until_buffer_empty: float | None = Field(
        None,
        description=(
            "Na hoeveel dagen de eigen berging op is [dagen]; null als dat binnen de "
            "periode niet gebeurt. Vaak de bruikbaarste uitlezing van de drie, omdat een "
            "aantal dagen makkelijker af te wegen is dan een aantal millimeters"
        ),
    )

    @model_serializer(mode="wrap")
    def _round_output(self, handler):
        """Rond de hele uitvoer af op significante cijfers; zie SIGNIFICANT_DIGITS."""
        return round_floats(handler(self))

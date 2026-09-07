"""Het gebied als toolinvoer: oppervlak, open water, capaciteiten en de peilband.

Dit is de INTERFACE-kant van `S`. De kernvorm is `core/state.py`; de omzetting staat als
`PolderState.from_water_system_input`. De vier capaciteitsvelden en de twee
oppervlakvelden bestaan hier zodat een taalmodel in willekeurige eenheden mag praten -
de toestand heeft er precies een van elk.
"""

import warnings
from typing import Literal

from pydantic import Field, model_validator
from pydantic_ai import ModelRetry

from talk_with_the_engineer.interface.schemas.base import (
    AssumedDefaults,
    hide_null_branch,
)
from talk_with_the_engineer.interface.schemas.rainfall import RainfallInput

SECONDS_PER_DAY = 86_400
MINUTES_PER_DAY = 1_440
M2_PER_HA = 10_000
LITRES_PER_M3 = 1_000

# Tabel 39 van Waterveiligheidsperspectief IJsselmeer geeft alleen deze drie mogelijkheden.
DAYS_TO_DISCHARGE = [2, 3, 4]


def one_unit_only(quantity_nl: str, **values) -> None:
    """Weiger een aanroep die dezelfde grootheid in twee eenheden opgeeft.

    Er BESTOND een prioriteitsvolgorde - `_ha` won van `_m2`, `_m3_per_sec` van `_l_s_ha` -
    en die was voor de beller onzichtbaar. Wie 4000 ha en 99 000 000 m2 tegelijk instuurde
    kreeg het antwoord voor 4000 ha, zonder melding en zonder regel in `assumptions`: een
    plausibel, intern consistent, volledig fout antwoord zonder enig signaal. Dat is het
    gevaarlijkste faaltype dat een tool kan hebben, en het is voor een taalmodel dat tussen
    twee eenheden twijfelt en er "voor de zekerheid" twee invult niet op te merken.

    Weigeren en niet kiezen, dus. De rest van dit systeem is uitzonderlijk expliciet over
    wat het heeft aangenomen; stil de ene eenheid laten winnen staat daar haaks op.
    """
    given = {name: value for name, value in values.items() if value is not None}
    if len(given) <= 1:
        return
    listed = " en ".join(f"`{name}`={value:g}" for name, value in given.items())
    raise ModelRetry(
        f"Geef {quantity_nl} in een eenheid op; er zijn er {len(given)} ingevuld: "
        f"{listed}. Laat de andere weg - de tool rekent alle eenheden zelf uit en zet ze "
        f"in de uitvoer, dus er gaat niets verloren."
    )


def discharge_capacity_to_m3_per_sec(
    *, m3_per_sec, m3_per_min, m3_per_day, mm_d, l_s_ha, area_m2
) -> float | None:
    """Reken de ingevulde eenheid om naar m3/s; `None` als er geen is ingevuld.

    De volgorde hieronder is een leesvolgorde en geen prioriteit: `one_unit_only` heeft er
    al voor gezorgd dat er hooguit een is ingevuld. Zie die functie voor waarom een
    prioriteitsvolgorde hier de verkeerde oplossing was.
    """
    if m3_per_sec is not None:
        return m3_per_sec
    if m3_per_min is not None:
        return m3_per_min / 60
    if m3_per_day is not None:
        return m3_per_day / SECONDS_PER_DAY
    if mm_d is not None:
        return mm_d / LITRES_PER_M3 * area_m2 / SECONDS_PER_DAY
    if l_s_ha is not None:
        return l_s_ha / LITRES_PER_M3 * (area_m2 / M2_PER_HA)
    return None


def discharge_capacity_in_all_units(m3_per_sec: float, area_m2: float) -> dict:
    """Vul alle vijf de eenheden uit de canonieke m3/s."""
    return {
        "m3_per_sec": m3_per_sec,
        "m3_per_min": m3_per_sec * 60,
        "m3_per_day": m3_per_sec * SECONDS_PER_DAY,
        "mm_d": m3_per_sec * SECONDS_PER_DAY / area_m2 * LITRES_PER_M3,
        "l_s_ha": m3_per_sec * LITRES_PER_M3 * M2_PER_HA / area_m2,
    }


class AreaInput(AssumedDefaults):
    """Het gebied zelf: hoe groot het is en hoeveel ervan open water is.

    De natte tools erven `WaterSystemInput`, die het gemaal erbij zet en verplicht stelt.
    De aanvoertools erven deze klasse: in een neerslagtekort is er niets weg te pompen, want
    de waterbalans klemt aan de bovenkant op streefpeil en die afkap IS het gemaal dat stopt.
    """

    # Een eigen klasse en geen vlag, omdat een veld dat verplicht is, wordt geaccepteerd en
    # niets doet precies de faalmodus is die `one_unit_only` en
    # `refuse_the_two_field_level_band` elders bestrijden.

    area_m2: float | None = Field(
        None,
        gt=0,
        description="Oppervlak van het gebied [m2]. Een polder ligt doorgaans tussen 1e6 en 1e8 m2",
    )
    area_ha: float | None = Field(
        None,
        gt=0,
        description="Oppervlak van het gebied in hectare [ha]. Een polder ligt doorgaans tussen 100 en 10000 ha",
    )

    percentage_open_water: float | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        gt=0,
        le=100,
        description=(
            "Percentage open water in het gebied, doorgaans tussen 0 en 10. Moet groter "
            "dan 0 zijn: zonder open water is er geen berging. Van alle invoervelden stuurt "
            "dit de uitkomst het sterkst, dus geef het op zodra je het kent - en schat "
            "het niet: laat het weg, dan rekent de tool met 2 % en meldt dat in "
            "`assumptions`"
        ),
    )

    @model_validator(mode="after")
    def fill_water_system_defaults(self):
        """Draait voor `warn_on_unusual_percentage_open_water`: validators in dezelfde
        klasse gaan in bronvolgorde."""
        self._apply_fallbacks("percentage_open_water")
        return self

    @model_validator(mode="after")
    def warn_on_unusual_percentage_open_water(self):
        # De grenzen zitten in het veld zelf en dus in het schema; dit is alleen nog een
        # signaal bij een ongebruikelijke maar geldige waarde.
        if self.percentage_open_water is not None and self.percentage_open_water > 10:
            warnings.warn(
                "percentage_open_water is often be between 0 and 10, consider checking your input"
            )
        return self

    @model_validator(mode="after")
    def validate_area(self):
        one_unit_only(
            "het oppervlak van het gebied",
            area_ha=self.area_ha,
            area_m2=self.area_m2,
        )
        if self.area_ha is not None:
            self.area_m2 = self.area_ha * 10000
        elif self.area_m2 is not None:
            self.area_ha = self.area_m2 / 10000
        else:
            raise ModelRetry(
                "Geef het oppervlak van het gebied op in een van deze eenheden: area_ha "
                "of area_m2. Een polder ligt doorgaans tussen 100 en 10000 ha."
            )
        return self


class WaterSystemInput(AreaInput):
    """Het gebied plus het gemaal dat het leegmaalt.

    Wat de natte tools nodig hebben. De capaciteit is verplicht en heeft geen
    standaardwaarde: zonder gemaal is er geen afvoer en is elke bui een inundatie.
    """

    discharge_capacity_m3_per_sec: float | None = Field(
        None,
        ge=0,
        description=(
            "Gemaalcapaciteit [m3/s]. Gangbaar is 1 tot 5 l/s/ha, oftewel 0,1 tot 0,5 "
            "m3/s per 100 ha."
        ),
    )
    discharge_capacity_m3_per_min: float | None = Field(
        None,
        ge=0,
        description=(
            "Gemaalcapaciteit [m3/min]. Gangbaar is 1 tot 5 l/s/ha, oftewel 6 tot 30 "
            "m3/min per 100 ha."
        ),
    )
    discharge_capacity_m3_per_day: float | None = Field(
        None,
        ge=0,
        description=(
            "Gemaalcapaciteit [m3/dag]. Gangbaar is 1 tot 5 l/s/ha, oftewel 8600 tot "
            "43000 m3/dag per 100 ha."
        ),
    )
    discharge_capacity_mm_d: float | None = Field(
        None,
        ge=0,
        description=(
            "Gemaalcapaciteit [mm/dag]. Gangbaar is 1 tot 5 l/s/ha, oftewel 8,6 tot 43 "
            "mm/dag. Let op: in mm/dag is het getal ruim acht keer zo groot als in "
            "l/s/ha; 1 l/s/ha is 8,64 mm/dag."
        ),
    )
    discharge_capacity_l_s_ha: float | None = Field(
        None,
        ge=0,
        description=(
            "Gemaalcapaciteit [l/s/ha]. Gangbaar is 1 tot 5 l/s/ha; 1,5 l/s/ha is de "
            "klassieke Nederlandse maalcapaciteit. Dit is de eenheid waarin de "
            "bandbreedtes hierboven zijn uitgedrukt, dus meestal de makkelijkste."
        ),
    )

    days_to_discharge: Literal[*DAYS_TO_DISCHARGE] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Aantal dagen waarover de dagneerslag in DIT gebied tot regionale afvoer komt "
            "(neerslag-afvoerrelatie, Tabel 39 van Waterveiligheidsperspectief IJsselmeer). "
            "Een eigenschap van bodem en drainage en niet van de bui: minder dagen "
            "concentreert de afvoer en geeft dus een hogere piek. Weet je dit niet, laat "
            "het veld dan weg in plaats van het te schatten; de tool rekent met 3 dagen "
            "en meldt dat in `assumptions`"
        ),
    )

    @model_validator(mode="after")
    def fill_the_discharge_relation(self):
        """De afvoerkarakteristiek staat op DEZE klasse en niet op `AreaInput`.

        `AreaInput` is wat de aanvoertools erven, en daar doet de neerslag-afvoerrelatie
        niets: een tekort is geen negatieve afvoer maar een vraag, en die komt onvertraagd
        uit het oppervlaktewater. Een veld dat wordt geaccepteerd en genegeerd is erger dan
        geen veld, dus hij hoort bij de klasse die een gemaal heeft.
        """
        self._apply_fallbacks("days_to_discharge")
        return self

    @model_validator(mode="after")
    def validate_discharge_capacity(self):
        """Vul de vijf capaciteitsvelden uit de ene die is opgegeven.

        Draait na `validate_area`, want mm/dag en l/s/ha kunnen pas worden omgerekend als
        het oppervlak bekend is.
        """
        one_unit_only(
            "de gemaalcapaciteit",
            discharge_capacity_m3_per_sec=self.discharge_capacity_m3_per_sec,
            discharge_capacity_m3_per_min=self.discharge_capacity_m3_per_min,
            discharge_capacity_m3_per_day=self.discharge_capacity_m3_per_day,
            discharge_capacity_mm_d=self.discharge_capacity_mm_d,
            discharge_capacity_l_s_ha=self.discharge_capacity_l_s_ha,
        )
        m3_per_sec = discharge_capacity_to_m3_per_sec(
            m3_per_sec=self.discharge_capacity_m3_per_sec,
            m3_per_min=self.discharge_capacity_m3_per_min,
            m3_per_day=self.discharge_capacity_m3_per_day,
            mm_d=self.discharge_capacity_mm_d,
            l_s_ha=self.discharge_capacity_l_s_ha,
            area_m2=self.area_m2,
        )
        if m3_per_sec is None:
            # Deze tak was eerder onbereikbaar - het if/elif op mm_d dekte None en
            # niet-None allebei af - waardoor "helemaal geen capaciteit opgegeven" een
            # kale TypeError opleverde in plaats van uitleg.
            raise ModelRetry(
                "Geef de gemaalcapaciteit op in een van deze eenheden: "
                "discharge_capacity_l_s_ha, discharge_capacity_m3_per_sec, "
                "discharge_capacity_m3_per_min, discharge_capacity_m3_per_day of "
                "discharge_capacity_mm_d."
            )

        units = discharge_capacity_in_all_units(m3_per_sec, self.area_m2)
        self.discharge_capacity_m3_per_sec = units["m3_per_sec"]
        self.discharge_capacity_m3_per_min = units["m3_per_min"]
        self.discharge_capacity_m3_per_day = units["m3_per_day"]
        self.discharge_capacity_mm_d = units["mm_d"]
        self.discharge_capacity_l_s_ha = units["l_s_ha"]
        return self


class LevelBandInput(WaterSystemInput):
    """Het watersysteem plus de peilband waarin het gebied staat.

    Twee velden en geen een, want ze zijn niet hetzelfde ding: peilopzet is een staande
    peilkeuze en peilmarge is een bedrijfsvoeringsafspraak. Samen spannen ze de band
    `[-level_margin_m, +target_level_rise_m]` rond het oorspronkelijke peil.

    Bewust NIET op `WaterSystemInput` zelf. De aanvoertools erven daarvan en beschrijven
    diezelfde band met een enkel veld - `drawdown_available_m`, de hele diepte onder het
    streefpeil - en zouden de twee velden dus accepteren zonder ze te kunnen gebruiken. Zie
    `SupplyWaterSystemInput.refuse_the_two_field_level_band`.
    """

    # CONTEXT en geen maatregel: de staande instelling van het gebied, niet iets waar de
    # pakketzoeker over zoekt. Zonder deze twee velden stond de band via elke tool altijd
    # op [0, 0] en kon een beller niet zeggen dat zijn polder al opgezet is.
    target_level_rise_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilopzet: hoeveel het streefpeil al is verhoogd ten opzichte van het "
            "oorspronkelijke peil [m]. Nul is een polder op zijn oorspronkelijke peil. "
            "Dit is de staande instelling en niet een maatregel die je vraagt door te "
            "rekenen; het verkleint de marge tot inundatie en vergroot de zomervoorraad"
        ),
    )
    level_margin_m: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Peilmarge: hoe diep onder het streefpeil het gemaal mag doormalen [m], de "
            "afspraak die voorbemaling mogelijk maakt. Nul is het klassieke gedrag, "
            "waarbij het gemaal op streefpeil stopt"
        ),
    )


class BaseInput(RainfallInput, LevelBandInput):
    """
    Base input model for rules of thumb tools.
    Requires return periods to be specified.
    """

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from LevelBandInput

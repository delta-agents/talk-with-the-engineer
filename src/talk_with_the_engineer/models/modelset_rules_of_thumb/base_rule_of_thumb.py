import warnings
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.base import EngineerBaseModel

# as defined in talk_with_the_engineer/models/modelset_rules_of_thumb/utils_rainfall_stats.py
# Alle gegeven zijn overgenomen uit tabel 6 en 7 in deelrapport 3 (regionale statistiek voor extreme neerslag) van STOWA-2019

RETURN_PERIODS = [
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    20.0,
    25.0,
    50.0,
    100.0,
    200.0,
    250.0,
    500.0,
    1000.0,
]

LENGTH_EVENT_HRS = [
    48.0,
    96.0,
    192.0,
]

TIME_OF_YEAR = [
    "winter",
    "summer",
]

RAINFALL_REGIMES = ["LL", "L", "R", "H"]

NAME_RAINFALL_PATTERN = ["p_0", "p1a", "p1b", "p1c", "p1d", "p2a", "p2b"]

# Tabel 39 van HKV PR4991.10 geeft alleen deze drie mogelijkheden.
DAYS_TO_DISCHARGE = [2, 3, 4]


# --- Standaardwaarden: van het schema naar de tool ----------------------------------
#
# De velden hieronder hebben in het schema geen `default` meer. De waarde staat in
# FIELD_FALLBACKS en wordt door `_apply_fallbacks` ingevuld zodra het veld `None` is.
#
# Dat is niet cosmetisch. Een tool die zijn aannames wil melden moet weten welke velden de
# beller heeft weggelaten, en dat is niet af te leiden uit `model_fields_set`: een
# MCP-client mag de standaardwaarden uit het schema in de aanroep invullen voordat hij hem
# verstuurt, en dan is server-side elk veld "opgegeven". Gemeten bij Claude Code: dezelfde
# kale payload gaf via een gewone `fastmcp.Client` zes aannames en via die client nul, bij
# identieke getallen.
#
# Staat er geen `default` in het schema, dan heeft die client niets om in te vullen en komt
# het veld aan zoals de beller het liet: als `None`. Een expliciete `null` werkt ook, maar
# daar valt niet op te bouwen - een client die zijn payload zelf tegen het schema
# valideert wijst hem af, want de null-tak wordt niet geadverteerd; zie `hide_null_branch`.
#
# De prijs is dat de fallbackwaarde niet meer uit het schema te lezen is. Die staat daarom
# in de veldbeschrijving en, voor clients die de beschrijvingen weghalen, in
# `SHARED_FOOTER`.

FIELD_FALLBACKS = {
    "time_of_year": "summer",
    "length_event_hrs": 96.0,
    "rainfall_regime": "R",
    "name_rainfall_pattern": "p1c",
    "days_to_discharge": 3,
    "percentage_open_water": 2.0,
    "days_to_retain_discharge": 2,
}


def hide_null_branch(schema: dict) -> None:
    """Laat het veld in het schema zien wat het echt aankan, zonder de null-tak.

    Pydantic maakt van `Literal[...] | None` een `anyOf` met een null-tak, en dan zakt de
    `enum` een niveau naar beneden - precies de informatie die een client nodig heeft om
    een geldige waarde te kiezen. Die null-tak is hier geen keuze maar het mechanisme van
    weglaten: null en niets betekenen hetzelfde, en dat hoeft een beller niet te weten.

    `default` gaat er ook uit. Een geadverteerde standaardwaarde is precies wat een client
    in de aanroep invult, en dan is niet meer te zien wat de beller heeft weggelaten.
    """
    branches = schema.pop("anyOf", None)
    if branches:
        real = next(b for b in branches if b.get("type") != "null")
        schema.update(real)
    schema.pop("default", None)


class AssumedDefaults(EngineerBaseModel):
    """Houdt bij welke velden met een fallback zijn ingevuld.

    Een privéveld en geen gewoon veld: het hoort in de uitvoer thuis (`assumptions`), niet
    in het invoerschema, waar het een beller alleen maar zou verleiden het zelf te vullen.
    """

    _assumed_fields: set[str] = PrivateAttr(default_factory=set)

    def _apply_fallbacks(self, *names: str) -> None:
        """Vul de weggelaten velden en onthoud welke dat waren."""
        for name in names:
            if getattr(self, name) is None:
                setattr(self, name, FIELD_FALLBACKS[name])
                self._assumed_fields.add(name)

    @property
    def assumed_fields(self) -> set[str]:
        """De velden waarvoor deze aanroep op een fallback leunt."""
        return set(self._assumed_fields)


class RainfallInput(AssumedDefaults):
    """De bui: het exogene deel van de invoer.

    De toegestane waarden staan als `Literal` in het type en dus als `enum` in het
    JSON-schema, met de constantenlijsten hierboven als enige bron. Eerder stonden ze
    alleen als tekst in de veldbeschrijvingen en werden ze door validators afgedwongen;
    een MCP-client kon ze daardoor niet valideren en een model dat op het schema gestuurd
    wordt kon nog steeds een ongeldige waarde genereren.
    """

    return_period: Literal[*RETURN_PERIODS] = Field(
        ...,
        description=(
            "Terugkeertijd van de bui in jaren. 0.5 betekent gemiddeld twee keer per jaar."
        ),
    )
    time_of_year: Literal[*TIME_OF_YEAR] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Halfjaar waarvoor de neerslagstatistiek geldt. Let op: 'summer' gebruikt de "
            "jaarrondstatistiek als benadering van de zomer. Weglaten mag: de tool rekent "
            "dan met 'summer' en meldt dat in `assumptions`"
        ),
    )
    length_event_hrs: Literal[*LENGTH_EVENT_HRS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Duur van de bui in uren. Weglaten mag: de tool rekent dan met 96 uur en "
            "meldt dat in `assumptions`"
        ),
    )
    rainfall_regime: Literal[*RAINFALL_REGIMES] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Neerslagregime van het gebied: LL en L voor weinig regionale spreiding, "
            "R als referentie, H voor veel spreiding. Weglaten mag: de tool rekent dan "
            "met 'R' en meldt dat in `assumptions`"
        ),
    )
    name_rainfall_pattern: Literal[*NAME_RAINFALL_PATTERN] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Naam van het neerslagpatroon binnen de bui. Weglaten mag: de tool rekent "
            "dan met 'p1c' en meldt dat in `assumptions`"
        ),
    )
    days_to_discharge: Literal[*DAYS_TO_DISCHARGE] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Aantal dagen waarover de dagneerslag tot regionale afvoer komt "
            "(neerslag-afvoerrelatie, Tabel 39 van HKV PR4991.10). Weglaten mag: de tool "
            "rekent dan met 3 dagen en meldt dat in `assumptions`"
        ),
    )

    @model_validator(mode="after")
    def fill_rainfall_defaults(self):
        self._apply_fallbacks(
            "time_of_year",
            "length_event_hrs",
            "rainfall_regime",
            "name_rainfall_pattern",
            "days_to_discharge",
        )
        return self


SECONDS_PER_DAY = 86_400
MINUTES_PER_DAY = 1_440
M2_PER_HA = 10_000
LITRES_PER_M3 = 1_000


def discharge_capacity_to_m3_per_sec(
    *, m3_per_sec, m3_per_min, m3_per_day, mm_d, l_s_ha, area_m2
) -> float | None:
    """Reken de eerst ingevulde eenheid om naar m3/s; `None` als er geen is ingevuld.

    De volgorde is vast en niet betekenisvol: meer dan een eenheid invullen is een
    invoerfout, en dan is een voorspelbare keuze beter dan een willekeurige.
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


class WaterSystemInput(AssumedDefaults):
    """
    Input model containing all the parameters for water systems.
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
            "dan 0 zijn: zonder open water is er geen berging. Weglaten mag: de tool "
            "rekent dan met 2 % en meldt dat in `assumptions`. Van alle invoervelden "
            "stuurt dit de uitkomst het sterkst, dus geef het op zodra je het kent"
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
        if self.area_ha is not None:
            self.area_m2 = self.area_ha * 10000
        elif self.area_m2 is not None:
            self.area_ha = self.area_m2 / 10000
        else:
            raise ModelRetry("One of area_m2 or area_ha must be provided.")
        return self

    @model_validator(mode="after")
    def validate_discharge_capacity(self):
        """Vul de vijf capaciteitsvelden uit de ene die is opgegeven.

        Draait na `validate_area`, want mm/dag en l/s/ha kunnen pas worden omgerekend als
        het oppervlak bekend is.
        """
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


class BaseInput(RainfallInput, WaterSystemInput):
    """
    Base input model for rules of thumb tools.
    Requires return periods to be specified.
    """

    # Everything for rainfall is inherited from RainfallInput
    # Everything for water systems is inherited from WaterSystemInput


# --- Aannames: welke standaardwaarden heeft de beller niet zelf ingevuld? -------------
#
# Elk veld met een fallback rekent stilzwijgend door als de beller het weglaat. Bij
# "reken eens uit wat een polder van 4000 ha nodig heeft" levert dat een zomerbui op een
# polder met 2 % open water op, en aan het antwoord is niet te zien dat die twee zijn
# aangenomen - terwijl de uitkomst er met 12,71 tegen 111,2 ha open water hard aan hangt.
# De fallbackwaarden staan in de veldbeschrijvingen en in `SHARED_FOOTER`, maar dat helpt
# alleen vooraf, en niet meer nadat het antwoord er eenmaal is.
#
# Daarom melden de tools hun aannames terug in de uitvoer. De lijst hieronder is bewust
# een allowlist en geen scan over alle velden met een default: zo is per veld een keuze
# gemaakt of het de uitkomst genoeg stuurt om te melden, en dwingt een nieuw veld met een
# standaardwaarde die keuze opnieuw af.
#
# De notities zeggen alleen wat deze rekenkern aantoonbaar doet, en zijn nagerekend op de
# tools zelf; `test_uitlegbaarheid.py` houdt de genoemde getallen en richtingen vast. Ze
# doen bewust geen uitspraak over wat in de praktijk maatgevend is, en verwijzen niet naar
# bronnen die de lezer niet heeft - een agent kan niets met "zie Tabel 39". De herkomst
# van een veld staat in de veldbeschrijving hierboven, waar een mens hem zoekt.

ASSUMPTION_NOTES = {
    "time_of_year": (
        "'summer' geeft bij elke terugkeertijd in deze statistiek een lagere neerslagsom "
        "dan 'winter'; bij T=100 is dat 87 tegen 100 mm. De standaardwaarde is dus de "
        "milde kant van de twee"
    ),
    "percentage_open_water": (
        "de waterstandstijging is hier vrijwel omgekeerd evenredig mee: halveer het "
        "percentage en de stijging verdubbelt. Van alle invoervelden stuurt dit de "
        "uitkomst het sterkst"
    ),
    "length_event_hrs": (
        "een langere bui brengt meer neerslag; bij T=100 in de winter geven 48, 96 en "
        "192 uur achtereenvolgens 77, 100 en 129 mm"
    ),
    "rainfall_regime": (
        "'R' is het referentieregime; LL geeft de laagste en H de hoogste neerslagsom, "
        "bij T=100 in de winter 82 tegen 108 mm"
    ),
    "name_rainfall_pattern": (
        "de neerslagsom verandert hier niet van, alleen de verdeling over de dagen "
        "binnen de bui, en daarmee de hoogte van de piek"
    ),
    "days_to_discharge": (
        "over hoeveel dagen de dagneerslag tot afvoer komt; minder dagen concentreert de "
        "afvoer en geeft een hogere waterstandstijging"
    ),
    "days_to_retain_discharge": (
        "hoeveel dagen de afvoer wordt vertraagd; meer dagen maakt vasthouden "
        "effectiever en verschuift het optimum naar een groter areaal"
    ),
}


class Assumption(BaseModel):
    """Een standaardwaarde waar de beller niets over heeft gezegd.

    Bewust geen `EngineerBaseModel`: dat voegt een `language`-veld toe, en dat hoort bij
    een toolaanroep en niet bij een losse aanname.
    """

    model_config = ConfigDict(frozen=True)

    field: str = Field(..., description="Naam van het invoerveld")
    value: str = Field(..., description="De waarde waarmee gerekend is")
    why_it_matters: str = Field(
        ..., description="Waarom deze keuze de uitkomst beinvloedt"
    )


def assumed_defaults(input) -> list[Assumption]:
    """De standaardwaarden waarmee gerekend is omdat de beller ze niet opgaf.

    Leeg als de beller alles heeft ingevuld, en dan kost dit niets in de uitvoer.
    """
    assumed = input.assumed_fields
    return [
        Assumption(
            field=name,
            value=str(getattr(input, name)),
            why_it_matters=note,
        )
        for name, note in ASSUMPTION_NOTES.items()
        if name in assumed
    ]

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

# Tabel 39 van Waterveiligheidsperspectief IJsselmeer geeft alleen deze drie mogelijkheden.
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
    "length_days": 30,
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


def hide_null_branch_and_bound(minimum: float):
    """`hide_null_branch`, plus een ondergrens die in het schema zichtbaar is.

    Twee dingen die allebei op `json_schema_extra` moeten en dat veld is er een. De
    ondergrens staat bewust NIET als `ge=` op het veld: een pydantic-constraint levert aan
    de MCP-grens een ruwe validatiedump op, met `[type=greater_than_equal]` en een link naar
    errors.pydantic.dev erin. Dezelfde afweging als bij `delta_area_ha`; de handhaving hoort
    in een validator met een melding in de stijl van de rest van dit systeem.
    """

    def apply(schema: dict) -> None:
        hide_null_branch(schema)
        schema["minimum"] = minimum

    return apply


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
    JSON-schema, met de constantenlijsten hierboven als enige bron. Dat is wat een MCP-client
    nodig heeft om ze te kunnen valideren: staan ze alleen als tekst in de veldbeschrijving
    en worden ze door een validator afgedwongen, dan kan een model dat op het schema wordt
    gestuurd nog steeds een ongeldige waarde genereren.
    """

    return_period: Literal[*RETURN_PERIODS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Terugkeertijd van de bui in jaren; 0.5 betekent gemiddeld twee keer per jaar. "
            "De tool zoekt de neerslagsom er dan bij in de STOWA-statistiek. Geef deze OF "
            "`rain_volume_mm` op - een van de twee is verplicht en allebei tegelijk wordt "
            "geweigerd."
        ),
    )
    rain_volume_mm: float | None = Field(
        None,
        gt=0,
        json_schema_extra=hide_null_branch,
        description=(
            "De neerslagsom van de bui [mm], als je hem zelf opgeeft in plaats van hem uit "
            "de statistiek te laten halen - een gemeten bui, een bui uit een ander rapport, "
            "of een hypothese. Dit is de BRUTO som over de hele bui: het neerslagverlies "
            "gaat er in de zomer nog vanaf. Ter ijking: de statistiek geeft voor 96 uur in "
            "de zomer 59 mm bij T10 en 87 mm bij T100. De duur, de vorm en het seizoen "
            "blijven gewoon gelden - `length_event_hrs` bepaalt over hoeveel dagen deze som "
            "wordt verdeeld en `name_rainfall_pattern` hoe. Geef deze OF `return_period` "
            "op; `rainfall_regime` vervalt hierbij, want dat is een correctie op de "
            "opgezochte som."
        ),
    )
    time_of_year: Literal[*TIME_OF_YEAR] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Halfjaar waarvoor de neerslagstatistiek geldt. Let op: 'summer' gebruikt de "
            "jaarrondstatistiek als benadering van de zomer. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 'summer' en meldt "
            "dat in `assumptions`"
        ),
    )
    length_event_hrs: Literal[*LENGTH_EVENT_HRS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Duur van de bui in uren: 48, 96 of 192, oftewel 2, 4 of 8 dagen. Vul uren in; "
            "de uitvoer meldt hem in dagen. Weet je dit niet, laat het veld dan weg in "
            "plaats van het te schatten; de tool rekent met 96 uur (4 dagen) en meldt dat "
            "in `assumptions`"
        ),
    )
    rainfall_regime: Literal[*RAINFALL_REGIMES] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Neerslagregime van het gebied: LL en L voor weinig regionale spreiding, "
            "R als referentie, H voor veel spreiding. Weet je dit niet, laat het veld dan "
            "weg in plaats van het te schatten; de tool rekent met 'R' en meldt dat in "
            "`assumptions`"
        ),
    )
    name_rainfall_pattern: Literal[*NAME_RAINFALL_PATTERN] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Naam van het neerslagpatroon binnen de bui. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 'p1c' en meldt dat "
            "in `assumptions`"
        ),
    )
    days_to_discharge: Literal[*DAYS_TO_DISCHARGE] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Aantal dagen waarover de dagneerslag tot regionale afvoer komt "
            "(neerslag-afvoerrelatie, Tabel 39 van Waterveiligheidsperspectief IJsselmeer). Weet je dit niet, laat "
            "het veld dan weg in plaats van het te schatten; de tool rekent met 3 dagen "
            "en meldt dat in `assumptions`"
        ),
    )

    @model_validator(mode="after")
    def require_one_source_for_the_rainfall_total(self):
        """De bui komt uit de statistiek of van de beller, en niet uit allebei.

        Dezelfde vorm als op de droge kant, waar `deficit_mm_per_day` en het droogtetripel
        elkaar uitsluiten: twee ingangen naast elkaar maakt onzichtbaar welke van de twee
        het antwoord stuurt.
        """
        if self.return_period is not None and self.rain_volume_mm is not None:
            raise ModelRetry(
                "De neerslagsom opgeven EN uit de statistiek halen is dubbelop: "
                f"`rain_volume_mm`={self.rain_volume_mm:g} staat naast "
                f"`return_period`={self.return_period:g}. Laat een van de twee weg, anders "
                "is niet te zien welk van beide het antwoord stuurt."
            )
        if self.return_period is None and self.rain_volume_mm is None:
            raise ModelRetry(
                "Geef de bui op: `return_period` als je hem uit de STOWA-statistiek wilt "
                "laten halen, of `rain_volume_mm` als je de neerslagsom zelf hebt. Zonder "
                "een van die twee is er geen bui om door te rekenen."
            )
        return self

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

    @model_validator(mode="after")
    def refuse_a_regime_that_cannot_apply(self):
        """`rainfall_regime` is een correctiefactor OP de opgezochte som.

        Geeft de beller de som zelf, dan is er niets meer om te corrigeren: de factor zou
        zijn gemeten of gekozen getal verschuiven met tot 9 %, en dat is precies het soort
        stille wijziging dat de rest van dit systeem weigert. Draait na
        `fill_rainfall_defaults`, zodat `assumed_fields` weet of de beller hem zelf invulde.
        """
        if self.rain_volume_mm is None:
            return self
        if "rainfall_regime" not in self._assumed_fields:
            raise ModelRetry(
                f"`rainfall_regime`={self.rainfall_regime!r} werkt niet samen met "
                "`rain_volume_mm`: het regime is een correctiefactor op de neerslagsom die "
                "de tool OPZOEKT, en die zoekt hij hier niet op. Laat het regime weg, of "
                "verwerk het zelf in de som die je opgeeft."
            )
        # niet aangenomen maar niet van toepassing: hem in `assumptions` melden zou
        # suggereren dat hij dit antwoord stuurt
        self._assumed_fields.discard("rainfall_regime")
        return self


SECONDS_PER_DAY = 86_400
MINUTES_PER_DAY = 1_440
M2_PER_HA = 10_000
LITRES_PER_M3 = 1_000


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
    "time_of_year": {
        "nl": (
            "'summer' geeft bij elke terugkeertijd in deze statistiek een lagere "
            "neerslagsom dan 'winter'; bij T=100 is dat 87 tegen 100 mm. De "
            "standaardwaarde is dus de milde kant van de twee"
        ),
        "en": (
            "'summer' gives a lower rainfall total than 'winter' at every return period "
            "in this statistic; at T=100 that is 87 against 100 mm. The default is "
            "therefore the mild end of the two"
        ),
    },
    "percentage_open_water": {
        "nl": (
            "de waterstandstijging is hier vrijwel omgekeerd evenredig mee: halveer het "
            "percentage en de stijging verdubbelt. Van alle invoervelden stuurt dit de "
            "uitkomst het sterkst"
        ),
        "en": (
            "the water level rise is very nearly inversely proportional to this: halve "
            "the percentage and the rise doubles. Of all input fields this one drives the "
            "outcome hardest"
        ),
    },
    "length_event_hrs": {
        "nl": (
            "een langere bui brengt meer neerslag; bij T=100 in de winter geven 2, 4 en 8 "
            "dagen achtereenvolgens 77, 100 en 129 mm. De buiduur telt bovendien door in "
            "het afvoerverloop: dat loopt tot de buiduur plus de afvoerduur uit "
            "`days_to_discharge`, dus een bui van 8 dagen met afvoer over 4 dagen geeft een "
            "afvoerverloop van 11 dagen"
        ),
        "en": (
            "a longer event brings more rainfall; at T=100 in winter, 2, 4 and 8 days give "
            "77, 100 and 129 mm respectively. The event length also carries into the "
            "discharge: that runs to the event length plus the discharge duration from "
            "`days_to_discharge`, so an 8-day event discharging over 4 days gives an 11-day "
            "discharge series"
        ),
    },
    "rainfall_regime": {
        "nl": (
            "'R' is het referentieregime; LL geeft de laagste en H de hoogste "
            "neerslagsom, bij T=100 in de winter 82 tegen 108 mm"
        ),
        "en": (
            "'R' is the reference regime; LL gives the lowest and H the highest rainfall "
            "total, at T=100 in winter 82 against 108 mm"
        ),
    },
    "name_rainfall_pattern": {
        "nl": (
            "de neerslagsom verandert hier niet van, alleen de verdeling over de dagen "
            "binnen de bui, en daarmee de hoogte van de piek"
        ),
        "en": (
            "this does not change the rainfall total, only how it is spread over the days "
            "within the event, and with it the height of the peak"
        ),
    },
    "days_to_discharge": {
        "nl": (
            "over hoeveel dagen de dagneerslag tot afvoer komt; minder dagen concentreert "
            "de afvoer en geeft een hogere waterstandstijging"
        ),
        "en": (
            "over how many days the daily rainfall turns into discharge; fewer days "
            "concentrates the discharge and gives a higher water level rise"
        ),
    },
    "days_to_retain_discharge": {
        "nl": (
            "hoeveel dagen de afvoer wordt vertraagd; meer dagen maakt vasthouden "
            "effectiever en verschuift het optimum naar een groter areaal"
        ),
        "en": (
            "how many days the discharge is delayed; more days makes retention more "
            "effective and shifts the optimum towards a larger area"
        ),
    },
    "length_days": {
        "nl": (
            "hoe lang het tekort aanhoudt; de benodigde aanvoercapaciteit loopt hiermee "
            "op, want de eigen berging onder streefpeil dekt een vast volume en dus een "
            "steeds kleiner deel van een langere periode"
        ),
        "en": (
            "how long the deficit lasts; the intake capacity needed rises with it, "
            "because the storage below the target level covers a fixed volume and thus an "
            "ever smaller share of a longer period"
        ),
    },
}
"""Per veld waarom de standaardwaarde de uitkomst stuurt, in beide talen.

Twee talen en niet een, en dat is niet cosmetisch. `language: "en"` vertaalde alleen
`description`; `why_it_matters` en alle `caveats` bleven Nederlands. Een Engelstalige
gebruiker kreeg dus een Engelse zin met een Nederlandse motivering eronder, of de beller
liet ze weg - en dan valt precies de relativering weg die het antwoord eerlijk houdt.

Dat botst met het ontwerpprincipe dat `read_me` zelf uitspreekt bij het ONTBREKEN van een
taalveld: een veld dat wordt geaccepteerd maar genegeerd is erger dan geen veld. Half
toepassen is een derde categorie, en waarschijnlijk de vervelendste van de drie, omdat de
gedeeltelijke vertaling suggereert dat de rest ook gedekt is.
"""


def language_of(input) -> str:
    """De taal van deze aanroep; 'nl' als het model er geen veld voor heeft."""
    return getattr(input, "language", "nl") or "nl"


def in_language(texts: dict, language: str) -> str:
    """Kies de tekst in `language`, met Nederlands als terugval."""
    return texts.get(language) or texts["nl"]


def _event_length_text(hours, language: str) -> str:
    """De buiduur in DAGEN, met de uren erachter.

    Het invoerveld heet `length_event_hrs` en de statistiek is in uren getabelleerd, dus het
    veld blijft in uren. De terugkoppeling niet: een waterbeheerder denkt in dagen, de
    neerslag-afvoerrelatie is in dagen (`days_to_discharge`), het vasthouden is in dagen
    (`days_to_retain_discharge`) en het afvoerverloop dat eruit komt is in dagen. Van die
    reeks was de buiduur de enige in uren, en dan moet de lezer bij elke vergelijking zelf
    door 24 delen.

    De uren blijven erbij staan tussen haakjes, want dat is de waarde die je moet invullen
    als je hem wilt overnemen. Terugkoppeling in dagen, invoer in uren.
    """
    hours = float(hours)
    days = hours / 24
    counted_days = f"{days:g} " + ("day" if days == 1 else "days")
    if language == "en":
        return f"{counted_days} ({hours:g} hours)"
    return f"{days:g} " + ("dag" if days == 1 else "dagen") + f" ({hours:g} uur)"


FIELD_VALUE_TEXT = {
    "length_event_hrs": _event_length_text,
}
"""Velden die anders worden TERUGGEKOPPELD dan ze worden ingevuld.

Alleen voor de weergave in `assumptions` en `sensitivity`; de invoer, het schema en de
rekenkern blijven ongemoeid. Staat een veld hier niet in, dan is `str(waarde)` de weergave -
en dat is voor alles behalve de buiduur precies goed.
"""


def field_value_text(field: str, value, language: str = "nl") -> str:
    """De waarde van een veld zoals de uitvoer hem noemt."""
    formatter = FIELD_VALUE_TEXT.get(field)
    return formatter(value, language) if formatter else str(value)


# Bewust geen `EngineerBaseModel`: dat voegt een `language`-veld toe, en dat hoort bij een
# toolaanroep en niet bij een losse aanname. Staat als comment en niet in de docstring,
# want die docstring komt in het uitvoerschema terecht.
class Assumption(BaseModel):
    """Een standaardwaarde waarmee gerekend is omdat de beller hem niet heeft opgegeven."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(..., description="Naam van het invoerveld")
    value: str = Field(..., description="De waarde waarmee gerekend is")
    why_it_matters: str = Field(
        ..., description="Waarom deze keuze de uitkomst beinvloedt"
    )


def assumed_defaults(input) -> list[Assumption]:
    """De standaardwaarden waarmee gerekend is omdat de beller ze niet opgaf.

    Leeg als de beller alles heeft ingevuld, en dan kost dit niets in de uitvoer.

    `why_it_matters` volgt de taal van de aanroep. Deed hij niet, en dan stond er onder een
    Engelse uitlegzin een Nederlandse motivering.
    """
    assumed = input.assumed_fields
    language = language_of(input)
    return [
        Assumption(
            field=name,
            value=field_value_text(name, getattr(input, name), language),
            why_it_matters=in_language(note, language),
        )
        for name, note in ASSUMPTION_NOTES.items()
        if name in assumed
    ]


# --- Onzekerheid: de spreiding, de caveats, en de precisie die daaruit volgt ----------
#
# De massabalans is exact; de maatregelen zijn vuistregels. De uitvoer gaf die twee tot nu
# toe dezelfde status - vier significante cijfers op alles - en dat is de eigenlijke fout.
# Niet de precisie zelf, maar dat hij overal gelijk is.
#
# Gemeten hoe groot dat verschil is. Bergen, doel 1,0 m, referentiepolder, T=100,
# basisantwoord 68,18 ha:
#
#   percentage_open_water 3,0 -> 4,0          48,2 - 88,2 ha, dus 59 % spreiding op EEN veld
#   regime LL -> H                             0,6 - 98,5 ha
#   alle aangenomen velden samen              64 % slaat om naar "geen maatregel nodig"
#   rangorde bergen versus afvoeren           0 van 162 combinaties draait om
#
# Het model is dus niet uniform betrouwbaar. Het is sterk over haalbaarheid en rangorde en
# zwak over maatvoering, en de uitvoer hoort dat te laten zien in plaats van te verbergen.
#
# Twee soorten onzekerheid, twee mechanismen, en ze worden bewust niet samengevoegd:
#
#   parametrisch  -> BEREKENBAAR. Meld hem als een berekend bereik: `Sensitivity`.
#   structureel   -> NIET berekenbaar. Meld hem als een benoemde lijst: `ModelCaveat`.
#
# Nooit als een gefuseerd getal. Een gefabriceerd "+/- 15 %" is erger dan een gefabriceerd
# puntgetal, want het ziet uit als kennis.

# De plausibele uiteinden per veld, voor de spreidingsberekening. Voor de Literal-velden is
# dat het domein dat het schema toch al adverteert; voor `percentage_open_water` de band die
# in de veldbeschrijving staat ("doorgaans tussen 0 en 10"). Geen verzonnen bandbreedtes:
# staat een veld hier niet in, dan wordt er geen spreiding voor gemeld.
FIELD_RANGES = {
    "time_of_year": ("summer", "winter"),
    "length_event_hrs": (48.0, 192.0),
    "rainfall_regime": ("LL", "H"),
    "days_to_discharge": (2, 4),
    "percentage_open_water": (1.0, 10.0),
    "days_to_retain_discharge": (0, 4),
    "length_days": (10, 90),
}


class Sensitivity(BaseModel):
    """Wat het antwoord wordt aan de uiteinden van het bereik van een onzeker veld.

    Dit maakt `ASSUMPTION_NOTES` van algemeen proza een uitspraak over *dit* antwoord.
    "Halveer het percentage en de stijging verdubbelt" is waar en niet bruikbaar; "48 tot
    88 ha" is bruikbaar.

    Alleen voor velden die de beller heeft weggelaten: daar is de onzekerheid van ons en
    niet van hem. Wat hij zelf heeft ingevuld weet hij.
    """

    model_config = ConfigDict(frozen=True)

    field: str = Field(..., description="Naam van het invoerveld")
    low_value: str = Field(..., description="De ene rand van het plausibele bereik")
    high_value: str = Field(..., description="De andere rand")
    low_answer: float | None = Field(
        None, description="Het antwoord bij `low_value`, in de eenheid van de tool"
    )
    high_answer: float | None = Field(None, description="Het antwoord bij `high_value`")
    low_note: str | None = Field(
        None,
        description=(
            "Staat er als het antwoord bij `low_value` van een andere soort is, "
            "bijvoorbeeld dat er dan geen maatregel nodig is of dat het doel onhaalbaar "
            "wordt. Hoort bij `low_answer`, die dan `null` is"
        ),
    )
    high_note: str | None = Field(
        None,
        description=(
            "Idem voor `high_value` en `high_answer`. Elke opmerking hoort bij zijn eigen "
            "kolom, ook wanneer ze allebei gevuld zijn: bij `no_measure_needed` en bij "
            "`action_infeasible` zijn beide antwoorden `null` en heeft elke rand zijn "
            "eigen reden"
        ),
    )


class ModelCaveat(BaseModel):
    """Een structurele beperking die op dít antwoord van toepassing is.

    Geen algemene disclaimer en geen percentage: een benoemde term met de richting waarin
    hij schuift. Conditioneel, zodat een lezer alleen ziet wat hier geldt - dezelfde vorm
    als `assumptions`, die al bewijst dat een agent dat oppikt.
    """

    model_config = ConfigDict(frozen=True)

    topic: str = Field(..., description="Waar de beperking over gaat")
    what: str = Field(..., description="Wat er niet in het model zit, of open staat")
    consequence: str = Field(
        ..., description="In welke richting en hoeveel het antwoord kan schuiven"
    )


def _caveat(language: str, topic: dict, what: dict, consequence: dict) -> "ModelCaveat":
    """Bouw de caveat in de taal van de aanroep.

    Drie tweetalige woordenboeken en geen if/else per regel: zo staat de Nederlandse en de
    Engelse formulering van dezelfde beperking naast elkaar, en is te zien wanneer er een
    uit de pas loopt.
    """
    return ModelCaveat(
        topic=in_language(topic, language),
        what=in_language(what, language),
        consequence=in_language(consequence, language),
    )


def _summer_loss_caveat(input, extra) -> "ModelCaveat | None":
    if getattr(input, "time_of_year", None) != "summer":
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "neerslagverlies van dit gebied",
            "en": "rainfall loss of this area",
        },
        {
            "nl": (
                "Er gaat 20 mm neerslagverlies van de eerste twee dagen af: wat dit "
                "oppervlak vasthoudt voordat er iets tot afvoer komt. Dat is een "
                "eigenschap van het GEBIED en niet van de bui, en het staat hier op een "
                "landelijke vuistregel en niet op een waarde voor dit gebied. Of het "
                "verlies bovendien al in de gebruikte neerslagstatistiek zit is een open "
                "vraag"
            ),
            "en": (
                "20 mm of rainfall loss is subtracted from the first two days. That is a "
                "property of the AREA and not of the event - what this surface holds back "
                "before anything reaches the water system - but it rests on a national "
                "rule of thumb here and not on a value for this area. Whether the loss is "
                "also already contained in the rainfall statistic used is an open question"
            ),
        },
        {
            "nl": (
                "Een gebied dat meer vasthoudt dan 20 mm krijgt hier dus een te zware "
                "maatregel en een gebied dat minder vasthoudt een te lichte; het verlies "
                "schaalt niet mee met de terugkeertijd. Zit het verlies al in de "
                "statistiek, dan wordt het bovendien dubbel geteld en valt de benodigde "
                "maatregel tot een derde lager uit - alle zomeruitkomsten zijn dan "
                "systematisch aan de veilige kant"
            ),
            "en": (
                "An area that holds back more than 20 mm therefore gets too heavy a "
                "measure here and one that holds back less too light a measure; the loss "
                "does not scale with the return period. If the loss is already in the "
                "statistic it is counted twice on top of that, and the measure needed "
                "comes out up to a third smaller - every summer answer is then "
                "systematically on the safe side"
            ),
        },
    )


def _event_length_caveat(input, extra) -> "ModelCaveat | None":
    length = getattr(input, "length_event_hrs", None)
    if length not in (48.0, 192.0):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "verdeling van het neerslagverlies",
            "en": "how the rainfall loss is spread",
        },
        {
            "nl": (
                "De regel die het verlies over de eerste twee dagen verdeelt is ontworpen "
                "voor een vierdaagse bui; bij 48 en 192 uur valt de piek elders"
            ),
            "en": (
                "The rule that spreads the loss over the first two days was designed for a "
                "four-day event; at 48 and 192 hours the peak falls elsewhere"
            ),
        },
        {
            "nl": (
                "Bij 192 uur dragen de eerste twee dagen samen 12 % van de bui, dus is de "
                "verdeling van het verlies daar het minst zeker"
            ),
            "en": (
                "At 192 hours the first two days together carry 12 % of the event, so the "
                "spread of the loss is least certain there"
            ),
        },
    )


def _return_period_caveat(input, extra) -> "ModelCaveat | None":
    period = getattr(input, "return_period", None)
    if period is None or period < 200:
        return None
    return _caveat(
        language_of(input),
        {"nl": "extrapolatie van de statistiek", "en": "extrapolating the statistic"},
        {
            "nl": (
                f"Een terugkeertijd van {period:g} jaar komt uit een reeks die veel korter "
                "is dan die terugkeertijd"
            ),
            "en": (
                f"A return period of {period:g} years comes from a record that is much "
                "shorter than that return period"
            ),
        },
        {
            "nl": (
                "De neerslagsom zelf heeft daar een onzekerheid die groter is dan het "
                "verschil tussen twee naburige terugkeertijden. Gebruik zo'n bui als "
                "testas en niet als voorspelling"
            ),
            "en": (
                "The rainfall total itself carries an uncertainty there that is larger "
                "than the difference between two neighbouring return periods. Use such an "
                "event as a test axis and not as a prediction"
            ),
        },
    )


def _cost_caveat(input, extra) -> "ModelCaveat | None":
    if not extra.get("has_cost"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "kostenvorm", "en": "shape of the cost"},
        {
            "nl": (
                "De kosten zijn lineair in de toename gerekend, terwijl een gemaal in "
                "werkelijkheid een trapkost is: je koopt een gemaal en niet een m3/min"
            ),
            "en": (
                "Costs are computed as linear in the increase, while a pumping station is "
                "really a step cost: you buy a station and not a m3/min"
            ),
        },
        {
            "nl": (
                "Lineair onderschat een kleine uitbreiding sterk, en het verandert de "
                "rangorde: in de vervangingslezing is er een omslagnorm waarBOVEN bergen "
                "goedkoper is dan afvoeren, en waaronder afvoeren wint. Waar die norm "
                "ligt verschilt per gebied, gemaal en bui - gemeten tussen ongeveer 40 en "
                "150 cm op uiteenlopende polders - dus lees de rangorde van dit antwoord "
                "af in plaats van er een vaste grens voor te nemen. De eenheidsprijzen "
                "hebben zelf een bandbreedte van ongeveer een factor twee bij bergen"
            ),
            "en": (
                "Linear badly understates a small extension, and it changes the ranking: "
                "under the replacement reading there is a crossover norm ABOVE which "
                "storage is cheaper than discharge, and below which discharge wins. Where "
                "that norm lies differs per area, pumping station and event - measured "
                "between roughly 40 and 150 cm across diverse polders - so read the "
                "ranking off this answer instead of assuming a fixed threshold. The unit "
                "prices themselves have a spread of roughly a factor two for storage"
            ),
        },
    )


def _supply_availability_caveat(input, extra) -> "ModelCaveat | None":
    """De dragende aanname onder een aanvoerantwoord - tenzij hij is opgegeven.

    Zolang de beller geen bronvolume meegeeft, rekent de tool met een onbeperkte bron en is
    dit de belangrijkste caveat van het hele model: op de natte kant is "de rand neemt je
    water aan" onschuldig, op de droge kant is hij dragend.

    Geef je het volume wél mee, dan zit de beschikbaarheid IN het model en is deze tekst
    onwaar. Dan blijft er een andere beperking over - waar dat volume vandaan komt - en die
    staat in `_supply_source_origin_caveat`. Dat onderscheid is de reden dat deze regel
    conditioneel is en niet altijd afgaat.
    """
    volume = extra.get("required_supply_volume_m3")
    if not volume or extra.get("source_volume_is_modelled"):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "beschikbaarheid van aanvoerwater",
            "en": "availability of water to draw in",
        },
        {
            "nl": (
                "Dit antwoord gaat over de capaciteit van de inlaat en veronderstelt dat "
                "het water bij die inlaat beschikbaar is. Dat is een eigenschap van het "
                "regionale watersysteem en niet van dit gebied, en het zit niet in dit model"
            ),
            "en": (
                "This answer is about the capacity of the intake and assumes the water is "
                "available at that intake. That is a property of the regional water system "
                "and not of this area, and it is not in this model"
            ),
        },
        {
            "nl": (
                f"Er is {volume / 1e6:.2f} miljoen m3 nodig over de opgegeven periode. In "
                "hoog Nederland - de zandgronden, boven het landelijke verdeelnetwerk - is "
                "aanvoer doorgaans niet beschikbaar en is beschikbaarheid en niet "
                "capaciteit de bindende beperking. Bij tekort rantsoeneert de "
                "verdringingsreeks landelijk"
            ),
            "en": (
                f"{volume / 1e6:.2f} million m3 is needed over the period given. In the "
                "elevated parts of the Netherlands - the sandy soils, above the national "
                "distribution network - supply is usually not available, and availability "
                "rather than capacity is the binding constraint. Under shortage the legal "
                "priority order rations nationally"
            ),
        },
    )


def _supply_source_origin_caveat(input, extra) -> "ModelCaveat | None":
    """Wat er overblijft zodra de bron wel is gemodelleerd.

    Dit is de opvolger van `_supply_availability_caveat`: de beschikbaarheid zit nu in het
    model, maar het volume is een INVOER. Hoe het tot stand komt - de landelijke
    waterverdeling, het Distributiemodel, de afvoer van de Rijn - zit er niet in.

    Tenzij het volume uit de droogtestatistiek komt. Dan is een deel van die herkomst er wel
    in gekomen - hoeveel minder de rivier levert bij een droogte van deze zeldzaamheid - en
    is deze tekst in die vorm onwaar. `_supply_source_statistic_caveat` neemt het dan over,
    met wat er dan nog openstaat en wat de statistiek zelf niet hard maakt.
    """
    if not extra.get("source_volume_is_modelled") or extra.get(
        "source_volume_from_statistic"
    ):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "herkomst van het bronvolume",
            "en": "where the source volume comes from",
        },
        {
            "nl": (
                "De beschikbaarheid van aanvoerwater zit nu IN dit antwoord, want er is een "
                "bronvolume opgegeven. Wat er niet in zit is hoe dat volume tot stand komt: "
                "de landelijke waterverdeling, het Distributiemodel, de afvoer van de rivier"
            ),
            "en": (
                "The availability of water is now IN this answer, because a source volume "
                "was given. What is not in it is how that volume comes about: the national "
                "water distribution, the Distribution Model, the discharge of the river"
            ),
        },
        {
            "nl": (
                "Dit antwoord is dus voorwaardelijk - 'als er zoveel is, dan gebeurt dit' - "
                "en geen voorspelling van hoeveel er zal zijn. Bij schaarste rantsoeneert de "
                "verdringingsreeks landelijk, en wat deze polder dan toekomt is een "
                "verdeling over meer afnemers; daarvoor is er een aparte vraag"
            ),
            "en": (
                "This answer is therefore conditional - 'if there is this much, then this "
                "happens' - and not a prediction of how much there will be. Under scarcity "
                "the legal priority order rations nationally, and what this area is then "
                "entitled to is an allocation across more consumers; there is a separate "
                "question for that"
            ),
        },
    )


def _supply_source_statistic_caveat(input, extra) -> "ModelCaveat | None":
    """Wat de afgeleide bron wel en niet hard maakt.

    Het bronvolume komt nu uit dezelfde statistiek als de droogte, en dat is winst: vraag en
    aanbod bewegen niet meer los van elkaar. Maar het verband waarop dat rust is zwak, en dat
    hoort een lezer te weten voordat hij op de derde decimaal gaat sturen.
    """
    if not extra.get("source_volume_from_statistic"):
        return None
    fraction = extra.get("source_availability_fraction")
    low, high = extra.get("source_spread_factor", (None, None))
    correlation = extra.get("source_fit_r")
    river = extra.get("source_river")
    # De aanvoertools zetten die band ook in `sensitivity`; de allocatietool heeft dat veld
    # niet. Het veld noemen waar het niet staat is erger dan het niet noemen.
    listed = extra.get("source_spread_in_sensitivity")
    where_nl = " Hij staat ook in `sensitivity`." if listed else ""
    where_en = " It is also in `sensitivity`." if listed else ""
    return _caveat(
        language_of(input),
        {
            "nl": "het bronvolume komt uit een zwak verband",
            "en": "the source volume rests on a weak relation",
        },
        {
            "nl": (
                f"Het aanbod is afgeleid uit de minimale 7-daagse {river}afvoer bij deze "
                f"droogte: {fraction * 100:.0f} % van een normaal jaar. Dat is een verband "
                f"met een correlatie van {correlation:+.2f} - een droogte in de polder en "
                "een lage rivierafvoer vallen maar deels samen"
            ),
            "en": (
                f"The supply is derived from the minimum 7-day discharge of the {river} "
                f"under this drought: {fraction * 100:.0f} % of a normal year. That relation "
                f"has a correlation of {correlation:+.2f} - a drought in the polder and a low "
                "river flow only partly coincide"
            ),
        },
        {
            "nl": (
                f"Reken daarom met een band van {low:.2f} tot {high:.2f} maal dit volume in "
                f"plaats van met het getal.{where_nl} Twee dingen schuiven "
                "hem verder: de indicator is de DIEPSTE week, dus als index op een heel "
                "groeiseizoen valt hij aan de lage kant uit, en wat van de rivier bij jouw "
                "inlaat aankomt bepaalt de landelijke verdeling en niet dit model"
            ),
            "en": (
                f"So work with a band of {low:.2f} to {high:.2f} times this volume rather "
                f"than with the number.{where_en} Two things shift it further: "
                "the indicator is the DEEPEST week, so as an index over a whole growing "
                "season it comes out on the low side, and what of the river arrives at your "
                "intake is set by the national distribution and not by this model"
            ),
        },
    )


def _demand_posts_caveat(input, extra) -> "ModelCaveat | None":
    """De vraagkant van dit model is een van vier posten, en de kleinste.

    Gaat op elke droogtevraag af, want de smalte is een eigenschap van het model en niet van
    de aanroep. Staat er een regio uit de werkopgave bij, dan wordt hij concreet: dan noemt
    hij het aandeel dat deze doorrekening beslaat.

    Dragen de afnemers zelf een post, dan zitten de vier posten IN het antwoord en is deze
    tekst onwaar; dan blijft alleen de vraag staan waar hun categorie op rust, en die staat in
    `_demand_post_category_caveat`.
    """
    if not extra.get("is_drought") or extra.get("demand_posts_used"):
        return None
    shares = extra.get("demand_share")
    if shares:
        irrigation = (shares.get("beregening") or 0.0) * 100
        management = (shares.get("peilbeheer") or 0.0) * 100
        flushing = (
            (shares.get("doorspoeling_boezem") or 0.0)
            + (shares.get("doorspoeling_polders") or 0.0)
        ) * 100
        region = extra.get("demand_post_choice", {}).get("demand_region", "deze regio")
        what_nl = (
            f"In {region} is beregening {irrigation:.0f} % van de zomerse watervraag, "
            f"peilbeheer {management:.0f} % en doorspoeling {flushing:.0f} %. Dit antwoord "
            "gaat over de beregeningsvraag plus het deel van peilbeheer dat op het open "
            "water verdampt; doorspoeling zit er niet in"
        )
        what_en = (
            f"In {region} irrigation is {irrigation:.0f} % of the summer water demand, "
            f"level management {management:.0f} % and flushing {flushing:.0f} %. This answer "
            "covers the irrigation demand plus the part of level management that evaporates "
            "from the open water; flushing is not in it"
        )
    else:
        what_nl = (
            "De vraag in dit model is een verdampingstekort dat uit het oppervlaktewater "
            "wordt gedekt, en dat is de post beregening. Landelijk is dat 9 tot 19 % van de "
            "zomerse watervraag en in West 5 tot 9 %; peilbeheer en doorspoeling zijn samen "
            "de rest en zitten hier niet in"
        )
        what_en = (
            "The demand in this model is an evaporation deficit met from the surface water, "
            "and that is the irrigation post. Nationally that is 9 to 19 % of the summer "
            "water demand and in the west 5 to 9 %; level management and flushing together "
            "are the rest and are not in this model"
        )
    return _caveat(
        language_of(input),
        {"nl": "een van vier watervraagposten", "en": "one of four water demand posts"},
        {"nl": what_nl, "en": what_en},
        {
            "nl": (
                "Een maatregel die hier helpt, helpt dus aan de kleinste post. En een getal "
                "uit dit antwoord naast een getal uit de werkopgave leggen is geen "
                "vergelijking van twee metingen van hetzelfde: die rust op de "
                "Basisprognoses 2018 en daarmee op KNMI'14, waar dit model op KNMI'23 rust. "
                "Het tekort onder KNMI'23 is tot een factor 1,42 groter"
            ),
            "en": (
                "A measure that helps here therefore helps the smallest post. And a number "
                "from this answer next to a number from the national assessment is not two "
                "measurements of the same thing: that rests on the 2018 base projections and "
                "thus on KNMI'14, where this model rests on KNMI'23. The deficit under "
                "KNMI'23 is up to a factor 1.42 larger"
            ),
        },
    )


def _demand_share_resolution_caveat(input, extra) -> "ModelCaveat | None":
    """De aandelen van een kleine regio zijn grof, en dan zegt het tweede cijfer niets."""
    if not extra.get("demand_share_is_coarse"):
        return None
    step = (extra.get("demand_share_resolution") or 0.0) * 100
    return _caveat(
        language_of(input),
        {
            "nl": "de vraagverdeling van deze regio is grof",
            "en": "the demand split of this region is coarse",
        },
        {
            "nl": (
                f"De werkopgave is op hele miljoenen m3 afgerond, en deze regio is zo klein "
                f"dat elk aandeel daardoor in stappen van {step:.0f} procentpunt ligt"
            ),
            "en": (
                f"The national assessment is rounded to whole millions of m3, and this "
                f"region is small enough that each share therefore comes in steps of "
                f"{step:.0f} percentage points"
            ),
        },
        {
            "nl": (
                "Lees de verdeling hier als een orde van grootte en niet als een "
                "verhouding. Wil je er een vraag over verdelen, neem dan de bovenliggende "
                "regio"
            ),
            "en": (
                "Read the split here as an order of magnitude and not as a ratio. To "
                "distribute a demand over it, take the parent region"
            ),
        },
    )


def _demand_post_category_caveat(input, extra) -> "ModelCaveat | None":
    """De categorie per post is een verdedigbare toewijzing en geen wettelijke tabel."""
    used = extra.get("demand_posts_used")
    if not used:
        return None
    listed = ", ".join(used)
    return _caveat(
        language_of(input),
        {
            "nl": "de categorie per vraagpost is toegewezen",
            "en": "the category per demand post is an assignment",
        },
        {
            "nl": (
                f"Deze posten dragen een categorie uit de verdringingsreeks: {listed}. De "
                "wet noemt criteria en geen posten: categorie 1 is veiligheid en "
                "onomkeerbare schade, en peilhandhaving tegen uitdrogende keringen, "
                "veenoxidatie en verzilting van veen valt daaronder"
            ),
            "en": (
                f"These posts carry a category from the legal priority order: {listed}. The "
                "law names criteria and not posts: category 1 is safety and irreversible "
                "damage, and maintaining levels against drying dikes, peat oxidation and "
                "salinisation of peat falls under it"
            ),
        },
        {
            "nl": (
                "Waar de post een gebruiker dient in plaats van onomkeerbare schade tegen "
                "te houden, ligt de categorie anders: doorspoelen voor de waterkwaliteit van "
                "glastuinbouw is 3 of 4, en beregening van kapitaalintensieve gewassen is 3. "
                "Geef dan `category` op in plaats van `demand_post`"
            ),
            "en": (
                "Where the post serves a user instead of preventing irreversible damage, the "
                "category differs: flushing for the water quality of greenhouse horticulture "
                "is 3 or 4, and irrigation of capital-intensive crops is 3. Then give "
                "`category` instead of `demand_post`"
            ),
        },
    )


def _salinisation_caveat(input, extra) -> "ModelCaveat | None":
    """Bij schaarste is de volgende stap zouter inlaten, en dat kent dit model niet."""
    if not extra.get("salinisation_is_the_next_step"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "verzilting zit er niet in", "en": "salinisation is not in the model"},
        {
            "nl": (
                "Dit model rekent in hoeveelheden water en kent geen chloride. Bij schaarste "
                "is de volgende stap in de praktijk niet minder inlaten maar ZOUTER inlaten, "
                "en dat is een andere beslissing met een andere schade"
            ),
            "en": (
                "This model works in quantities of water and knows no chloride. Under "
                "scarcity the next step in practice is not to draw in less but to draw in "
                "SALTIER water, and that is a different decision with different damage"
            ),
        },
        {
            "nl": (
                "Twee dingen volgen eruit. De inlaatcapaciteit van een verziltende polder is "
                "gedimensioneerd op doorspoeling en dus op waterkwaliteit - landelijk 32 tot "
                "46 % van de zomerse watervraag - dus een capaciteit die hier volstaat kan "
                "voor de kwaliteitsopgave te klein zijn. En verzilting van een veenpakket is "
                "onomkeerbaar, dus doorspoelen ertegen staat in categorie 1 van de "
                "verdringingsreeks en niet bij de landbouw"
            ),
            "en": (
                "Two things follow. The intake capacity of a salinising polder is sized on "
                "flushing and therefore on water quality - nationally 32 to 46 % of the "
                "summer water demand - so a capacity that suffices here may be too small for "
                "the quality task. And salinisation of a peat layer is irreversible, so "
                "flushing against it sits in category 1 of the legal priority order and not "
                "with agriculture"
            ),
        },
    )


def _storage_is_full_at_the_start_caveat(input, extra) -> "ModelCaveat | None":
    """De voorraad staat vol bij het begin, en hem vullen kost bronwater.

    Dit is de kanttekening die in de plaats komt van een tijd-as. Vullen tijdens de droogte
    haalt water uit dezelfde bron die de rest van de selectie ook aanspreekt, en of dat water
    er op dat moment nog is, is een vraag die dit model niet stelt.
    """
    if not extra.get("storage_m3"):
        return None
    days = extra.get("days_of_shortfall_covered")
    bought = (
        f" Deze voorraad dekt het tekort van {days:.1f} dagen."
        if days is not None
        else ""
    )
    bought_en = (
        f" This store covers {days:.1f} days of the shortfall."
        if days is not None
        else ""
    )
    return _caveat(
        language_of(input),
        {
            "nl": "de voorraad staat vol bij het begin",
            "en": "the store is full at the start",
        },
        {
            "nl": (
                f"De {extra['storage_m3'] / 1e6:.2f} miljoen m3 voorraad in deze selectie is "
                "vol veronderstéld op de eerste dag van de periode, alsof hij in een nattere "
                f"tijd is gevuld.{bought}"
            ),
            "en": (
                f"The {extra['storage_m3'] / 1e6:.2f} million m3 of storage in this selection "
                "is assumed FULL on the first day of the period, as if it had been filled in "
                f"a wetter time.{bought_en}"
            ),
        },
        {
            "nl": (
                "Hem tijdens de droogte vullen kost water uit dezelfde bron die de rest van "
                "de selectie aanspreekt, en dat is hier niet meegerekend - dit antwoord is "
                "daarmee te gunstig. Wanneer je moet vullen en of het water er dan nog is, "
                "zegt dit model niet: daarvoor is een verloop binnen het seizoen nodig en de "
                "statistiek geeft één getal per seizoen"
            ),
            "en": (
                "Filling it during the drought costs water from the same source the rest of "
                "the selection draws on, and that is not counted here - so this answer is too "
                "favourable. When to fill, and whether the water is still there by then, this "
                "model does not say: that needs a profile within the season and the statistic "
                "gives one number per season"
            ),
        },
    )


def _storage_place_caveat(input, extra) -> "ModelCaveat | None":
    """Waar het gedeelde water in het model terechtkomt, en waar het exact is.

    Alleen wanneer er voorraad wordt GEDEELD - een gebied dat zijn eigen voorraad opmaakt,
    deelt niets en heeft deze kanttekening niet nodig.
    """
    if not extra.get("storage_shared_m3"):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "de plaats van het gedeelde water",
            "en": "where the shared water sits",
        },
        {
            "nl": (
                f"De {extra['storage_shared_m3'] / 1e6:.2f} miljoen m3 die gebieden zonder "
                "eigen vraag inbrengen, komt bij het bronvolume van de hele selectie. Dit "
                "model weet niet welke afnemer er fysiek achter ligt"
            ),
            "en": (
                f"The {extra['storage_shared_m3'] / 1e6:.2f} million m3 contributed by areas "
                "without demand of their own is added to the source volume of the whole "
                "selection. This model does not know which consumer physically sits behind it"
            ),
        },
        {
            "nl": (
                "Dat is EXACT zolang er één boezem is waar iedereen achter hangt, en TE "
                "GUNSTIG bij parallelle takken: een berging in de ene tak helpt in het model "
                "dan ook de andere. Deel de selectie in dat geval per tak op"
            ),
            "en": (
                "That is EXACT as long as there is one main channel everyone sits behind, and "
                "TOO FAVOURABLE with parallel branches: storage in one branch then also helps "
                "the other in this model. In that case split the selection per branch"
            ),
        },
    )


def _no_groundwater_caveat(input, extra) -> "ModelCaveat | None":
    """De voorraad is het open water - zolang de bodem er niet bij is gezet.

    Zodra de beller een bodemvoorraad opgeeft is deze tekst onwaar, en neemt
    `_soil_store_caveat` het over met wat er dan nog niet in zit.
    """
    if not extra.get("is_drought") or extra.get("soil_store_is_modelled"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "alleen oppervlaktewater", "en": "surface water only"},
        {
            "nl": (
                "De voorraad in dit model is de berging onder het streefpeil in het open "
                "water. Bodemvocht, grondwater en overdracht van winter naar zomer zitten "
                "er niet in"
            ),
            "en": (
                "The store in this model is the storage below the target level in the open "
                "water. Soil moisture, groundwater and carry-over from winter to summer are "
                "not in it"
            ),
        },
        {
            "nl": (
                "Water vasthouden in de bodem - sponswerking - is daarmee niet te "
                "waarderen, terwijl dat voor gebieden met weinig open water juist de "
                "belangrijkste maatregel is. Voor die gebieden is dit antwoord een "
                "ondergrens op wat er mogelijk is"
            ),
            "en": (
                "Retaining water in the soil - the sponge effect - therefore cannot be "
                "valued, while for areas with little open water that is precisely the most "
                "important measure. For those areas this answer is a lower bound on what is "
                "possible"
            ),
        },
    )


def _soil_store_caveat(input, extra) -> "ModelCaveat | None":
    """Wat de bodemvoorraad wel en niet hard maakt.

    Neemt het over van `_no_groundwater_caveat`: de bodem zit nu IN het antwoord, en wat er
    overblijft is dat de getallen indicatief zijn en dat het plafond niet meebeweegt met de
    droogte.
    """
    if not extra.get("soil_store_is_modelled"):
        return None
    from_table = extra.get("soil_type")
    origin_nl = (
        f"De voorraad en het plafond komen uit het gebiedstype {from_table!r} en zijn "
        "afgeleid uit een bergingscoefficient, een toegestane zakking, een "
        "infiltratieweerstand en de kritieke opstijghoogte"
        if from_table
        else (
            "De voorraad en het plafond zijn opgegeven in deze aanroep en komen niet uit een "
            "gebiedstype"
        )
    )
    origin_en = (
        f"The store and the ceiling come from area type {from_table!r} and are derived from a "
        "storage coefficient, an allowed drawdown, an infiltration resistance and the "
        "critical capillary rise height"
        if from_table
        else (
            "The store and the ceiling were supplied in this call and do not come from an "
            "area type"
        )
    )
    return _caveat(
        language_of(input),
        {
            "nl": "de bodemvoorraad is indicatief en zijn plafond staat stil",
            "en": "the soil store is indicative and its ceiling is constant",
        },
        {
            "nl": (
                f"{origin_nl}. Die afleiding is niet aan veldmetingen getoetst, en hoe "
                "zelfvoorzienend gebieden werkelijk zijn wordt niet gemonitord - elk getal "
                "hierover is dus een modeluitspraak zonder veldreferentie"
            ),
            "en": (
                f"{origin_en}. That derivation has not been tested against field "
                "measurements, and how self-sufficient areas really are is not monitored - "
                "so any number about this is a model statement without a field reference"
            ),
        },
        {
            "nl": (
                "Twee dingen om mee te wegen. Het plafond geldt voor de route DOOR de bodem, "
                "dus voor infiltratie uit de sloot en capillaire opstijging; beregening die "
                "water rechtstreeks uit de watergang op het gewas brengt loopt daar niet "
                "door, en voor die vraag is dit antwoord te streng. En het plafond loopt in "
                "werkelijkheid terug naarmate het grondwater zakt - hoe dieper de stand, hoe "
                "minder er capillair naar boven komt - terwijl het hier een constante is, dus "
                "aan het eind van een lange droogte is het antwoord te gunstig. De maatregel "
                "die het plafond verhoogt, onderwaterdrainage of subirrigatie, kost zelf "
                "water; die post staat in `priceless`"
            ),
            "en": (
                "Two things to weigh. The ceiling applies to the route THROUGH the soil, so "
                "to infiltration from the ditch and capillary rise; sprinkler irrigation that "
                "takes water straight from the watercourse onto the crop does not pass "
                "through it, and for that demand this answer is too strict. And in reality "
                "the ceiling falls as the groundwater drops - the deeper the level, the less "
                "rises capillary - while here it is a constant, so at the tail of a long "
                "drought the answer is too favourable. The measure that raises the ceiling, "
                "submerged drainage or subirrigation, costs water itself; that post is in "
                "`priceless`"
            ),
        },
    )


def _coupling_law_caveat(input, extra) -> "ModelCaveat | None":
    """De koppelingswet is een open vraag en het cascade-effect hangt eraan.

    Staat apart van de andere caveats omdat hij alleen op systeemschaal bestaat: bij een
    losse polder is er geen benedenstroomse stand die iets blokkeert.
    """
    if not extra.get("coupling_law"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "koppelingswet tussen gebieden", "en": "coupling law between areas"},
        {
            "nl": (
                "De capaciteit neemt lineair af met de benedenstroomse stand. Of "
                "waterschappen een poldergemaal zo modelleren of met een uitschakelpeil, en "
                "met welke waarden, is een open vraag"
            ),
            "en": (
                "Capacity falls off linearly with the downstream level. Whether water "
                "authorities model a polder pump this way or with a cut-out level, and with "
                "which values, is an open question"
            ),
        },
        {
            "nl": (
                "De grootte van het cascade-effect hangt hieraan. De richting niet: op een "
                "gemeten ketting draait de rangorde van de maatregelen om zodra de "
                "opvoerhoogte onder ongeveer 5 m komt, en dat is de hele plausibele band "
                "voor een poldergemaal. Wat wel schuift is hoeveel het scheelt"
            ),
            "en": (
                "The size of the cascade effect hangs on this. The direction does not: on a "
                "measured chain the ranking of the measures flips as soon as the head drops "
                "below roughly 5 m, and that is the whole plausible band for a polder pump. "
                "What does move is how much it matters"
            ),
        },
    )


def _allocation_rule_caveat(input, extra) -> "ModelCaveat | None":
    """De regel binnen een categorie is een keuze, en de wet noemt een andere.

    Staat apart omdat hij alleen bij een verdelingsvraag bestaat: bij een losse aanvoervraag
    is er niets te verdelen, en dan is er ook geen regel om over te beslissen.
    """
    rule = extra.get("allocation_rule")
    if not rule:
        return None
    return _caveat(
        language_of(input),
        {"nl": "verdeling binnen een categorie", "en": "sharing within a category"},
        {
            "nl": (
                "De wettelijke verdringingsreeks (art. 3.14 Bkl) ordent de vier "
                "categorieen, en noemt binnen categorie 3 en 4 minimalisatie van de "
                "economische maatschappelijke schade als criterium. Dit model verdeelt "
                f"binnen een categorie {rule!r} - bij 'proportional' krijgt iedereen "
                "dezelfde dekkingsfractie"
            ),
            "en": (
                "The Dutch legal priority order (art. 3.14 Bkl) ranks the four categories, "
                "and within categories 3 and 4 names minimising economic and societal "
                f"damage as the criterion. This model shares within a category {rule!r} - "
                "under 'proportional' everyone gets the same coverage fraction"
            ),
        },
        {
            "nl": (
                "Dat is een proxy en niet het wettelijke criterium: zodra de schadefuncties "
                "per afnemer verschillen, wijkt gelijk verdelen daarvan af. De ORDENING "
                "tussen de categorieen is wel de wettelijke, en die is bindend - tussen "
                "categorie 3 en 4 is nadere prioritering niet mogelijk. Gebruik de verdeling "
                "binnen een schil dus als bandbreedte en niet als voorschrift"
            ),
            "en": (
                "That is a proxy and not the legal criterion: as soon as damage functions "
                "differ between consumers, equal sharing departs from it. The ORDER between "
                "the categories is the legal one and is binding - between categories 3 and 4 "
                "further prioritisation is not possible. So use the sharing within a shell "
                "as a range and not as a prescription"
            ),
        },
    )


def _allocation_source_caveat(input, extra) -> "ModelCaveat | None":
    """Waar het bronvolume vandaan komt, zit niet in dit model.

    Tenzij het uit de droogtestatistiek komt; dan neemt `_supply_source_statistic_caveat`
    het over, om dezelfde reden als bij aanvoeren.
    """
    if not extra.get("source_volume_given") or extra.get(
        "source_volume_from_statistic"
    ):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "herkomst van het bronvolume",
            "en": "where the source volume comes from",
        },
        {
            "nl": (
                "Het beschikbare volume is hier een INVOER. Hoe het tot stand komt - de "
                "landelijke waterverdeling, het Distributiemodel, de afvoer van de Rijn - "
                "zit niet in dit model"
            ),
            "en": (
                "The available volume is an INPUT here. How it comes about - the national "
                "water distribution, the Distribution Model, the discharge of the Rhine - is "
                "not in this model"
            ),
        },
        {
            "nl": (
                "Dit antwoord is dus voorwaardelijk: 'als er zoveel is, dan valt dit af'. "
                "Het is geen voorspelling van hoeveel er zal zijn. De trap in `theta_steps` "
                "is daarom bruikbaarder dan het ene getal: die laat zien vanaf welk aanbod "
                "het antwoord verandert, zonder dat er een aanbod voorspeld hoeft te worden. "
                "Lees een trede wel als een bereik - `coverage_at_low` tot "
                "`coverage_at_high` - en niet als een enkel getal"
            ),
            "en": (
                "This answer is therefore conditional: 'if there is this much, this is what "
                "falls short'. It is not a prediction of how much there will be. The "
                "staircase in `theta_steps` is more useful than the single number: it shows "
                "from which supply the answer changes, without anyone having to predict a "
                "supply. Do read a step as a range - `coverage_at_low` to `coverage_at_high` "
                "- and not as a single number"
            ),
        },
    )


def _raised_datum_caveat(input, extra) -> "ModelCaveat | None":
    """Peilopzet in een cascade telt in de stijging, maar niet in de opvoerhoogte."""
    nodes = getattr(input, "nodes", None) or []
    if not any(getattr(node, "target_level_rise_m", 0.0) for node in nodes):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "peilopzet en de koppeling tussen gebieden",
            "en": "a raised target level and the coupling between areas",
        },
        {
            "nl": (
                "De peilopzet van een gebied telt mee in de gerapporteerde stijging, want "
                "die wordt boven het oorspronkelijke peil gemeten. Wat het model NIET doet "
                "is de opvoerhoogte tussen twee gebieden aanpassen: een gebied dat 20 cm "
                "hoger staat pompt in werkelijkheid tegen 20 cm minder verval naar zijn "
                "benedenstrooms gebied, en dat verschil in nulpunt zit niet in de "
                "doorrekening"
            ),
            "en": (
                "An area's raised target level counts towards the reported rise, because "
                "that is measured above the original level. What the model does NOT do is "
                "adjust the head between two areas: an area standing 20 cm higher really "
                "pumps against 20 cm less head towards its downstream area, and that "
                "difference in datum is not in the computation"
            ),
        },
        {
            "nl": (
                "Het gemaal van een opgezet gebied wordt hier dus iets te pessimistisch "
                "gerekend zolang `head_max_m` is opgegeven. Bij een peilonafhankelijk gemaal "
                "maakt het niets uit, want dan speelt de opvoerhoogte geen rol"
            ),
            "en": (
                "The pump of a raised area is therefore computed slightly too "
                "pessimistically as long as `head_max_m` is given. For a head-independent "
                "pump it makes no difference, because then the head plays no role"
            ),
        },
    )


def _drought_statistic_caveat(input, extra) -> "ModelCaveat | None":
    """Wat een gekozen droogte uit STOWA 2025-23 wel en niet zegt.

    Gaat alleen af als de beller de statistiek heeft gebruikt; wie zijn tekort zelf opgeeft
    heeft deze twee grenzen niet, want dan is er geen karakteristiek jaar in het spel.
    """
    chosen = extra.get("drought_statistic")
    if not chosen:
        return None
    total = extra.get("cumulative_deficit_mm")
    period = chosen["drought_return_period"]
    # Twee vensters en niet een. `window_days` is het accumulatievenster van de STATISTIEK
    # en ligt vast op het groeiseizoen; `concentrated_over_days` is `length_days`, de keuze
    # van de aanroeper. Onder een naam levert dat bij `length_days: 90` de zin "uitgesmeerd
    # over 90 dagen. Dat venster is 1 april tot 1 oktober" op, die zichzelf tegenspreekt.
    window = extra.get("window_days")
    chosen_days = extra.get("concentrated_over_days", window)
    return _caveat(
        language_of(input),
        {"nl": "de gekozen droogte", "en": "the drought that was chosen"},
        {
            "nl": (
                f"Het tekort komt uit de statistiek: {total:.0f} mm bij een herhaaltijd van "
                f"{period} jaar, opgeteld over het groeiseizoen: een venster van {window} "
                f"dagen, 1 april tot 1 oktober. Hier is dat volume uitgesmeerd over "
                f"{chosen_days} dagen, en dat "
                "is een keuze van de aanroep en geen eigenschap van de bron. Het maximum "
                "wordt in de meeste jaren voor 1 oktober bereikt, dus het tekort per dag komt "
                "over het volle venster aan de milde kant uit"
            ),
            "en": (
                f"The deficit comes from the statistic: {total:.0f} mm at a return period of "
                f"{period} years, accumulated over the {window}-day growing season - 1 April "
                f"to 1 October. Here that volume is spread over {chosen_days} days, which is a "
                "choice made in the call and not a property of the source. In most years the "
                "maximum is reached before 1 October, so over the full window the deficit per "
                "day comes out at the mild end"
            ),
        },
        {
            "nl": (
                "Wil je het scherper, zet `length_days` dan korter; hetzelfde volume over "
                "minder dagen vraagt meer inlaatcapaciteit. En boven ongeveer T5 "
                "vertegenwoordigt een karakteristiek jaar niet alle droogte-indicatoren "
                "tegelijk, dus noem de herhaaltijd erbij en doe niet alsof dit hét droge "
                "jaar is"
            ),
            "en": (
                "For a sharper answer, set `length_days` shorter; the same volume over "
                "fewer days asks for more intake capacity. And above roughly T5 a single "
                "characteristic year does not represent all drought indicators at once, so "
                "name the return period and do not present this as THE dry year"
            ),
        },
    )


def _racmo_caveat(input, extra) -> "ModelCaveat | None":
    """De reeksen achter de droogtestatistiek zijn gesimuleerd en niet gemeten."""
    if not extra.get("drought_statistic"):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "herkomst van de droogtereeks",
            "en": "where the drought record comes from",
        },
        {
            "nl": (
                "De statistiek is gefit op RACMO-klimaatreeksen: gesimuleerde jaren en geen "
                "gemeten geschiedenis. Een scenario is een consistent klimaat en geen "
                "voorspelling van een specifiek jaar"
            ),
            "en": (
                "The statistic is fitted on RACMO climate runs: simulated years and not a "
                "measured history. A scenario is a consistent climate and not a prediction "
                "of any particular year"
            ),
        },
        {
            "nl": (
                "Het verschil tussen twee jaren in zo'n reeks is weersvariatie en geen "
                "klimaatverandering; dat verschil zit tussen de SCENARIO's. Vergelijk dus "
                "'Referentie' met 'Hd_2050' en niet twee jaren binnen een scenario"
            ),
            "en": (
                "The difference between two years within such a run is weather variability "
                "and not climate change; that difference sits between the SCENARIOS. So "
                "compare 'Referentie' with 'Hd_2050' rather than two years within one"
            ),
        },
    )


PLAUSIBLE_RISE_M = 1.0
"""Boven deze stijging is de lineaire berging geen goede beschrijving meer [m].

De waterbalans rekent met een VAST open-wateroppervlak: elke kuub verhoogt de stand met
dezelfde centimeters. Dat klopt zolang het water in de watergang blijft. Zodra het over de
kant komt spreidt het zich over het land, groeit het bergende oppervlak met een orde, en
stijgt de stand veel langzamer dan dit model zegt.

Een meter is de ordegrootte waarop dat gebeurt: `delta_h_available` beschrijft de
drooglegging tot het laagste te beschermen perceel en noemt 0,2 tot 1,0 m als bandbreedte.
Daarboven staat het maaiveld al onder water en is de vraag niet meer "hoe hoog komt het"
maar "hoeveel land loopt onder".
"""


def _implausible_rise_caveat(input, extra) -> "ModelCaveat | None":
    """Een stijging die het model niet meer kan dragen, benoemd in plaats van gemeld.

    De systeemtools hebben bewust geen `status`-veld - er is geen maatvoering om haalbaar of
    onhaalbaar te noemen - en `converged` zegt alleen iets over de numeriek. Zonder deze
    regel is er dus niets dat een stijging van bijna vijf meter kán markeren, en komt die er
    even stellig uit als dertien centimeter.

    Een caveat en geen vlag, want dat is in dit systeem de vorm voor "hier houdt het model
    op". Hij zegt ook welke kant het op staat: een bovengrens, want spreiding over het land
    verlaagt de werkelijke stand.
    """
    rise = extra.get("worst_rise_m")
    if rise is None or rise <= PLAUSIBLE_RISE_M:
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "de stijging valt buiten het bereik van het model",
            "en": "the rise falls outside the range of the model",
        },
        {
            "nl": (
                f"Er komt {rise * 100:.0f} cm stijging uit, en de waterbalans rekent met een "
                "vast open-wateroppervlak. Boven ongeveer een meter komt het water over de "
                "kant, spreidt het zich over het land en groeit het bergende oppervlak met "
                "een orde - dat zit hier niet in, net zomin als overstorten, inundatie van "
                "percelen of een gemaal dat afslaat"
            ),
            "en": (
                f"The computed rise is {rise * 100:.0f} cm, and the water balance uses a "
                "fixed open-water area. Above roughly one metre the water leaves the "
                "watercourse, spreads across the land and the storing area grows by an order "
                "of magnitude - that is not in this model, and neither are overflows, "
                "inundation of parcels or a pump that cuts out"
            ),
        },
        {
            "nl": (
                "Lees dit getal daarom als een BOVENGRENS en niet als een voorspelling: in "
                "werkelijkheid komt de stand lager uit doordat het land meebergt. Wat het "
                "wel zegt is dat het hier niet past - de vraag verschuift van 'hoe hoog "
                "komt het' naar 'hoeveel land loopt onder', en die beantwoordt dit model "
                "niet"
            ),
            "en": (
                "So read this number as an UPPER BOUND and not as a prediction: in reality "
                "the level comes out lower because the land stores water too. What it does "
                "tell you is that it does not fit here - the question shifts from 'how high "
                "does it get' to 'how much land floods', and this model does not answer that "
                "one"
            ),
        },
    )


def _own_storm_caveat(input, extra) -> "ModelCaveat | None":
    """De bui komt van de beller en niet uit de statistiek, en dat hoort in het antwoord.

    Een opgezochte bui draagt een herhaaltijd: je kunt zeggen hoe zeldzaam hij is en waar
    dat vandaan komt. Een opgegeven som draagt dat niet, terwijl het antwoord er verder
    identiek uitziet - zelfde velden, zelfde stelligheid. Deze regel is wat die twee uit
    elkaar houdt.
    """
    volume = getattr(input, "rain_volume_mm", None)
    if volume is None:
        return None
    return _caveat(
        language_of(input),
        {"nl": "de bui is opgegeven", "en": "the event was supplied"},
        {
            "nl": (
                f"De neerslagsom van {volume:g} mm komt uit deze aanroep en niet uit de "
                "STOWA-statistiek. Er hoort dus geen herhaaltijd bij: dit antwoord zegt "
                "wat er bij deze bui gebeurt, niet hoe zeldzaam die bui is"
            ),
            "en": (
                f"The rainfall total of {volume:g} mm comes from this call and not from "
                "the STOWA statistic. There is therefore no return period attached: this "
                "answer says what happens in this event, not how rare that event is"
            ),
        },
        {
            "nl": (
                "Noem de herkomst als je dit doorgeeft. Wil je de zeldzaamheid er wel bij, "
                "gebruik dan `return_period` in plaats van `rain_volume_mm`; ter ijking "
                "geeft de statistiek voor 96 uur in de zomer 59 mm bij T10 en 87 mm bij "
                "T100. De vorm van de bui en het neerslagverlies komen hoe dan ook uit het "
                "model en niet uit jouw getal"
            ),
            "en": (
                "Name that origin when you pass this on. If you do want the rarity, use "
                "`return_period` instead of `rain_volume_mm`; for calibration the statistic "
                "gives 59 mm at T10 and 87 mm at T100 for a 96-hour summer event. The shape "
                "of the event and the rainfall loss come from the model either way, not "
                "from your number"
            ),
        },
    )


def _own_deficit_caveat(input, extra) -> "ModelCaveat | None":
    """De droge tegenhanger: het tekort komt van de beller en niet uit de statistiek.

    Dezelfde stilte als bij een opgegeven bui, en dus dezelfde melding. Gaat niet af zodra
    er een droogte is gekozen; dan staat de herkomst al in `data.drought_statistic` en
    schrijft `_drought_statistic_caveat` op wat die keuze betekent.
    """
    if not extra.get("is_drought") or extra.get("drought_statistic"):
        return None
    deficit = getattr(input, "deficit_mm_per_day", None)
    if deficit is None:
        return None
    return _caveat(
        language_of(input),
        {"nl": "het tekort is opgegeven", "en": "the deficit was supplied"},
        {
            "nl": (
                f"Het neerslagtekort van {deficit:g} mm/dag komt uit deze aanroep en niet "
                "uit de droogtestatistiek. Er hoort dus geen herhaaltijd bij: dit antwoord "
                "zegt wat er bij deze droogte gebeurt, niet hoe zeldzaam die droogte is"
            ),
            "en": (
                f"The deficit of {deficit:g} mm/day comes from this call and not from the "
                "drought statistic. There is therefore no return period attached: this "
                "answer says what happens in this drought, not how rare that drought is"
            ),
        },
        {
            "nl": (
                "Noem de herkomst als je dit doorgeeft. Wil je de zeldzaamheid er wel bij, "
                "kies dan een droogte met `drought_region`, `drought_scenario` en "
                "`drought_return_period`; het tekort komt dan uit STOWA 2025-23 en zakt mee "
                "met het klimaatscenario"
            ),
            "en": (
                "Name that origin when you pass this on. If you do want the rarity, choose "
                "a drought with `drought_region`, `drought_scenario` and "
                "`drought_return_period`; the deficit then comes from STOWA 2025-23 and "
                "moves with the climate scenario"
            ),
        },
    )


CAVEAT_RULES = (
    _drought_statistic_caveat,
    _racmo_caveat,
    _allocation_rule_caveat,
    _allocation_source_caveat,
    _summer_loss_caveat,
    _event_length_caveat,
    _return_period_caveat,
    _cost_caveat,
    _supply_availability_caveat,
    _supply_source_origin_caveat,
    _supply_source_statistic_caveat,
    _demand_posts_caveat,
    _demand_share_resolution_caveat,
    _demand_post_category_caveat,
    _storage_is_full_at_the_start_caveat,
    _storage_place_caveat,
    _salinisation_caveat,
    _no_groundwater_caveat,
    _soil_store_caveat,
    _coupling_law_caveat,
    _raised_datum_caveat,
    _implausible_rise_caveat,
    _own_storm_caveat,
    _own_deficit_caveat,
)
"""De caveats, als lijst van regels die zelf beslissen of ze van toepassing zijn.

Een allowlist en geen scan: elke regel is een keuze dat déze beperking het antwoord genoeg
stuurt om te melden. Een nieuwe regel dwingt die keuze opnieuw af.
"""


def model_caveats(input, **extra) -> list[ModelCaveat]:
    """De structurele beperkingen die op dit antwoord van toepassing zijn."""
    found = (rule(input, extra) for rule in CAVEAT_RULES)
    return [caveat for caveat in found if caveat is not None]


# --- prijsloze posten: geen bedrag, wel een prijs -----------------------------------
#
# Peilopzet, peilmarge en aanvoeren kosten geen aanleg. Ze stonden daarom niet in `cost`,
# en er stond ook niets anders over ze in het antwoord - terwijl `read_me` belooft dat ze
# in `priceless` staan en niet op nul.
#
# Dat gemis is niet cosmetisch. Een peilmarge van 30 cm verlaagt op de referentiepolder de
# benodigde berging van 68 naar 38 ha en de kosten van 9,2 naar 5,1 miljoen euro. Een
# maatregel die de kosten zichtbaar verlaagt en niets zichtbaars verhoogt, leest als
# gratis winst; wat hij werkelijk kost is marge tot inundatie en bedrijfsvoering, en dat
# staat nergens in een getal omdat het geen getal IS.
#
# Dus geen bedrag maar een benoeming. Zelfde vorm als `CAVEAT_RULES`: een allowlist van
# regels die zelf beslissen of ze van toepassing zijn, zodat een beller alleen ziet wat
# hier geldt.


def _is_drought_input(input) -> bool:
    """Een droogte-invoer herken je aan `drawdown_available_m`.

    Die is daar de HELE peilband die je inzet, en de aanvoertools zetten hem dan ook als
    `level_margin_m` op de toestand. Een apart veld voor peilopzet kennen ze niet - een post
    daarover zou een prijs melden naast de post die diezelfde centimeters al noemt.
    """
    return getattr(input, "drawdown_available_m", None) is not None


def _target_level_rise_post(input, measure_nl):
    if _is_drought_input(input):
        return None
    rise = getattr(input, "target_level_rise_m", 0.0) or 0.0
    if not rise:
        return None
    return dict(
        topic="peilopzet",
        magnitude=f"{rise * 100:.0f} cm",
        what_it_costs="Drooglegging: een hoger streefpeil betekent landbouwschade en functiebeperking, "
        "en dat is een verdringingsvraagstuk en geen investeringspost. In dit antwoord "
        "betaal je hem bovendien al in de waterstand - de opzet telt mee in de gerapporteerde "
        "stijging, dus elke centimeter opzet is een centimeter minder marge tot inundatie.",
    )


def _level_margin_post(input, measure_nl):
    """De peilband onder het streefpeil, hoe de tool hem ook noemt.

    Op de natte kant heet hij `level_margin_m` en is hij de afspraak die voorbemaling
    mogelijk maakt; op de droge kant heet hij `drawdown_available_m` en is hij de buffer
    die je leegtrekt. Dat is dezelfde centimeter en dezelfde niet-monetaire prijs.
    """
    if _is_drought_input(input):
        margin = input.drawdown_available_m
        name = "drawdown_available_m"
    else:
        margin = getattr(input, "level_margin_m", 0.0) or 0.0
        name = "peilmarge"
    if not margin:
        return None
    if name == "peilmarge":
        # De natte lezing: het gemaal maalt vooruit, en het systeem daarachter is zelf een
        # investering. Wie de marge als gegeven opgeeft, hoort beide te zien.
        what_it_costs = (
            "Bedrijfsvoering en drooglegging: het gemaal maalt vooruit op een bui die "
            "nog niet is gevallen, en zolang het peil uitgezakt staat draagt het gebied "
            "de diepere drooglegging. Deze prijs heeft geen bedrag, maar de marge "
            "verlaagt het gemelde bedrag wel - noem deze post dus mee, anders leest de "
            "marge als gratis winst. En voorbemalen veronderstelt sturing - telemetrie, "
            "automatisering en protocollen - een investering die hier evenmin geprijsd is."
        )
    else:
        # De droge lezing van dezelfde centimeters: een buffer die je leegtrekt.
        what_it_costs = (
            "Voorraad en drooglegging: elke centimeter die je leegtrekt is zomervoorraad "
            "die op is zodra hij is gebruikt, en zolang het peil uitgezakt staat draagt "
            "het gebied de diepere drooglegging. Deze prijs heeft geen bedrag, maar hij "
            "bepaalt het antwoord wel - noem deze post mee."
        )
    return dict(
        topic="peilmarge"
        if name == "peilmarge"
        else "bruikbare diepte onder streefpeil",
        magnitude=f"{margin * 100:.0f} cm",
        what_it_costs=what_it_costs,
    )


def _supply_post(input, measure_nl):
    if measure_nl != "aanvoeren":
        return None
    return dict(
        topic="aanvoeren",
        magnitude="de inlaat",
        what_it_costs="Het water, niet het kunstwerk. Wat aanvoer in een tekort kost is een "
        "verdelingsvraag - de verdringingsreeks rantsoeneert landelijk - en de "
        "aanvoercapaciteit van een verziltende polder wordt bovendien gedimensioneerd op "
        "doorspoeling en dus op waterkwaliteit. Een bedrag verzinnen zou hier erger zijn "
        "dan geen bedrag.",
    )


def _level_water_post(input, measure_nl):
    """Peilopzet kost ook water, en in een droog jaar is dat het schaarse goed.

    Twee prijzen op dezelfde centimeters, en beide zijn waar. `_target_level_rise_post` en
    `_level_margin_post` noemen de drooglegging; deze noemt het water. Een hoger peil
    handhaven vraagt aanvoer, want het verdampt en infiltreert weg - in veenweidegebieden
    ongeveer 4 % meer watervraag voor peilbeheer. Bij ons koopt peilopzet voorraad; in de
    landelijke werkopgave is hij een vraagpost.
    """
    if _is_drought_input(input):
        depth = input.drawdown_available_m
        if not depth:
            return None
        return dict(
            topic="water voor peilhandhaving",
            magnitude=f"{depth * 100:.0f} cm",
            what_it_costs="Water. Voor zover deze diepte peilopzet is, is die opzet niet alleen berging "
            "maar ook vraag: een verhoogd peil moet worden aangevuld omdat het verdampt en "
            "infiltreert, in veenweidegebieden met ongeveer 4 % meer watervraag voor "
            "peilbeheer. Dit antwoord telt de voorraad die de opzet oplevert en niet het "
            "water dat het handhaven ervan kost, en in een droog jaar is dat precies het "
            "schaarse goed.",
        )
    rise = getattr(input, "target_level_rise_m", 0.0) or 0.0
    if not rise:
        return None
    return dict(
        topic="water voor peilhandhaving",
        magnitude=f"{rise * 100:.0f} cm",
        what_it_costs="Water. Een verhoogd streefpeil moet worden aangevuld omdat het verdampt en "
        "infiltreert, in veenweidegebieden met ongeveer 4 % meer watervraag voor peilbeheer. "
        "Dat is de zomerse tegenrekening van de winterse berging die deze opzet oplevert, en "
        "hij staat in geen van beide antwoorden in een getal.",
    )


def _soil_measure_post(input, measure_nl):
    """De maatregel die de bodemvoorraad bereikbaar maakt, kost water.

    Zonder onderwaterdrainage of subirrigatie is de weerstand tussen sloot en bodem precies
    het plafond dat het antwoord meldt. Die maatregel verhoogt het plafond en vraagt zelf 6
    tot 77 mm per jaar aan extra infiltratie, afhankelijk van het gebied. Zet dat naast de
    voorraad die hij ontsluit - in veenweide 5,8 mm - dan kan de maatregel meer water vragen
    dan de voorraad die hij vrijmaakt.
    """
    store = getattr(input, "soil_store_mm", None)
    if not store:
        return None
    return dict(
        topic="de bodemvoorraad bereikbaar maken",
        magnitude=f"{store:.1f} mm voorraad",
        what_it_costs="Water, en in veen bovendien bodem. Het plafond in dit antwoord hoort bij de "
        "weerstand die er nu is; hoger komt hij met onderwaterdrainage of subirrigatie, en "
        "die vragen 6 tot 77 mm per jaar aan extra infiltratie. Dat kan meer zijn dan de "
        "voorraad die ze ontsluiten. In een droog jaar wordt de onttrekking via peilgestuurde "
        "drainage bovendien zelf gerantsoeneerd, en grondwaterstandsdaling in veen is "
        "onomkeerbaar: dat kost maaiveld.",
    )


PRICELESS_RULES = (
    _target_level_rise_post,
    _level_margin_post,
    _level_water_post,
    _soil_measure_post,
    _supply_post,
)


def priceless_posts(input, measure_nl: str | None = None) -> list:
    """De posten in dit antwoord die geen bedrag hebben maar wel een prijs.

    Levert dicts en geen `PricelessPost`, want die woont in `results.py` en dat bestand
    importeert dit bestand al. De regels horen hier omdat ze naar INVOERvelden kijken, net
    als `CAVEAT_RULES`.
    """
    found = (rule(input, measure_nl) for rule in PRICELESS_RULES)
    return [post for post in found if post is not None]


MINIMUM_DIGITS = 2
"""Twee significante cijfers is de ondergrens in de tekst, ook bij een grote spreiding.

Op een cijfer wordt de zin een tweede, afwijkende bewering naast `measure.delta`: 12,71 ha
leest dan als "ongeveer 10 ha" en 1266 ha als "ongeveer 1000 ha", allebei ruim een vijfde
eronder. Die afronding is bovendien niet symmetrisch - zodra het eerste cijfer laag is gaat
hij structureel naar beneden - dus wie de zin citeert zonder het veld erbij te pakken zit er
systematisch onder in plaats van eromheen.

De onzekerheid staat er niet minder om: `_approximation` zet er "ongeveer" voor en
`append_spread` zet het bereik erachter. Die twee dragen de boodschap "dit is een
vuistregel"; het puntgetal hoeft hem niet nog eens te dragen door ernaast te gaan liggen.
"""


def supported_digits(spread: float, value: float) -> int | None:
    """Hoeveel significante cijfers de spreiding toestaat, of `None` bij geen informatie.

    De uitvoer houdt vier cijfers - die zijn nodig voor round-tripping en voor de
    regressietests - maar de *tekst* hoort niet meer te beweren dan er te weten valt. Boven
    3 % spreiding zijn het er twee, daaronder drie, en twee is de ondergrens; zie
    `MINIMUM_DIGITS`.

    `None` betekent "we hebben geen spreiding gemeten", en dan blijft de formattering zoals
    hij was. Dat is geen gemakzucht maar dezelfde discipline als bij de caveats: heeft de
    beller alles ingevuld, dan is er geen parametrische onzekerheid die WIJ kennen, en dan
    gaan we er ook geen cijfers aan toevoegen. Wat er dan nog aan onzekerheid over is, is
    structureel, en die staat in `caveats` en niet in een getal.
    """
    if not value or spread <= 0:
        return None
    relative = abs(spread / value)
    if relative > 0.03:
        return MINIMUM_DIGITS
    return 3

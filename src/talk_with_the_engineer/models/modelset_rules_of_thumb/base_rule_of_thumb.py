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
            "jaarrondstatistiek als benadering van de zomer. Weet je dit niet, laat het veld "
            "dan weg in plaats van het te schatten; de tool rekent met 'summer' en meldt "
            "dat in `assumptions`"
        ),
    )
    length_event_hrs: Literal[*LENGTH_EVENT_HRS] | None = Field(
        None,
        json_schema_extra=hide_null_branch,
        description=(
            "Duur van de bui in uren. Weet je dit niet, laat het veld dan weg in plaats van "
            "het te schatten; de tool rekent met 96 uur en meldt dat in `assumptions`"
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
            "(neerslag-afvoerrelatie, Tabel 39 van HKV PR4991.10). Weet je dit niet, laat "
            "het veld dan weg in plaats van het te schatten; de tool rekent met 3 dagen "
            "en meldt dat in `assumptions`"
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
            "dan 0 zijn: zonder open water is er geen berging. Van alle invoervelden stuurt "
            "dit de uitkomst het sterkst, dus geef het op zodra je het kent - en schat "
            "het niet: laat het weg, dan rekent de tool met 2 % en meldt dat in "
            "`assumptions`"
        ),
    )

    # De peilband rond het oorspronkelijke peil. Dit is CONTEXT en geen maatregel: het is de
    # staande instelling van het gebied, niet iets waar de pakketzoeker over zoekt. Zonder
    # deze twee velden stond de band via elke tool altijd op [0, 0] en kon een beller niet
    # zeggen dat zijn polder al opgezet is. Zie PLAN_DROOGTE_EIS_ALS_WATERSTAND.md Sec. 4.4.
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
    "length_days": (
        "hoe lang het tekort aanhoudt; de benodigde aanvoercapaciteit loopt hiermee op, "
        "want de eigen berging onder streefpeil dekt een vast volume en dus een steeds "
        "kleiner deel van een langere periode"
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
            "Idem voor `high_value` en `high_answer`. Bewust een opmerking per KOLOM en "
            "niet een gedeelde: er stond een enkelvoudig \"bij deze waarde\", en zodra "
            "beide kolommen `null` zijn - wat gebeurt bij `no_measure_needed` en bij "
            "`action_infeasible` - verwees dat naar twee waarden tegelijk"
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


def _summer_loss_caveat(input, extra) -> ModelCaveat | None:
    if getattr(input, "time_of_year", None) != "summer":
        return None
    return ModelCaveat(
        topic="zomers neerslagverlies",
        what=(
            "Er gaat 20 mm neerslagverlies van de eerste twee dagen af. Of dat verlies al "
            "in de gebruikte statistiek zit is een open vraag"
        ),
        consequence=(
            "Zit het er al in, dan wordt het dubbel geteld en valt de benodigde maatregel "
            "tot een derde lager uit. Alle zomeruitkomsten zijn in dat geval systematisch "
            "aan de veilige kant"
        ),
    )


def _event_length_caveat(input, extra) -> ModelCaveat | None:
    length = getattr(input, "length_event_hrs", None)
    if length not in (48.0, 192.0):
        return None
    return ModelCaveat(
        topic="verdeling van het neerslagverlies",
        what=(
            "De regel die het verlies over de eerste twee dagen verdeelt is ontworpen voor "
            "een vierdaagse bui; bij 48 en 192 uur valt de piek elders"
        ),
        consequence=(
            "Bij 192 uur dragen de eerste twee dagen samen 12 % van de bui, dus is de "
            "verdeling van het verlies daar het minst zeker"
        ),
    )


def _return_period_caveat(input, extra) -> ModelCaveat | None:
    period = getattr(input, "return_period", None)
    if period is None or period < 200:
        return None
    return ModelCaveat(
        topic="extrapolatie van de statistiek",
        what=(
            f"Een terugkeertijd van {period:g} jaar komt uit een reeks die veel korter is "
            "dan die terugkeertijd"
        ),
        consequence=(
            "De neerslagsom zelf heeft daar een onzekerheid die groter is dan het verschil "
            "tussen twee naburige terugkeertijden. Gebruik zo'n bui als testas en niet als "
            "voorspelling"
        ),
    )


def _cost_caveat(input, extra) -> ModelCaveat | None:
    if not extra.get("has_cost"):
        return None
    return ModelCaveat(
        topic="kostenvorm",
        what=(
            "De kosten zijn lineair in de toename gerekend, terwijl een gemaal in "
            "werkelijkheid een trapkost is: je koopt een gemaal en niet een m3/min"
        ),
        consequence=(
            "Lineair onderschat een kleine uitbreiding sterk, en het verandert de rangorde: "
            "met trapkost ontstaat er een omslagpunt rond 100 cm waaronder bergen "
            "goedkoper is. De eenheidsprijzen hebben zelf een bandbreedte van ongeveer een "
            "factor twee bij bergen"
        ),
    )


def _supply_availability_caveat(input, extra) -> ModelCaveat | None:
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
    return ModelCaveat(
        topic="beschikbaarheid van aanvoerwater",
        what=(
            "Dit antwoord gaat over de capaciteit van de inlaat en veronderstelt dat het "
            "water bij die inlaat beschikbaar is. Dat is een eigenschap van het regionale "
            "watersysteem en niet van dit gebied, en het zit niet in dit model"
        ),
        consequence=(
            f"Er is {volume / 1e6:.2f} miljoen m3 nodig over de opgegeven periode. In hoog "
            "Nederland - de zandgronden, boven het landelijke verdeelnetwerk - is aanvoer "
            "doorgaans niet beschikbaar en is beschikbaarheid en niet capaciteit de "
            "bindende beperking. Bij tekort rantsoeneert de verdringingsreeks landelijk"
        ),
    )


def _supply_source_origin_caveat(input, extra) -> ModelCaveat | None:
    """Wat er overblijft zodra de bron wel is gemodelleerd.

    Dit is de opvolger van `_supply_availability_caveat`: de beschikbaarheid zit nu in het
    model, maar het volume is een INVOER. Hoe het tot stand komt - de landelijke
    waterverdeling, het Distributiemodel, de afvoer van de Rijn - zit er niet in.
    """
    if not extra.get("source_volume_is_modelled"):
        return None
    return ModelCaveat(
        topic="herkomst van het bronvolume",
        what=(
            "De beschikbaarheid van aanvoerwater zit nu IN dit antwoord, want er is een "
            "bronvolume opgegeven. Wat er niet in zit is hoe dat volume tot stand komt: de "
            "landelijke waterverdeling, het Distributiemodel, de afvoer van de rivier"
        ),
        consequence=(
            "Dit antwoord is dus voorwaardelijk - 'als er zoveel is, dan gebeurt dit' - en "
            "geen voorspelling van hoeveel er zal zijn. Bij schaarste rantsoeneert de "
            "verdringingsreeks landelijk, en wat deze polder dan toekomt is een verdeling "
            "over meer afnemers; daarvoor is er een aparte vraag"
        ),
    )


def _no_groundwater_caveat(input, extra) -> ModelCaveat | None:
    if not extra.get("is_drought"):
        return None
    return ModelCaveat(
        topic="alleen oppervlaktewater",
        what=(
            "De voorraad in dit model is de berging onder het streefpeil in het open water. "
            "Bodemvocht, grondwater en overdracht van winter naar zomer zitten er niet in"
        ),
        consequence=(
            "Water vasthouden in de bodem - sponswerking - is daarmee niet te waarderen, "
            "terwijl dat voor gebieden met weinig open water juist de belangrijkste "
            "maatregel is. Voor die gebieden is dit antwoord een ondergrens op wat er "
            "mogelijk is"
        ),
    )


def _coupling_law_caveat(input, extra) -> ModelCaveat | None:
    """De koppelingswet is een open vraag en het cascade-effect hangt eraan.

    Staat apart van de andere caveats omdat hij alleen op systeemschaal bestaat: bij een
    losse polder is er geen benedenstroomse stand die iets blokkeert.
    """
    if not extra.get("coupling_law"):
        return None
    return ModelCaveat(
        topic="koppelingswet tussen gebieden",
        what=(
            "De capaciteit neemt lineair af met de benedenstroomse stand. Of waterschappen "
            "een poldergemaal zo modelleren of met een uitschakelpeil, en met welke "
            "waarden, is een open vraag"
        ),
        consequence=(
            "De grootte van het cascade-effect hangt hieraan. De richting niet: op een "
            "gemeten ketting draait de rangorde van de maatregelen om zodra de "
            "opvoerhoogte onder ongeveer 5 m komt, en dat is de hele plausibele band voor "
            "een poldergemaal. Wat wel schuift is hoeveel het scheelt"
        ),
    )


def _allocation_rule_caveat(input, extra) -> ModelCaveat | None:
    """De regel binnen een categorie is een keuze, en de wet noemt een andere.

    Staat apart omdat hij alleen bij een verdelingsvraag bestaat: bij een losse aanvoervraag
    is er niets te verdelen, en dan is er ook geen regel om over te beslissen.
    """
    rule = extra.get("allocation_rule")
    if not rule:
        return None
    return ModelCaveat(
        topic="verdeling binnen een categorie",
        what=(
            "De wettelijke verdringingsreeks (art. 3.14 Bkl) ordent de vier categorieen, en "
            "noemt binnen categorie 3 en 4 minimalisatie van de economische maatschappelijke "
            f"schade als criterium. Dit model verdeelt binnen een categorie {rule!r} - bij "
            "'proportional' krijgt iedereen dezelfde dekkingsfractie"
        ),
        consequence=(
            "Dat is een proxy en niet het wettelijke criterium: zodra de schadefuncties per "
            "afnemer verschillen, wijkt gelijk verdelen daarvan af. De ORDENING tussen de "
            "categorieen is wel de wettelijke, en die is bindend - tussen categorie 3 en 4 is "
            "nadere prioritering niet mogelijk. Gebruik de verdeling binnen een schil dus als "
            "bandbreedte en niet als voorschrift"
        ),
    )


def _allocation_source_caveat(input, extra) -> ModelCaveat | None:
    """Waar het bronvolume vandaan komt, zit niet in dit model."""
    if not extra.get("source_volume_given"):
        return None
    return ModelCaveat(
        topic="herkomst van het bronvolume",
        what=(
            "Het beschikbare volume is hier een INVOER. Hoe het tot stand komt - de "
            "landelijke waterverdeling, het Distributiemodel, de afvoer van de Rijn - zit "
            "niet in dit model"
        ),
        consequence=(
            "Dit antwoord is dus voorwaardelijk: 'als er zoveel is, dan valt dit af'. Het is "
            "geen voorspelling van hoeveel er zal zijn. De trap in `theta_steps` is daarom "
            "bruikbaarder dan het ene getal: die laat zien vanaf welk aanbod het antwoord "
            "verandert, zonder dat er een aanbod voorspeld hoeft te worden"
        ),
    )


def _raised_datum_caveat(input, extra) -> ModelCaveat | None:
    """Peilopzet in een cascade telt in de stijging, maar niet in de opvoerhoogte."""
    nodes = getattr(input, "nodes", None) or []
    if not any(getattr(node, "target_level_rise_m", 0.0) for node in nodes):
        return None
    return ModelCaveat(
        topic="peilopzet en de koppeling tussen gebieden",
        what=(
            "De peilopzet van een gebied telt mee in de gerapporteerde stijging, want die "
            "wordt boven het oorspronkelijke peil gemeten. Wat het model NIET doet is de "
            "opvoerhoogte tussen twee gebieden aanpassen: een gebied dat 20 cm hoger staat "
            "pompt in werkelijkheid tegen 20 cm minder verval naar zijn benedenstrooms "
            "gebied, en dat verschil in nulpunt zit niet in de doorrekening"
        ),
        consequence=(
            "Het gemaal van een opgezet gebied wordt hier dus iets te pessimistisch "
            "gerekend zolang `head_max_m` is opgegeven. Bij een peilonafhankelijk gemaal "
            "maakt het niets uit, want dan speelt de opvoerhoogte geen rol"
        ),
    )


CAVEAT_RULES = (
    _allocation_rule_caveat,
    _allocation_source_caveat,
    _summer_loss_caveat,
    _event_length_caveat,
    _return_period_caveat,
    _cost_caveat,
    _supply_availability_caveat,
    _supply_source_origin_caveat,
    _no_groundwater_caveat,
    _coupling_law_caveat,
    _raised_datum_caveat,
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

    Die is daar de peilband die je inzet, en de aanvoertools zetten hem dan ook als
    `level_margin_m` op de toestand. `target_level_rise_m` doen ze niets mee, dus een post
    daarover zou een prijs melden voor iets wat dit antwoord niet gebruikt.
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
    return dict(
        topic="peilmarge" if name == "peilmarge" else "bruikbare diepte onder streefpeil",
        magnitude=f"{margin * 100:.0f} cm",
        what_it_costs="Bedrijfsvoering en drooglegging: de marge die je onder het streefpeil vrijmaakt "
        "is zomervoorraad die je in een droge periode niet meer hebt, en op de natte kant "
        "maalt het gemaal ervoor voor op een bui die nog niet gevallen is. Die kosten "
        "staan niet in `cost`, terwijl de VERLAGING van `cost` die deze marge oplevert er "
        "wel in staat - een peilmarge van 30 cm brengt de benodigde berging op de "
        "referentiepolder van 68 naar 38 ha.",
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


PRICELESS_RULES = (_target_level_rise_post, _level_margin_post, _supply_post)


def priceless_posts(input, measure_nl: str | None = None) -> list:
    """De posten in dit antwoord die geen bedrag hebben maar wel een prijs.

    Levert dicts en geen `PricelessPost`, want die woont in `results.py` en dat bestand
    importeert dit bestand al. De regels horen hier omdat ze naar INVOERvelden kijken, net
    als `CAVEAT_RULES`.
    """
    found = (rule(input, measure_nl) for rule in PRICELESS_RULES)
    return [post for post in found if post is not None]


def supported_digits(spread: float, value: float) -> int | None:
    """Hoeveel significante cijfers de spreiding toestaat, of `None` bij geen informatie.

    De uitvoer houdt vier cijfers - die zijn nodig voor round-tripping en voor de
    regressietests - maar de *tekst* hoort niet meer te beweren dan er te weten valt. Boven
    30 % spreiding is een cijfer genoeg, boven 3 % zijn het twee.

    `None` betekent "we hebben geen spreiding gemeten", en dan blijft de formattering zoals
    hij was. Dat is geen gemakzucht maar dezelfde discipline als bij de caveats: heeft de
    beller alles ingevuld, dan is er geen parametrische onzekerheid die WIJ kennen, en dan
    gaan we er ook geen cijfers aan toevoegen. Wat er dan nog aan onzekerheid over is, is
    structureel, en die staat in `caveats` en niet in een getal.
    """
    if not value or spread <= 0:
        return None
    relative = abs(spread / value)
    if relative > 0.30:
        return 1
    if relative > 0.03:
        return 2
    return 3

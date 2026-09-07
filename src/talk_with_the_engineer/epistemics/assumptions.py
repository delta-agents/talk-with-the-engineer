"""Welke standaardwaarden heeft de beller niet zelf ingevuld?

De eerste van de vier epistemieklagen. Elk veld met een fallback rekent stilzwijgend door
als de beller het weglaat; deze laag maakt dat zichtbaar in de uitvoer.

De BOEKHOUDING zit in de schemalaag - `AssumedDefaults` onthoudt welke velden zijn
ingevuld - en de RAPPORTAGE hier. Die scheiding is met opzet: het invoermodel weet welke
velden leeg binnenkwamen, en wat dat voor een antwoord betekent is geen eigenschap van
het invoermodel.
"""

from pydantic import BaseModel, ConfigDict, Field

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

    `why_it_matters` volgt de taal van de aanroep, want anders staat er onder een Engelse
    uitlegzin een Nederlandse motivering.
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

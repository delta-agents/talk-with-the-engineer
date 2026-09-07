"""Parametrische onzekerheid: de spreiding, en de precisie die daaruit volgt.

De massabalans is exact; de maatregelen zijn vuistregels. Vier significante cijfers op
alles gaf die twee dezelfde status, en dat is de eigenlijke fout - niet de precisie zelf,
maar dat hij overal gelijk is.

Gemeten hoe groot dat verschil is. Bergen, doel 1,0 m, T=100, op de referentiecasus
(4000 ha, 3,5 % open water, gemaal 5 m3/s), basisantwoord 68,18 ha:

    percentage_open_water 3,0 -> 4,0     48,2 - 88,2 ha, dus 59 % spreiding op EEN veld
    regime LL -> H                        0,6 - 98,5 ha
    alle aangenomen velden samen         64 % slaat om naar "geen maatregel nodig"
    rangorde bergen versus afvoeren      0 van 162 combinaties draait om

Het model is dus niet uniform betrouwbaar. Het is sterk over haalbaarheid en rangorde en
zwak over maatvoering, en de uitvoer hoort dat te laten zien in plaats van te verbergen.

De vijf functies onderaan horen bij deze laag en niet bij de omkering: ze rekenen een
antwoord meerdere keren door om de spreiding te meten, en dat is een uitspraak OVER een
antwoord en geen stap in de transitie. Ze leunen op `solve` en `evaluate` uit de kern, en
dat is de toegestane richting - andersom zou de kern zijn eigen epistemiek importeren.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import ModelRetry

from talk_with_the_engineer.core.inverse import (
    evaluate,
    solve,
)
from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.epistemics.assumptions import (
    field_value_text,
    in_language,
    language_of,
)
from talk_with_the_engineer.epistemics.caveats import model_caveats

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


def sensitivity_of(input, answer_for) -> list[Sensitivity]:
    """De spreiding van het antwoord over de velden die de beller heeft weggelaten.

    `answer_for(variant) -> (getal, opmerking)` is de doorrekening van de tool zelf met een
    aangepaste invoer. Dat is per tool twee regels en het houdt deze functie onwetend van
    wat "het antwoord" is - bij de inverse tools de maatvoering, bij de voorwaartse de
    waterstand.

    Alleen weggelaten velden: daar is de onzekerheid van ons. Wat de beller zelf invulde
    weet hij, en een bandbreedte eromheen zouden wij verzinnen.

    Kosten: twee doorrekeningen per veld, dus bij een kale aanroep een tiental. Op een
    inverse van 5 ms is dat een paar tienden van een seconde en het is de enige manier om
    van "dit veld doet veel" een getal te maken.
    """
    language = language_of(input)
    invalid = in_language(
        {
            "nl": "deze waarde is in dit watersysteem niet geldig",
            "en": "this value is not valid in this water system",
        },
        language,
    )
    reported = []
    for field in sorted(input.assumed_fields & set(FIELD_RANGES)):
        low_value, high_value = FIELD_RANGES[field]
        answers, notes = [], []
        for value in (low_value, high_value):
            try:
                answer, note = answer_for(input.model_copy(update={field: value}))
            except (ValueError, ModelRetry):
                answer, note = None, invalid
            answers.append(answer)
            notes.append(note)
        # Een opmerking per KOLOM. Ze stonden eerder samengevoegd in een veld `note`, met
        # een enkelvoudig "bij deze waarde" erin - en zodra beide kolommen `null` zijn,
        # wat bij `no_measure_needed` en bij `action_infeasible` gebeurt, verwees dat naar
        # twee waarden tegelijk zonder te zeggen welke welke was.
        reported.append(
            Sensitivity(
                field=field,
                # de weergave en niet de ruwe waarde: de buiduur gaat in uren in en komt in
                # dagen terug. Zie `FIELD_VALUE_TEXT`.
                low_value=field_value_text(field, low_value, language),
                high_value=field_value_text(field, high_value, language),
                low_answer=answers[0],
                high_answer=answers[1],
                low_note=notes[0],
                high_note=notes[1],
            )
        )
    return reported


def spread_of(sensitivity, reported_answer: float) -> float:
    """De grootste afstand tussen het gemelde antwoord en een rand van het bereik.

    Dit is wat `supported_digits` nodig heeft. Bewust het maximum en niet de spreiding
    tussen de randen: als het antwoord dicht bij de ene rand ligt is de afstand naar de
    andere de eerlijke maat voor hoe hard het kan bewegen.
    """
    distances = [
        abs(value - reported_answer)
        for item in sensitivity
        for value in (item.low_answer, item.high_answer)
        if value is not None
    ]
    return max(distances, default=0.0)


def inverse_answer_for(action_factory, target_field: str):
    """Bouw de `answer_for` die `sensitivity_of` nodig heeft, voor een inverse tool.

    Het gemelde antwoord van een inverse tool is de maatvoering, dus dat is wat er
    gevarieerd wordt. Een variant die een andere STATUS oplevert krijgt geen getal maar een
    opmerking: "geen maatregel nodig" is geen kleine maatvoering maar een ander antwoord, en
    het als 0 in een bereik zetten zou dat verstoppen.
    """

    def answer_for(variant):
        state = PolderState.from_water_system_input(variant)
        result = solve(
            state, variant.to_storm(), action_factory(), getattr(variant, target_field)
        )
        language = language_of(variant)
        if result.status is SolveStatus.NO_MEASURE_NEEDED:
            return None, in_language(
                {
                    "nl": "bij deze waarde is er geen maatregel nodig",
                    "en": "at this value no measure is needed",
                },
                language,
            )
        if result.status is SolveStatus.ACTION_INFEASIBLE:
            return None, in_language(
                {
                    "nl": "bij deze waarde is het doel met deze maatregel niet haalbaar",
                    "en": "at this value the target cannot be reached with this measure",
                },
                language,
            )
        return result.magnitude, None

    return answer_for


def forward_answer_for(action_factory):
    """Idem voor een voorwaartse tool: daar is het gemelde antwoord de waterstandstijging."""

    def answer_for(variant):
        state = PolderState.from_water_system_input(variant)
        return evaluate(
            state, variant.to_storm(), action_factory()
        ).dh_with_measure_m, None

    return answer_for


def uncertainty_for(input, answer_for, **caveat_context):
    """De spreiding en de caveats in een aanroep; wat elke tool aan zijn uitvoer hangt."""
    return sensitivity_of(input, answer_for), model_caveats(input, **caveat_context)

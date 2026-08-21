"""Tekstuitvoer van de vuistregeltools.

Twee uitlegbare zinnen per antwoord, in het Nederlands of Engels, en een derde zodra er
standaardwaarden zijn aangenomen. Apart gehouden van de rekenlogica omdat de formulering
afhangt van de status: een onhaalbaar doel verdient een uitleg met het optimum erbij, geen
getal.

De grootheid waar de tools op rekenen is de maximale water*stijging* met maatregel. Eerder
noemden de teksten van bergen en afvoeren datzelfde getal een "waterstandverlaging",
waardoor 210 cm stijging als 210 cm verlaging werd gerapporteerd. Zie
PLAN_TOOLS_REFACTOR.md D11.
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    LimitReason,
    SolveResult,
    SolveStatus,
)

_OTHER_MEASURES = {
    "bergen": "afvoeren of vasthouden",
    "afvoeren": "bergen of vasthouden",
    "vasthouden": "bergen of afvoeren",
}
_OTHER_MEASURES_EN = {
    "bergen": "discharge or retention",
    "afvoeren": "store or retention",
    "vasthouden": "store or discharge",
}
_MEASURE_EN = {"bergen": "store", "afvoeren": "discharge", "vasthouden": "retention"}


def _event_phrase(return_period: float, language: str) -> str:
    """Benoem de bui zoals je hem uitspreekt, niet zoals hij in het veld staat.

    Een terugkeertijd kleiner dan een jaar is een frequentie: T = 0,5 betekent gemiddeld
    twee keer per jaar, niet "eens per 0,5 jaar". Zo staat het ook in de STOWA-tabel waar
    deze statistiek uit komt - "die gemiddeld 2 maal per jaar tot gemiddeld eens per 1000
    jaar worden overschreden". En "eens per 1 jaar" is "eens per jaar".

    Hele jaren komen zonder decimaal, want `return_period` is een float sinds 0.5
    bereikbaar moest zijn.
    """
    if return_period < 1:
        times_per_year = 1 / return_period
        if language == "en":
            return (
                "an event that occurs twice a year on average"
                if times_per_year == 2
                else f"an event that occurs {times_per_year:g} times a year on average"
            )
        return (
            "een bui die gemiddeld twee keer per jaar voorkomt"
            if times_per_year == 2
            else f"een bui die gemiddeld {times_per_year:g} keer per jaar voorkomt"
        )
    if return_period == 1:
        return (
            "an event that occurs once a year on average"
            if language == "en"
            else ("een bui die gemiddeld eens per jaar voorkomt")
        )
    if language == "en":
        return f"a 1-in-{return_period:g}-year event"
    return f"een bui van eens per {return_period:g} jaar"


def _magnitude_nl(result: SolveResult) -> str:
    if result.unit == "ha open water":
        return f"{result.magnitude:.0f} ha extra open water"
    if result.unit == "ha land":
        return f"{result.magnitude:.0f} ha land"
    return f"{result.magnitude:.2f} m3/s extra gemaalcapaciteit"


def _magnitude_en(result: SolveResult) -> str:
    if result.unit == "ha open water":
        return f"{result.magnitude:.0f} ha of additional open water"
    if result.unit == "ha land":
        return f"{result.magnitude:.0f} ha of land"
    return f"{result.magnitude:.2f} m3/s of additional pumping capacity"


def append_assumptions(text: str, assumptions, language: str) -> str:
    """Zet de aangenomen standaardwaarden achter de uitleg.

    Ze staan ook als `assumptions` in de uitvoer, maar dat is een veld dat een lezer kan
    overslaan; de uitlegzin is wat er wordt voorgelezen. Bij een volledig ingevulde
    aanroep is de lijst leeg en verandert er niets aan de twee zinnen.
    """
    if not assumptions:
        return text
    fields = ", ".join(f"{a.field}={a.value}" for a in assumptions)
    if language == "en":
        return f"{text} Assumed, because they were not given: {fields}."
    return f"{text} Aangenomen omdat ze niet zijn opgegeven: {fields}."


def describe_inverse(result: SolveResult, return_period: float, language: str) -> str:
    """Uitleg bij een inverse berekening: hoeveel maatregel is er nodig?"""
    event = _event_phrase(return_period, language)
    target_cm = (result.target_dh_m or 0.0) * 100
    reference_cm = result.dh_reference_m * 100
    optimum_cm = result.feasible_dh_min_m * 100

    if language == "en":
        measure = _MEASURE_EN[result.measure_nl]
        if result.status is SolveStatus.NO_MEASURE_NEEDED:
            return (
                f"No '{measure}' measure is needed: in {event} "
                f"the water level rises by {reference_cm:.0f} cm, which already stays "
                f"below the {target_cm:.0f} cm available."
            )
        if result.status is SolveStatus.INFEASIBLE:
            limit = (
                "the measure reaches its optimum"
                if result.limit_reason is LimitReason.MEASURE_OPTIMUM
                else "the physical limit of the water system is reached"
            )
            return (
                f"A rise of {target_cm:.0f} cm cannot be reached with '{measure}' alone: "
                f"{limit} at {optimum_cm:.0f} cm, using "
                f"{_magnitude_en(result)}. Combine it with "
                f"{_OTHER_MEASURES_EN[result.measure_nl]} to go further."
            )
        return (
            f"To keep the water level rise at {target_cm:.0f} cm in "
            f"{event}, the '{measure}' measure needs "
            f"{_magnitude_en(result)}. "
            f"Without the measure the rise is {reference_cm:.0f} cm, so this is a "
            f"reduction of {result.dh_reduction_m * 100:.0f} cm."
        )

    if result.status is SolveStatus.NO_MEASURE_NEEDED:
        return (
            f"De maatregel '{result.measure_nl}' is niet nodig: bij {event} "
            f"stijgt de waterstand {reference_cm:.0f} cm, en dat "
            f"blijft al onder de beschikbare {target_cm:.0f} cm."
        )
    if result.status is SolveStatus.INFEASIBLE:
        limit = (
            "de maatregel bereikt zijn optimum"
            if result.limit_reason is LimitReason.MEASURE_OPTIMUM
            else "de fysieke grens van het watersysteem is bereikt"
        )
        return (
            f"Een stijging van {target_cm:.0f} cm is met alleen '{result.measure_nl}' niet "
            f"haalbaar: {limit} bij {optimum_cm:.0f} cm, met "
            f"{_magnitude_nl(result)}. "
            f"Combineer met {_OTHER_MEASURES[result.measure_nl]} om verder te komen."
        )
    return (
        f"Om de waterstandstijging bij {event} op "
        f"{target_cm:.0f} cm te houden, is met de maatregel '{result.measure_nl}' "
        f"{_magnitude_nl(result)} nodig. "
        f"Zonder maatregel is de stijging {reference_cm:.0f} cm, dus dat is een verlaging "
        f"van {result.dh_reduction_m * 100:.0f} cm."
    )


def describe_forward(result: SolveResult, return_period: float, language: str) -> str:
    """Uitleg bij een voorwaartse berekening: wat levert deze maatvoering op?"""
    event = _event_phrase(return_period, language)
    reference_cm = result.dh_reference_m * 100
    with_measure_cm = result.dh_with_measure_m * 100
    reduction_cm = result.dh_reduction_m * 100

    if language == "en":
        measure = _MEASURE_EN[result.measure_nl]
        return (
            f"With {_magnitude_en(result)}, the '{measure}' measure brings the water level "
            f"rise in {event} to {with_measure_cm:.0f} cm. "
            f"Without the measure it is {reference_cm:.0f} cm, so this is a reduction of "
            f"{reduction_cm:.0f} cm."
        )
    return (
        f"Met {_magnitude_nl(result)} brengt de maatregel '{result.measure_nl}' de "
        f"waterstandstijging bij {event} op "
        f"{with_measure_cm:.0f} cm. "
        f"Zonder maatregel is de stijging {reference_cm:.0f} cm, dus dat is een verlaging "
        f"van {reduction_cm:.0f} cm."
    )

"""Tekstuitvoer van de vuistregeltools.

Twee uitlegbare zinnen per antwoord, in het Nederlands of Engels. Apart gehouden van de
rekenlogica omdat de formulering afhangt van de status: een onhaalbaar doel verdient een
uitleg met het optimum erbij, geen getal.

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


def describe_inverse(result: SolveResult, return_period: int, language: str) -> str:
    """Uitleg bij een inverse berekening: hoeveel maatregel is er nodig?"""
    target_cm = (result.target_dh_m or 0.0) * 100
    reference_cm = result.dh_reference_m * 100
    optimum_cm = result.feasible_dh_min_m * 100

    if language == "en":
        measure = _MEASURE_EN[result.measure_nl]
        if result.status is SolveStatus.NO_MEASURE_NEEDED:
            return (
                f"No '{measure}' measure is needed: in a 1-in-{return_period}-year event "
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
            f"To keep the water level rise at {target_cm:.0f} cm in a "
            f"1-in-{return_period}-year event, the '{measure}' measure needs "
            f"{_magnitude_en(result)}. "
            f"Without the measure the rise is {reference_cm:.0f} cm, so this is a "
            f"reduction of {result.dh_reduction_m * 100:.0f} cm."
        )

    if result.status is SolveStatus.NO_MEASURE_NEEDED:
        return (
            f"De maatregel '{result.measure_nl}' is niet nodig: bij een bui van eens per "
            f"{return_period} jaar stijgt de waterstand {reference_cm:.0f} cm, en dat "
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
        f"Om de waterstandstijging bij een bui van eens per {return_period} jaar op "
        f"{target_cm:.0f} cm te houden, is met de maatregel '{result.measure_nl}' "
        f"{_magnitude_nl(result)} nodig. "
        f"Zonder maatregel is de stijging {reference_cm:.0f} cm, dus dat is een verlaging "
        f"van {result.dh_reduction_m * 100:.0f} cm."
    )


def describe_forward(result: SolveResult, return_period: int, language: str) -> str:
    """Uitleg bij een voorwaartse berekening: wat levert deze maatvoering op?"""
    reference_cm = result.dh_reference_m * 100
    with_measure_cm = result.dh_with_measure_m * 100
    reduction_cm = result.dh_reduction_m * 100

    if language == "en":
        measure = _MEASURE_EN[result.measure_nl]
        return (
            f"With {_magnitude_en(result)}, the '{measure}' measure brings the water level "
            f"rise in a 1-in-{return_period}-year event to {with_measure_cm:.0f} cm. "
            f"Without the measure it is {reference_cm:.0f} cm, so this is a reduction of "
            f"{reduction_cm:.0f} cm."
        )
    return (
        f"Met {_magnitude_nl(result)} brengt de maatregel '{result.measure_nl}' de "
        f"waterstandstijging bij een bui van eens per {return_period} jaar op "
        f"{with_measure_cm:.0f} cm. "
        f"Zonder maatregel is de stijging {reference_cm:.0f} cm, dus dat is een verlaging "
        f"van {reduction_cm:.0f} cm."
    )

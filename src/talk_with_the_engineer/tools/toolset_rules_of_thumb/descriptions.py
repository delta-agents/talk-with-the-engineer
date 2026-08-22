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
    "aanvoeren": "bergen of vasthouden",
    "voorbemalen": "bergen, afvoeren of vasthouden",
}
_OTHER_MEASURES_EN = {
    "bergen": "discharge or retention",
    "afvoeren": "store or retention",
    "vasthouden": "store or discharge",
    "aanvoeren": "store or retention",
    "voorbemalen": "store, discharge or retention",
}
_MEASURE_EN = {
    "bergen": "store",
    "afvoeren": "discharge",
    "vasthouden": "retention",
    "aanvoeren": "supply",
    "voorbemalen": "prerelease",
}


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
    if result.unit == "m3/s inlaat":
        return f"{result.magnitude:.2f} m3/s extra inlaatcapaciteit"
    if result.unit == "m peilmarge":
        return f"{result.magnitude * 100:.0f} cm peilmarge"
    return f"{result.magnitude:.2f} m3/s extra gemaalcapaciteit"


def _magnitude_en(result: SolveResult) -> str:
    if result.unit == "ha open water":
        return f"{result.magnitude:.0f} ha of additional open water"
    if result.unit == "ha land":
        return f"{result.magnitude:.0f} ha of land"
    if result.unit == "m3/s inlaat":
        return f"{result.magnitude:.2f} m3/s of additional intake capacity"
    if result.unit == "m peilmarge":
        return f"{result.magnitude * 100:.0f} cm of level margin"
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
        if result.status is SolveStatus.ACTION_INFEASIBLE:
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
    if result.status is SolveStatus.ACTION_INFEASIBLE:
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


# --- de droogtekant vertelt een ander verhaal ----------------------------------------
#
# Op de natte kant is de zin "de stijging blijft onder X". Dat frame past hier niet: er is
# geen stijging maar een uitzakking, en de interessante grootheid is niet een waterstand
# maar hoeveel vraag onvervuld blijft en hoe lang de eigen berging het volhoudt. Daarom
# eigen tekstfuncties in plaats van een vlag op de bestaande.
#
# Het aantal dagen staat vooraan waar dat kan. "Nog 19 van de 30 dagen" is voor een lezer
# af te wegen; "5,8 mm onvervulde vraag" is dat niet.


def _days_phrase(result, length_days: int, language: str) -> str:
    days = result.days_until_buffer_empty
    if days == float("inf"):
        return (
            f"the level never reaches the limit within {length_days} days"
            if language == "en"
            else f"het peil raakt de grens binnen {length_days} dagen niet"
        )
    if language == "en":
        return f"the buffer runs out after {days:.0f} of the {length_days} days"
    return f"de berging is na {days:.0f} van de {length_days} dagen op"


def describe_supply_inverse(result, input, language: str) -> str:
    """Uitleg bij de inverse: hoeveel inlaatcapaciteit is er nodig?"""
    per_ha = result.supply_capacity_m3_per_sec * 1000 / input.area_ha
    deficit = input.deficit_mm_per_day
    days = input.length_days

    if language == "en":
        if result.status is SolveStatus.NO_MEASURE_NEEDED:
            return (
                f"No intake capacity is needed: a deficit of {deficit:g} mm/day over "
                f"{days} days asks {result.demand_mm:.0f} mm, and the "
                f"{result.buffer_mm:.0f} mm of storage below the target level already "
                f"covers it."
            )
        if result.status is SolveStatus.ACTION_INFEASIBLE:
            return (
                f"A deficit of {deficit:g} mm/day over {days} days cannot be covered by "
                f"intake alone: even {per_ha:.2f} l/s/ha leaves {result.shortfall_mm:.0f} "
                f"mm of demand unmet. Combine it with store or retention."
            )
        return (
            f"To cover a deficit of {deficit:g} mm/day over {days} days, the intake needs "
            f"{per_ha:.2f} l/s/ha ({result.supply_capacity_m3_per_sec:.2f} m3/s). That "
            f"delivers {result.supplied_mm:.0f} mm; the remaining {result.buffer_mm:.0f} "
            f"mm comes from storage below the target level, drawing it down "
            f"{result.drawdown_m * 100:.0f} cm."
        )

    if result.status is SolveStatus.NO_MEASURE_NEEDED:
        return (
            f"Er is geen inlaatcapaciteit nodig: een tekort van {deficit:g} mm/dag over "
            f"{days} dagen vraagt {result.demand_mm:.0f} mm, en de "
            f"{result.buffer_mm:.0f} mm berging onder het streefpeil dekt dat al."
        )
    if result.status is SolveStatus.ACTION_INFEASIBLE:
        return (
            f"Een tekort van {deficit:g} mm/dag over {days} dagen is met alleen aanvoeren "
            f"niet te dekken: zelfs {per_ha:.2f} l/s/ha laat {result.shortfall_mm:.0f} mm "
            f"vraag onvervuld. Combineer met bergen of vasthouden."
        )
    return (
        f"Om een tekort van {deficit:g} mm/dag over {days} dagen te dekken is een inlaat "
        f"van {per_ha:.2f} l/s/ha nodig ({result.supply_capacity_m3_per_sec:.2f} m3/s). "
        f"Die levert {result.supplied_mm:.0f} mm; de resterende {result.buffer_mm:.0f} mm "
        f"komt uit de berging onder het streefpeil, die daarvoor "
        f"{result.drawdown_m * 100:.0f} cm uitzakt."
    )


def describe_supply_forward(result, input, language: str) -> str:
    """Uitleg bij de voorwaartse richting: wat doet deze inlaatcapaciteit?"""
    per_ha = result.supply_capacity_m3_per_sec * 1000 / input.area_ha
    deficit = input.deficit_mm_per_day
    days = input.length_days
    covered = result.shortfall_mm <= 1e-9
    when = _days_phrase(result, days, language)

    if language == "en":
        if covered:
            return (
                f"An intake of {per_ha:.2f} l/s/ha covers a deficit of {deficit:g} mm/day "
                f"over {days} days: it delivers {result.supplied_mm:.0f} of the "
                f"{result.demand_mm:.0f} mm demand and {when}."
            )
        return (
            f"An intake of {per_ha:.2f} l/s/ha delivers {result.supplied_mm:.0f} of the "
            f"{result.demand_mm:.0f} mm that a deficit of {deficit:g} mm/day over {days} "
            f"days asks; {when}, and {result.shortfall_mm:.0f} mm of demand stays unmet. "
            f"The level drops {result.drawdown_m * 100:.0f} cm."
        )

    if covered:
        return (
            f"Een inlaat van {per_ha:.2f} l/s/ha dekt een tekort van {deficit:g} mm/dag "
            f"over {days} dagen: hij levert {result.supplied_mm:.0f} van de "
            f"{result.demand_mm:.0f} mm vraag, en {when}."
        )
    return (
        f"Een inlaat van {per_ha:.2f} l/s/ha levert {result.supplied_mm:.0f} van de "
        f"{result.demand_mm:.0f} mm die een tekort van {deficit:g} mm/dag over {days} "
        f"dagen vraagt; {when}, en {result.shortfall_mm:.0f} mm vraag blijft onvervuld. "
        f"Het peil zakt {result.drawdown_m * 100:.0f} cm uit."
    )

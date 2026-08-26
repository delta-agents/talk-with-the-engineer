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

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    supported_digits,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    LimitReason,
    MeasureRole,
    SolveResult,
    SolveStatus,
    round_significant,
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
    "peilopzet": "raise target level",
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


def _rounded(
    value: float, digits: int | None, fallback_decimals: int | None = None
) -> str:
    """De maatvoering met de precisie die de spreiding toestaat.

    `data` houdt altijd vier significante cijfers - die zijn nodig voor round-tripping en
    voor de regressietests - maar de tekst is wat een agent voorleest, en die hoort niet
    meer te beweren dan er te weten valt. Zonder spreiding blijft het gedrag zoals het was.

    `fallback_decimals` is dat "zoals het was" voor de eenheden die hun eigen opmaak hadden:
    een debiet werd altijd op twee decimalen gemeld en een peilmarge op hele centimeters.
    Zonder die parameter zou het routeren van die eenheden door deze functie hun precisie
    stil verlagen - "3 m3/s" waar "2,91 m3/s" stond - en dat is een andere wijziging dan
    hier bedoeld. Is er wél een spreiding gemeten, dan telt die en niet de fallback.
    """
    if digits is None:
        if fallback_decimals is not None:
            return f"{value:.{fallback_decimals}f}"
        return f"{value:.0f}" if abs(value) >= 1 else f"{value:.2f}"
    return f"{round_significant(value, digits):g}"


def _approximation(value: float, digits: int | None, language: str) -> str:
    """"ongeveer " als het getal in de tekst merkbaar is afgerond, anders niets.

    De afronding zelf is goed: het model is zwak over maatvoering, en drie cijfers noemen
    waar de spreiding er een toestaat is valse precisie. Maar het RESULTAAT werd als punt
    gepresenteerd - "10 ha" - terwijl `measure.delta` in dezelfde uitvoer 12,71 ha zegt.
    Een beller die beide doorgeeft, spreekt zichzelf tegen.

    Met dit woordje is de zin geen tweede, afwijkende bewering meer maar een benadering van
    dezelfde. Het bereik zelf staat er ook nog: `append_spread` zet "reken op 13 tot 128 ha"
    erachter zodra de spreiding groot genoeg is.

    De drempel is een half procent, zodat een afronding die niets verschuift ook niets
    toevoegt aan de zin.
    """
    if digits is None or not value:
        return ""
    if abs(round_significant(value, digits) - value) <= abs(value) * 5e-3:
        return ""
    return "about " if language == "en" else "ongeveer "


# Alle vijf de eenheden lopen door `_rounded`, en dat was niet zo. Drie ervan - de twee
# debieten en de peilmarge - hadden hun opmaak hardgecodeerd, waardoor de afgeleide precisie
# uit `supported_digits` er niet aan kwam. Dat was precies de "2,91 m3/s" uit issue #30: de
# discipline bestond al en deze drie takken sloegen hem over.
def _magnitude_nl(result: SolveResult, digits: int | None = None) -> str:
    about = _approximation(result.magnitude, digits, "nl")
    if result.unit == "ha open water":
        return f"{about}{_rounded(result.magnitude, digits)} ha extra open water"
    if result.unit == "ha land":
        return f"{about}{_rounded(result.magnitude, digits)} ha land"
    if result.unit == "m3/s inlaat":
        return f"{about}{_rounded(result.magnitude, digits, 2)} m3/s extra inlaatcapaciteit"
    if result.unit == "m peilmarge":
        return f"{about}{_rounded(result.magnitude * 100, digits, 0)} cm peilmarge"
    return f"{about}{_rounded(result.magnitude, digits, 2)} m3/s extra gemaalcapaciteit"


def _magnitude_en(result: SolveResult, digits: int | None = None) -> str:
    about = _approximation(result.magnitude, digits, "en")
    if result.unit == "ha open water":
        return f"{about}{_rounded(result.magnitude, digits)} ha of additional open water"
    if result.unit == "ha land":
        return f"{about}{_rounded(result.magnitude, digits)} ha of land"
    if result.unit == "m3/s inlaat":
        return (
            f"{about}{_rounded(result.magnitude, digits, 2)} m3/s of additional intake "
            f"capacity"
        )
    if result.unit == "m peilmarge":
        return f"{about}{_rounded(result.magnitude * 100, digits, 0)} cm of level margin"
    return (
        f"{about}{_rounded(result.magnitude, digits, 2)} m3/s of additional pumping "
        f"capacity"
    )


# --- het gebied in plaats van het punt ----------------------------------------------
#
# Een pakketzoeker die één punt meldt, verbergt de speelruimte. Deze functies zeggen wat
# vastzit en wat vrij is, met een interval erbij - en de precisie van dat interval volgt uit
# de BREEDTE van het interval, net zoals `append_spread` hem uit de spreiding haalt. Een
# gebied van 2,912 tot 3,185 melden zou dezelfde valse precisie zijn als een punt van 2,91.

# De maatregel staat al in de zin, dus de eenheid hoeft hem niet te herhalen: "'peilopzet'
# 57 cm" en niet "'peilopzet' 57 cm peilopzet". Alleen waar de eenheid zelf ambigu is - een
# hectare land is iets anders dan een hectare open water - staat er een woord bij.
_REGION_UNIT = {
    "ha open water": ("ha open water", 1.0),
    "ha land": ("ha land", 1.0),
    "m3/s": ("m3/s", 1.0),
    "m3/s inlaat": ("m3/s", 1.0),
    "m peilopzet": ("cm", 100.0),
    "m peilmarge": ("cm", 100.0),
}


def _interval_phrase(measure_range, language: str) -> str:
    """Het interval van één maatregel, met de precisie die de breedte toestaat.

    `supported_digits` is hier bewust hergebruikt. Hij is gemaakt voor de spreiding over de
    aangenomen invoervelden, maar de vraag is dezelfde: hoeveel cijfers mag ik noemen gegeven
    hoe hard dit getal kan bewegen. Een interval van 2,912 tot 3,185 wordt daarmee "2,9 tot
    3,2" - en een plateau van 0,571 tot 1,000 m wordt "60 tot 100 cm", want een interval dat
    75 % breed is verdraagt geen twee cijfers.
    """
    words, scale = _REGION_UNIT.get(measure_range.unit, (measure_range.unit, 1.0))
    low = measure_range.magnitude_min * scale
    high = measure_range.magnitude_max * scale
    # Twee cijfers als er geen breedte is. Een interval dat tot een punt samenvalt weet niets
    # over zijn eigen precisie, en dan is drie cijfers noemen precies de fout die we hier
    # aan het repareren zijn - te meer omdat een punt hier vaak betekent dat de sweep
    # coordinaatgewijs vastzit en de echte ruimte groter is. Zie `ranges_of`.
    digits = supported_digits(high - low, low) or 2
    low_text = f"{round_significant(low, digits):g}"
    high_text = f"{round_significant(high, digits):g}"
    if low_text == high_text:
        return f"{low_text} {words}"
    joiner = "to" if language == "en" else "tot"
    return f"{low_text} {joiner} {high_text} {words}"


def describe_region(ranges, language: str = "nl") -> str:
    """Wat er vastzit, wat vrij is, en tussen welke grenzen.

    Dit is de zin die in plaats van "2,91 m3/s" hoort te staan. Niet omdat 2,91 fout is,
    maar omdat het net zo goed 3,1 had kunnen zijn en de lezer dat niet kan zien. Een
    optimum is alleen optimaal voor wat er gemodelleerd is; wat een waterschap daarnaast
    heeft - draagvlak, uitvoerbaarheid, een prijs die eigenlijk een trap is - leeft náást
    dat punt, en de enige eerlijke uitspraak daarover is hoeveel ruimte er is.

    De twee grenzen betekenen niet hetzelfde, en dat staat er daarom bij: de onderkant is
    wat de EIS vraagt, de bovenkant wat binnen de PRIJSBAND nog past. En `absent` betekent
    "draagt niet bij", niet "te duur" - dat onderscheid is voor een bestuurder het verschil
    tussen een maatregel die afvalt en een maatregel die nooit meedeed.
    """
    forced = [r for r in ranges if r.role is MeasureRole.FORCED]
    optional = [r for r in ranges if r.role is MeasureRole.OPTIONAL]
    absent = [r for r in ranges if r.role is MeasureRole.ABSENT]

    def name(measure_range):
        if language == "en":
            return _MEASURE_EN.get(measure_range.name_nl, measure_range.name_nl)
        return measure_range.name_nl

    def listing(items):
        names = [name(item) for item in items]
        if len(names) == 1:
            return names[0]
        joiner = " and " if language == "en" else " en "
        return ", ".join(names[:-1]) + joiner + names[-1]

    def clauses(items):
        return ", ".join(f"'{name(r)}' {_interval_phrase(r, language)}" for r in items)

    parts = []
    if forced:
        if language == "en":
            parts.append(
                f"Every package that is equally good within the price band uses "
                f"{clauses(forced)}. The lower end is what the requirement demands; below "
                f"it the requirement is not met. The upper end is what still fits within "
                f"the price band; above it nothing more is bought."
            )
        else:
            parts.append(
                f"Elk pakket dat binnen de prijsband even goed is, gebruikt "
                f"{clauses(forced)}. De onderkant is wat de eis vraagt - daaronder wordt de "
                f"eis niet gehaald. De bovenkant is wat er binnen de prijsband nog past; "
                f"daarboven koopt het niets meer."
            )
    if optional:
        if language == "en":
            parts.append(
                f"Optional, so this is a choice and not ours: {clauses(optional)}."
            )
        else:
            parts.append(
                f"Optioneel, en dus een keuze die niet van ons is: {clauses(optional)}."
            )
    if absent:
        plural = len(absent) > 1
        if language == "en":
            verb = "appear" if plural else "appears"
            parts.append(
                f"{listing(absent).capitalize()} {verb} in no package in this region - not "
                f"because they are too expensive but because they do not contribute."
                if plural
                else f"{listing(absent).capitalize()} {verb} in no package in this region - "
                f"not because it is too expensive but because it does not contribute."
            )
        else:
            verb = "komen" if plural else "komt"
            parts.append(
                f"{listing(absent).capitalize()} {verb} in geen enkel pakket in dit gebied "
                f"voor - niet omdat ze te duur zijn maar omdat ze niet bijdragen."
                if plural
                else f"{listing(absent).capitalize()} {verb} in geen enkel pakket in dit "
                f"gebied voor - niet omdat het te duur is maar omdat het niet bijdraagt."
            )
    return " ".join(parts)


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


def describe_inverse(
    result: SolveResult, return_period: float, language: str, digits: int | None = None
) -> str:
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
                f"{_magnitude_en(result, digits)}. Combine it with "
                f"{_OTHER_MEASURES_EN[result.measure_nl]} to go further."
            )
        return (
            f"To keep the water level rise at {target_cm:.0f} cm in "
            f"{event}, the '{measure}' measure needs "
            f"{_magnitude_en(result, digits)}. "
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
            f"{_magnitude_nl(result, digits)}. "
            f"Combineer met {_OTHER_MEASURES[result.measure_nl]} om verder te komen."
        )
    return (
        f"Om de waterstandstijging bij {event} op "
        f"{target_cm:.0f} cm te houden, is met de maatregel '{result.measure_nl}' "
        f"{_magnitude_nl(result, digits)} nodig. "
        f"Zonder maatregel is de stijging {reference_cm:.0f} cm, dus dat is een verlaging "
        f"van {result.dh_reduction_m * 100:.0f} cm."
    )


def _past_optimum_clause(result: SolveResult, language: str) -> str:
    """De zin die zegt dat een kleinere maatregel hier beter EN goedkoper is.

    Alleen bij een binnenoptimum, en alleen als de opgegeven maatvoering erboven ligt. Dat
    is het meest contra-intuitieve resultaat dat dit model produceert - meer land
    vasthouden maakt de piek hoger, want het uitgestelde water komt op de piek terug - en
    het stond nergens in de tekst. Wie 3800 ha opgaf kreeg een exact antwoord dat 44 % meer
    kost dan 2645 ha voor een 5 cm hogere stijging, zonder dat er iets op dat betere punt
    wees.
    """
    if result.limit_reason is not LimitReason.PAST_OPTIMUM:
        return ""
    optimum = _rounded(result.magnitude_at_optimum, 2)
    unit = "ha" if result.unit.startswith("ha") else result.unit
    if language == "en":
        return (
            f" This sizing lies PAST the optimum of the measure: {optimum} {unit} gives a "
            f"lower rise for less money, and everything above that point buys a worse "
            f"result at a higher price."
        )
    return (
        f" Deze maatvoering ligt VOORBIJ het optimum van de maatregel: bij {optimum} "
        f"{unit} is de stijging lager en de prijs ook, en alles daarboven koopt een "
        f"slechter resultaat voor meer geld."
    )


def describe_forward(
    result: SolveResult, return_period: float, language: str, digits: int | None = None
) -> str:
    """Uitleg bij een voorwaartse berekening: wat levert deze maatvoering op?"""
    event = _event_phrase(return_period, language)
    reference_cm = result.dh_reference_m * 100
    with_measure_cm = result.dh_with_measure_m * 100
    reduction_cm = result.dh_reduction_m * 100

    if language == "en":
        measure = _MEASURE_EN[result.measure_nl]
        return (
            f"With {_magnitude_en(result, digits)}, the '{measure}' measure brings the water level "
            f"rise in {event} to {with_measure_cm:.0f} cm. "
            f"Without the measure it is {reference_cm:.0f} cm, so this is a reduction of "
            f"{reduction_cm:.0f} cm." + _past_optimum_clause(result, language)
        )
    return (
        f"Met {_magnitude_nl(result, digits)} brengt de maatregel '{result.measure_nl}' de "
        f"waterstandstijging bij {event} op "
        f"{with_measure_cm:.0f} cm. "
        f"Zonder maatregel is de stijging {reference_cm:.0f} cm, dus dat is een verlaging "
        f"van {reduction_cm:.0f} cm." + _past_optimum_clause(result, language)
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
            else f"de waterstand raakt de grens binnen {length_days} dagen niet"
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
        f"De waterstand zakt {result.drawdown_m * 100:.0f} cm uit."
    )


def append_spread(
    text: str, sensitivity, answer: float, unit: str, language: str
) -> str:
    """Zet de spreiding achter de uitleg, met de oorzaak erbij.

    Het gemelde getal is niet fout, maar het is het midden van een bereik dat de beller
    niet ziet. Bij een kale aanroep loopt de benodigde berging van 13 tot 128 ha over de
    keuze van het seizoen alleen - dan is "35 ha" een antwoord dat zijn eigen precisie
    tegenspreekt.

    Alleen het veld dat het hardst uitmaakt, en alleen als het iets uitmaakt. Drie velden
    opsommen is een lijst; één veld met zijn bereik is een uitspraak.
    """
    ranges = [
        (max(abs(v - answer) for v in values), item, values)
        for item in sensitivity
        if (values := [v for v in (item.low_answer, item.high_answer) if v is not None])
    ]
    if not ranges:
        return text
    spread, worst, values = max(ranges, key=lambda row: row[0])
    if not answer or spread / abs(answer) <= 0.03:
        return text

    low, high = min(values + [answer]), max(values + [answer])
    digits = 2 if spread / abs(answer) <= 0.30 else 1
    low_text = f"{round_significant(low, digits):g}"
    high_text = f"{round_significant(high, digits):g}"
    if language == "en":
        return (
            f"{text} Reckon on {low_text} to {high_text} {unit} depending on "
            f"{worst.field}, which was assumed here."
        )
    return (
        f"{text} Reken op {low_text} tot {high_text} {unit} afhankelijk van "
        f"{worst.field}, die hier is aangenomen."
    )


def describe_allocation(
    result,
    node_count: int,
    theta,
    capacity_bound: bool,
    spread=None,
    language: str = "nl",
) -> str:
    """Wie er afvalt, en of meer water zou helpen.

    Dat tweede is de zin die een verdelingsvraag toevoegt aan een reeks losse
    aanvoervragen. Komt het tekort door de BRON, dan is het advies water aanvoeren of
    rantsoeneren; komt het door de INLATEN, dan helpt meer water niets en is het een
    kunstwerkvraag. Een model per gebied kan dat onderscheid niet maken, want het ziet de
    bron niet.

    En er staat expliciet bij dat de verdeling binnen een categorie een KEUZE is. De wet
    ordent de categorieen en noemt binnen de laagste twee schademinimalisatie als criterium;
    gelijk tekort is wat je doet als je de schadefuncties niet kent. Dat verschil weglaten
    zou dezelfde fout zijn als een puntoptimum melden zonder het gebied.
    """
    binding = result.binding_category
    covered = binding is None
    # boven de volle vraag is een percentage misleidend: "bij 314 % van de vraag als aanbod"
    # leest als een fout terwijl het betekent dat de bron ruim is en de inlaten de klem zijn
    if theta is None or theta >= 1.0:
        share = ""
    else:
        share = f"{theta:.0%}"

    if language == "en":
        if covered:
            text = (
                f"Across {node_count} areas the whole demand is met"
                + (f" at {share} of it available" if share else "")
                + "."
            )
        else:
            coverage = result.coverage_of_category(binding)
            text = (
                f"Across {node_count} areas the demand is not met"
                + (f" at {share} of it available" if share else "")
                + f": category {binding} is the first to fall short, at "
                f"{coverage:.0%} of its demand."
            )
            text += (
                " The intakes are binding, not the source, so supplying more water would "
                "not help - a larger intake would."
                if capacity_bound
                else " The source is binding, so this is a rationing question and not a "
                "structures question."
            )
        if binding is None or not spread:
            return text + (
                " Within a category the shortfall is shared equally. That is a modelling "
                "choice: the law ranks the categories and points to minimising economic and "
                "societal damage within the lowest two, and equal sharing is what stands in "
                "for damage functions we do not have."
            )
        low, high = spread
        return text + (
            f" How much water each category uses does not depend on how it is shared within "
            f"that category; who gets it does. Share the shortfall equally and everyone in "
            f"category {binding} lands on "
            f"{result.coverage_of_category(binding):.0%}; place it on the largest users and "
            f"coverage runs from {low:.0%} to {high:.0%}. The law does not choose between "
            f"those - it points to minimising economic and societal damage, and we do not "
            f"have those damage functions."
        )

    if covered:
        text = (
            f"Over {node_count} gebieden komt de hele watervraag rond"
            + (f" bij {share} van die vraag als aanbod" if share else "")
            + "."
        )
    else:
        coverage = result.coverage_of_category(binding)
        text = (
            f"Over {node_count} gebieden komt de watervraag niet rond"
            + (f" bij {share} van die vraag als aanbod" if share else "")
            + f": categorie {binding} valt als eerste af, op {coverage:.0%} van zijn vraag."
        )
        text += (
            " De inlaten zijn de klem en niet de bron, dus meer water aanvoeren helpt hier "
            "niet - een grotere inlaat wel."
            if capacity_bound
            else " De bron is de klem, dus dit is een rantsoeneringsvraag en geen "
            "kunstwerkvraag."
        )
    if binding is None or not spread:
        return text + (
            " Binnen een categorie is het tekort gelijk verdeeld. Dat is een modelkeuze: de "
            "wet ordent de categorieen en noemt binnen de laagste twee minimalisatie van de "
            "economische maatschappelijke schade, en gelijk verdelen is wat er staat waar wij "
            "die schadefuncties niet hebben."
        )
    low, high = spread
    return text + (
        f" Hoeveel water er per categorie omgaat hangt niet af van hoe je binnen die "
        f"categorie verdeelt; wie het krijgt wel. Verdeel je het tekort gelijk, dan komt "
        f"iedereen in categorie {binding} op {result.coverage_of_category(binding):.0%}; leg "
        f"je het bij de grootste vragers, dan loopt de dekking van {low:.0%} tot {high:.0%}. "
        f"De wet kiest daartussen niet - hij noemt minimalisatie van de economische "
        f"maatschappelijke schade, en die schadefuncties hebben wij niet."
    )


def describe_step_cost_plateau(best, indistinguishable, language: str = "nl") -> str:
    """Wat de twee kostenlezingen samen zeggen, en waarom dat geen vaagheid is.

    De lineaire prijs is een bewuste vuistregelvereenvoudiging met een bekende richting: hij
    onderschat een kleine uitbreiding sterk, want je koopt een gemaal en niet een m3/min. Dat
    stond al als caveat. Wat er niet stond is dat het de RANGORDE verandert - en dat is het
    verschil tussen "een groter gemaal is drie keer goedkoper" en "een groter gemaal en 111
    hectare open water zijn niet van elkaar te onderscheiden".

    Twee lezingen naast elkaar en niet een bredere epsilon op een van de twee: met een factor
    2,7 als slack slikt de band elk pakket en zegt hij niets meer.
    """
    others = [
        package
        for package in indistinguishable
        if set(name for name, value in package.quantities.items() if value > 0)
        != set(name for name, value in best.quantities.items() if value > 0)
    ]
    linear = best.cost / 1e6
    replacement = best.replacement_cost / 1e6

    if language == "en":
        text = (
            f"Priced as an increase the cheapest package costs EUR {linear:.1f} million; "
            f"priced as a replacement - which is what a pumping station really is, you buy "
            f"a station and not a m3/min - it costs EUR {replacement:.1f} million."
        )
        if not others:
            return text + " The ranking does not change under that reading."
        names = ", ".join(
            "/".join(
                _MEASURE_EN.get(name, name)
                for name, value in package.quantities.items()
                if value > 0
            )
            for package in others
        )
        return text + (
            f" Under that reading the ranking changes: {names} become indistinguishable from "
            f"it, because their price bands overlap. Which of them is cheapest is then not "
            f"something this model can tell you - and that is the honest answer, not a "
            f"missing one."
        )

    text = (
        f"Als toename gerekend kost het goedkoopste pakket {linear:.1f} miljoen euro; als "
        f"vervanging gerekend - en dat is wat een gemaal werkelijk is, je koopt een gemaal en "
        f"geen m3/min - kost het {replacement:.1f} miljoen."
    )
    if not others:
        return text + " De rangorde verandert daar niet van."
    names = ", ".join(
        "/".join(name for name, value in package.quantities.items() if value > 0)
        for package in others
    )
    return text + (
        f" In die lezing verandert de rangorde wel: {names} zijn er niet meer van te "
        f"onderscheiden, want hun prijsbanden overlappen. Welke van die pakketten het "
        f"goedkoopst is, kan dit model dan niet zeggen - en dat is het eerlijke antwoord, "
        f"geen ontbrekend antwoord."
    )

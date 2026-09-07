"""Tekstuitvoer van de vuistregeltools.

Twee uitlegbare zinnen per antwoord, in het Nederlands of Engels, en een derde zodra er
standaardwaarden zijn aangenomen. Apart gehouden van de rekenlogica omdat de formulering
afhangt van de status: een onhaalbaar doel verdient een uitleg met het optimum erbij, geen
getal.

De grootheid waar de tools op rekenen is de maximale water*stijging* met maatregel. Eerder
noemden de teksten van bergen en afvoeren datzelfde getal een "waterstandverlaging",
waardoor 210 cm stijging als 210 cm verlaging werd gerapporteerd.
"""

from talk_with_the_engineer.epistemics.uncertainty import (
    MINIMUM_DIGITS,
    supported_digits,
)
from talk_with_the_engineer.core.results import (
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
    "sturing": "bergen, afvoeren of vasthouden",
}
_OTHER_MEASURES_EN = {
    "bergen": "discharge or retention",
    "afvoeren": "store or retention",
    "vasthouden": "store or discharge",
    "aanvoeren": "store or retention",
    "sturing": "store, discharge or retention",
}
_PRICELESS_MEASURES = frozenset({"peilopzet", "aanvoeren", "sturing"})
"""De maatregelen zonder eenheidsprijs; hun bovengrens in een gebied is nooit de prijsband."""

_MEASURE_UNIT = {
    "vasthouden": "ha land",
    "bergen": "ha open water",
    "afvoeren": "m3/s",
    "peilopzet": "m peilopzet",
    "aanvoeren": "m3/s inlaat",
    "sturing": "m peilmarge",
}
"""Eenheid per maatregel, voor zinnen die uit een `quantities`-dict worden gebouwd."""

_PRICELESS_WORD = {
    "peilopzet": ("drooglegging", "drainage depth"),
    "aanvoeren": ("water", "water"),
    "sturing": ("investering en bedrijfsvoering", "investment and operations"),
}
"""Wat een prijsloze maatregel kost in plaats van euro's, als één woord voor in een zin."""

_MEASURE_EN = {
    "bergen": "store",
    "afvoeren": "discharge",
    "vasthouden": "retention",
    "aanvoeren": "supply",
    "sturing": "operational control",
    "peilopzet": "raise target level",
}


def counted(number: int, singular: str, plural: str) -> str:
    """Een aantal met het zelfstandig naamwoord erbij, in het juiste getal.

    Nodig op de systeemtools: die worden met een enkel gebied uitgeprobeerd - zo leert een
    beller ze kennen - en "Over 1 gebieden in 1 topologische lagen" is dan de eerste zin die
    hij leest.
    """
    return f"{number} {singular if number == 1 else plural}"


def _event_phrase(storm, language: str) -> str:
    """Benoem de bui zoals je hem uitspreekt, niet zoals hij in het veld staat.

    Twee soorten bui, want er zijn twee ingangen. Komt de neerslagsom uit de statistiek,
    dan is de terugkeertijd waar je hem aan herkent; geeft de beller de som zelf op, dan is
    er geen terugkeertijd en is de som zelf de enige eerlijke aanduiding. Er dan toch een
    zeldzaamheid bij verzinnen zou de bui een status geven die hij niet heeft.

    Een terugkeertijd kleiner dan een jaar is een frequentie: T = 0,5 betekent gemiddeld
    twee keer per jaar, niet "eens per 0,5 jaar". Zo staat het ook in de STOWA-tabel waar
    deze statistiek uit komt - "die gemiddeld 2 maal per jaar tot gemiddeld eens per 1000
    jaar worden overschreden". En "eens per 1 jaar" is "eens per jaar".

    Hele jaren komen zonder decimaal, want `return_period` is een float sinds 0.5
    bereikbaar moest zijn.
    """
    own_volume = getattr(storm, "rain_volume_mm", None)
    if own_volume is not None:
        return (
            f"a {own_volume:g} mm event"
            if language == "en"
            else f"een bui van {own_volume:g} mm"
        )
    return_period = storm.return_period
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
    """ "ongeveer " als het getal in de tekst merkbaar is afgerond, anders niets.

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


# Alle vijf de eenheden lopen door `_rounded`, en dat is geen stijlregel. Een tak die zijn
# opmaak hardcodeert - `:.2f` op een debiet, bijvoorbeeld - slaat de afgeleide precisie uit
# `supported_digits` over, en dan meldt de zin "2,91 m3/s" waar de spreiding twee cijfers
# toestaat. De discipline zit in `_rounded`; er hoort geen tak langs.
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
        return (
            f"{about}{_rounded(result.magnitude, digits)} ha of additional open water"
        )
    if result.unit == "ha land":
        return f"{about}{_rounded(result.magnitude, digits)} ha of land"
    if result.unit == "m3/s inlaat":
        return (
            f"{about}{_rounded(result.magnitude, digits, 2)} m3/s of additional intake "
            f"capacity"
        )
    if result.unit == "m peilmarge":
        return (
            f"{about}{_rounded(result.magnitude * 100, digits, 0)} cm of level margin"
        )
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
    """Wat er vastzit, wat vrij is en wat niet meedoet - met de herkomst per grens inline.

    Eén zin, en elke grens draagt zijn herkomst bij zijn eigen getal: de onderkant komt uit
    de eis, de bovenkant uit de prijsband, of - bij een prijsloze maatregel - alleen uit de
    zoekgrens, en dan staat er "vanaf" in plaats van een koopgrens. Wat hier niet staat is
    de algemene uitleg van die begrippen: die leeft in het schema en in de handleiding, en
    een les die elke uitvoer herhaalt is ruis voor wie het antwoord al kent.

    Bij `absent` noemt de zin de reden alleen wanneer de aanroeper die gemeten meegeeft
    (`absent_reason`): draagt niet bij, of past niet binnen de prijsband. Zonder meting
    wordt er geen reden geclaimd - uit het gebied alleen is die niet af te lezen, en een
    geclaimde reden zonder meting leest als een feit terwijl het een gok is.
    """
    forced = [r for r in ranges if r.role is MeasureRole.FORCED]
    optional = [r for r in ranges if r.role is MeasureRole.OPTIONAL]
    absent = [r for r in ranges if r.role is MeasureRole.ABSENT]

    def name(measure_range):
        if language == "en":
            return _MEASURE_EN.get(measure_range.name_nl, measure_range.name_nl)
        return measure_range.name_nl

    def bound_phrase(r):
        words, scale = _REGION_UNIT.get(r.unit, (r.unit, 1.0))
        low, high = r.magnitude_min * scale, r.magnitude_max * scale
        digits = supported_digits(high - low, low) or 2
        low_text = f"{round_significant(low, digits):g}"
        high_text = f"{round_significant(high, digits):g}"
        source = getattr(r, "magnitude_max_source", None)
        if source is None:
            # aanroepers zonder herkomst (de kern-`MeasureRange`): prijsloos zonder prijs
            # kan alleen de zoekgrens zijn, geprijsd de prijsband
            source = "zoekgrens" if r.name_nl in _PRICELESS_MEASURES else "prijsband"
        if low_text == high_text:
            # als naamwoordgroep, want de zin begint met "gebruikt ..."
            template = (
                "'{n}' at exactly {v} {u}"
                if language == "en"
                else "'{n}' op precies {v} {u}"
            )
            return template.format(n=name(r), v=low_text, u=words)
        if source == "zoekgrens":
            template = (
                "'{n}' from {lo} {u} up (any size beyond works; searched up to {hi})"
                if language == "en"
                else "'{n}' vanaf {lo} {u} (elke maat daarboven voldoet; gezocht tot {hi})"
            )
            return template.format(n=name(r), lo=low_text, hi=high_text, u=words)
        template = (
            "'{n}' from {lo} (the requirement) to {hi} {u} (the price band)"
            if language == "en"
            else "'{n}' van {lo} (de eis) tot {hi} {u} (de prijsband)"
        )
        return template.format(n=name(r), lo=low_text, hi=high_text, u=words)

    def listing(items):
        names = [name(item) for item in items]
        if len(names) == 1:
            return names[0]
        joiner = " and " if language == "en" else " en "
        return ", ".join(names[:-1]) + joiner + names[-1]

    parts = []
    if forced:
        head = (
            "Every equally good package uses "
            if language == "en"
            else "Elk even goed pakket gebruikt "
        )
        joiner = " and " if language == "en" else " en "
        parts.append(head + joiner.join(bound_phrase(r) for r in forced))
    if optional:
        head = "optional: " if language == "en" else "als keuze kan "
        tail = "" if language == "en" else " erbij"
        parts.append(head + ", ".join(bound_phrase(r) for r in optional) + tail)
    if absent:
        # met de gemeten reden erbij zodra de aanroeper die meegeeft; zonder meting wordt
        # er geen reden geclaimd
        too_dear = [
            r for r in absent if getattr(r, "absent_reason", None) == "buiten_prijsband"
        ]
        no_help = [
            r for r in absent if getattr(r, "absent_reason", None) == "draagt_niet_bij"
        ]
        unmeasured = [r for r in absent if getattr(r, "absent_reason", None) is None]
        if too_dear:
            parts.append(
                f"{listing(too_dear)} would contribute but "
                + ("does" if len(too_dear) == 1 else "do")
                + " not fit the price band of the cheapest package"
                if language == "en"
                else f"{listing(too_dear)} "
                + (
                    "draagt wel bij maar past"
                    if len(too_dear) == 1
                    else "dragen wel bij maar passen"
                )
                + " niet binnen de prijsband van het goedkoopste pakket"
            )
        if no_help:
            parts.append(
                f"{listing(no_help)} "
                + ("does" if len(no_help) == 1 else "do")
                + " not improve any stated requirement"
                if language == "en"
                else f"{listing(no_help)} "
                + ("verbetert" if len(no_help) == 1 else "verbeteren")
                + " geen enkele gestelde eis"
            )
        if unmeasured:
            parts.append(
                f"{listing(unmeasured)} take"
                + ("s" if len(unmeasured) == 1 else "")
                + " no part here"
                if language == "en"
                else f"{listing(unmeasured)} "
                + ("doet" if len(unmeasured) == 1 else "doen")
                + " hier niet mee"
            )
    if not parts:
        return ""
    return "; ".join(parts) + "."


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
    result: SolveResult, storm, language: str, digits: int | None = None
) -> str:
    """Uitleg bij een inverse berekening: hoeveel maatregel is er nodig?

    `storm` is het hele invoermodel en niet de terugkeertijd alleen, want een bui met een
    eigen neerslagsom heeft er geen. Zie `_event_phrase`.
    """
    event = _event_phrase(storm, language)
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
    het is uit een exact antwoord niet af te lezen. Wie 3800 ha opgeeft, krijgt een
    maatvoering die 44 % meer kost dan 2645 ha voor een 5 cm hogere stijging; zonder deze
    zin wijst er niets op dat betere punt.
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
    result: SolveResult, storm, language: str, digits: int | None = None
) -> str:
    """Uitleg bij een voorwaartse berekening: wat levert deze maatvoering op?"""
    event = _event_phrase(storm, language)
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


def _ceiling_clause(result, language: str) -> str:
    """De zin die erbij hoort zodra het bodemplafond de klem is.

    Zonder deze zin adviseert het antwoord bergen of vasthouden waar geen van beide helpt:
    knijpt de bodem de vraag af, dan komt het water niet bij het gewas en verandert een
    grotere voorraad daar niets aan. Leeg zodra het plafond niet knelt.
    """
    if getattr(result, "unreachable_mm", 0.0) <= 0.0:
        return ""
    if language == "en":
        return (
            f" Of that, {result.unreachable_mm:.0f} mm does not reach the root zone at all: "
            f"the soil passes at most {result.soil_transfer_mm_per_day:.2f} mm/day "
            f"({result.binding_link}), so a larger intake and more storage do not change it - "
            "submerged drainage or subirrigation does."
        )
    return (
        f" Daarvan bereikt {result.unreachable_mm:.0f} mm de wortelzone niet: de bodem laat "
        f"ten hoogste {result.soil_transfer_mm_per_day:.2f} mm/dag door "
        f"({result.binding_link}), dus een grotere inlaat en meer berging veranderen daar "
        "niets aan - onderwaterdrainage of subirrigatie wel."
    )


def describe_supply_inverse(result, input, language: str) -> str:
    """Uitleg bij de inverse: hoeveel inlaatcapaciteit is er nodig?

    Het tekort krijgt drie cijfers en niet zijn volle precisie. Het is niet altijd meer een
    getal dat de beller heeft getypt: komt het uit de droogtestatistiek, dan is het een
    deling - 268,6 mm over 183 dagen - en "1.46776 mm/dag" suggereert dan een nauwkeurigheid
    die noch de statistiek noch het venster heeft.
    """
    per_ha = result.supply_capacity_m3_per_sec * 1000 / input.area_ha
    deficit = input.deficit_mm_per_day
    days = input.length_days

    if language == "en":
        if result.status is SolveStatus.NO_MEASURE_NEEDED:
            return (
                f"No intake capacity is needed: a deficit of {deficit:.3g} mm/day over "
                f"{days} days asks {result.demand_mm:.0f} mm, and the "
                f"{result.buffer_mm:.0f} mm of storage below the target level already "
                f"covers it."
            )
        if result.status is SolveStatus.ACTION_INFEASIBLE:
            return (
                f"A deficit of {deficit:.3g} mm/day over {days} days cannot be covered by "
                f"intake alone: even {per_ha:.2f} l/s/ha leaves {result.shortfall_mm:.0f} "
                f"mm of demand unmet."
                + (
                    _ceiling_clause(result, language)
                    or " Combine it with store or retention."
                )
            )
        return (
            f"To cover a deficit of {deficit:.3g} mm/day over {days} days, the intake needs "
            f"{per_ha:.2f} l/s/ha ({result.supply_capacity_m3_per_sec:.2f} m3/s). That "
            f"delivers {result.supplied_mm:.0f} mm; the remaining {result.buffer_mm:.0f} "
            f"mm comes from storage below the target level, drawing it down "
            f"{result.drawdown_m * 100:.0f} cm."
        )

    if result.status is SolveStatus.NO_MEASURE_NEEDED:
        return (
            f"Er is geen inlaatcapaciteit nodig: een tekort van {deficit:.3g} mm/dag over "
            f"{days} dagen vraagt {result.demand_mm:.0f} mm, en de "
            f"{result.buffer_mm:.0f} mm berging onder het streefpeil dekt dat al."
        )
    if result.status is SolveStatus.ACTION_INFEASIBLE:
        return (
            f"Een tekort van {deficit:.3g} mm/dag over {days} dagen is met alleen aanvoeren "
            f"niet te dekken: zelfs {per_ha:.2f} l/s/ha laat {result.shortfall_mm:.0f} mm "
            f"vraag onvervuld."
            + (
                _ceiling_clause(result, language)
                or " Combineer met bergen of vasthouden."
            )
        )
    return (
        f"Om een tekort van {deficit:.3g} mm/dag over {days} dagen te dekken is een inlaat "
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
                f"An intake of {per_ha:.2f} l/s/ha covers a deficit of {deficit:.3g} mm/day "
                f"over {days} days: it delivers {result.supplied_mm:.0f} of the "
                f"{result.demand_mm:.0f} mm demand and {when}."
            )
        return (
            f"An intake of {per_ha:.2f} l/s/ha delivers {result.supplied_mm:.0f} of the "
            f"{result.demand_mm:.0f} mm that a deficit of {deficit:.3g} mm/day over {days} "
            f"days asks; {when}, and {result.shortfall_mm:.0f} mm of demand stays unmet. "
            f"The level drops {result.drawdown_m * 100:.0f} cm."
            + _ceiling_clause(result, language)
        )

    if covered:
        return (
            f"Een inlaat van {per_ha:.2f} l/s/ha dekt een tekort van {deficit:.3g} mm/dag "
            f"over {days} dagen: hij levert {result.supplied_mm:.0f} van de "
            f"{result.demand_mm:.0f} mm vraag, en {when}."
        )
    return (
        f"Een inlaat van {per_ha:.2f} l/s/ha levert {result.supplied_mm:.0f} van de "
        f"{result.demand_mm:.0f} mm die een tekort van {deficit:.3g} mm/dag over {days} "
        f"dagen vraagt; {when}, en {result.shortfall_mm:.0f} mm vraag blijft onvervuld. "
        f"De waterstand zakt {result.drawdown_m * 100:.0f} cm uit."
        + _ceiling_clause(result, language)
    )


def append_source(text: str, result, input, language: str) -> str:
    """Zet de bron achter de uitleg: waar hij vandaan komt, en wanneer hij leeg is.

    Twee zinnen, en ze bestaan omdat het bronvolume uit de statistiek kan komen. Typt de
    beller het getal zelf, dan weet hij wat hij heeft opgegeven; komt het uit een opzoeking,
    dan verandert het antwoord met de herhaaltijd van de droogte zonder dat daar iets van te
    zien is.

    De tweede zin is de belangrijkste, want zonder hem leest een onhaalbaar antwoord verkeerd.
    `describe_supply_inverse` zegt bij `ACTION_INFEASIBLE` "zelfs 5,00 l/s/ha laat 30 mm
    onvervuld - combineer met bergen of vasthouden". Dat is het juiste advies als de INLAAT de
    klem is en het verkeerde als de BRON het is: dan helpt geen enkel kunstwerk, en gaat het
    gesprek over waar het water vandaan moet komen.
    """
    parts = [text]
    availability = getattr(input, "source_availability", None)
    if availability is not None:
        percentage = availability.fraction * 100
        if language == "en":
            parts.append(
                f"The source volume comes from the same statistic as the drought: at a "
                f"{input.drought_return_period}-year drought in "
                f"{input.drought_region.replace('_', ' ')} the {input.source_river} carries "
                f"{percentage:.0f} % of a normal year."
            )
        else:
            parts.append(
                f"Het bronvolume komt uit dezelfde statistiek als de droogte: bij een "
                f"{input.drought_return_period}-jaarlijkse droogte in "
                f"{input.drought_region.replace('_', ' ')} levert de {input.source_river} "
                f"{percentage:.0f} % van een normaal jaar."
            )

    days = result.days_until_source_empty
    if days != float("inf"):
        binding = result.shortfall_mm > 0
        if language == "en":
            parts.append(
                f"The source runs dry after {days:.0f} of the {input.length_days} days"
                + (
                    ", so the binding constraint is availability and not the intake: more "
                    "capacity does not help here."
                    if binding
                    else "."
                )
            )
        else:
            parts.append(
                f"De bron is na {days:.0f} van de {input.length_days} dagen leeg"
                + (
                    ", dus de klem zit in de beschikbaarheid en niet in de inlaat: meer "
                    "capaciteit helpt hier niet."
                    if binding
                    else "."
                )
            )
    return " ".join(parts)


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
    # dezelfde ondergrens als in de zin ervoor: "reken op 10 tot 100 ha" naast een antwoord
    # van 12,71 ha suggereert een ander bereik dan "reken op 13 tot 130 ha". Zie
    # `MINIMUM_DIGITS`.
    digits = MINIMUM_DIGITS
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
    coverage_of_category=None,
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
    # De dekking komt van buiten wanneer de beller hem meegeeft, want dan is hij gemeten
    # tegen de vraag die de gebieden ECHT hebben: hun eigen voorraad gaat als een lagere
    # vraag de rekenkern in, en de dekking daarvan is er een van de restvraag.
    coverage_of_category = coverage_of_category or result.coverage_of_category
    # boven de volle vraag is een percentage misleidend: "bij 314 % van de vraag als aanbod"
    # leest als een fout terwijl het betekent dat de bron ruim is en de inlaten de klem zijn
    if theta is None or theta >= 1.0:
        share = ""
    else:
        share = f"{theta:.0%}"

    if language == "en":
        if covered:
            text = (
                f"Across {counted(node_count, 'area', 'areas')} the whole demand is met"
                + (f" at {share} of it available" if share else "")
                + "."
            )
        else:
            coverage = coverage_of_category(binding)
            text = (
                f"Across {counted(node_count, 'area', 'areas')} the demand is not met"
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
            f"{coverage_of_category(binding):.0%}; place it on the largest users and "
            f"coverage runs from {low:.0%} to {high:.0%}. The law does not choose between "
            f"those - it points to minimising economic and societal damage, and we do not "
            f"have those damage functions."
        )

    if covered:
        text = (
            f"Over {counted(node_count, 'gebied', 'gebieden')} komt de hele watervraag rond"
            + (f" bij {share} van die vraag als aanbod" if share else "")
            + "."
        )
    else:
        coverage = coverage_of_category(binding)
        text = (
            f"Over {counted(node_count, 'gebied', 'gebieden')} komt de watervraag niet rond"
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
        f"iedereen in categorie {binding} op {coverage_of_category(binding):.0%}; leg "
        f"je het bij de grootste vragers, dan loopt de dekking van {low:.0%} tot {high:.0%}. "
        f"De wet kiest daartussen niet - hij noemt minimalisatie van de economische "
        f"maatschappelijke schade, en die schadefuncties hebben wij niet."
    )


def describe_step_cost_plateau(best, indistinguishable, language: str = "nl") -> str:
    """De vervangingslezing, alleen wanneer hij de rangorde verandert.

    Lineair rekenen is een bewuste vuistregelvereenvoudiging met een bekende richting: het
    onderschat een kleine uitbreiding, want je koopt een gemaal en geen m3/s. Meestal
    verandert dat niets aan de rangorde, en dan is er niets te zeggen - stilte, geen vaste
    zin die elke uitvoer vult. Verandert de rangorde wel, dan is dat het melden waard, met
    de getallen erbij en zonder verzonnen zekerheid over welk pakket dan wint.
    """
    others = [
        package
        for package in indistinguishable
        if set(name for name, value in package.quantities.items() if value > 0)
        != set(name for name, value in best.quantities.items() if value > 0)
    ]
    if not others:
        return ""
    replacement = best.replacement_cost / 1e6
    names = ", ".join(
        "/".join(
            (_MEASURE_EN.get(name, name) if language == "en" else name)
            for name, value in package.quantities.items()
            if value > 0
        )
        for package in others
    )
    if language == "en":
        return (
            f"Priced as a replacement - a pumping station is bought whole, not per m3/s - "
            f"this package costs EUR {replacement:.1f} million and {names} "
            f"{'is' if len(others) == 1 else 'are'} then indistinguishable from it: the "
            f"price bands overlap, so which one is cheapest is not something this model "
            f"can say."
        )
    werkwoord = "is" if len(others) == 1 else "zijn"
    return (
        f"Als vervanging gerekend - een gemaal koop je als geheel, niet per m3/s - kost "
        f"dit pakket {replacement:.1f} miljoen euro en {werkwoord} {names} er niet van te "
        f"onderscheiden: de prijsbanden overlappen, dus welke de goedkoopste is kan dit "
        f"model dan niet zeggen."
    )


# --- de pakketzoeker: drie statussen, drie sjablonen, elke zin een getal --------------


def _requirement_clauses(input, language: str) -> str:
    """De gestelde eisen als zinsdeel, elk met zijn getal."""
    clauses = []
    if input.max_dh_total_m is not None:
        clauses.append(
            f"stay below {input.max_dh_total_m * 100:.0f} cm"
            if language == "en"
            else f"onder de {input.max_dh_total_m * 100:.0f} cm te blijven"
        )
    if input.min_storage_mm is not None:
        clauses.append(
            f"keep at least {input.min_storage_mm:g} mm of storage below target level"
            if language == "en"
            else f"minstens {input.min_storage_mm:g} mm voorraad onder streefpeil te houden"
        )
    if input.max_shortfall_mm is not None:
        clauses.append(
            f"keep the unmet demand under {input.max_shortfall_mm:g} mm"
            if language == "en"
            else f"het onvervulde tekort onder {input.max_shortfall_mm:g} mm te houden"
        )
    joiner = " and " if language == "en" else " en "
    return joiner.join(clauses)


def measure_amount(name: str, magnitude: float) -> str:
    """Een maatvoering in de leesbare eenheid van die maatregel: 0,5714 m wordt "57 cm"."""
    unit = _MEASURE_UNIT.get(name, "")
    words, scale = _REGION_UNIT.get(unit, (unit, 1.0))
    return f"{round_significant(magnitude * scale, 2):g} {words}"


def _measures_phrase(quantities: dict, language: str) -> str:
    """De ingezette maatregelen met hun maatvoering, in leesbare eenheden."""
    parts = []
    for name, magnitude in sorted(quantities.items()):
        if magnitude <= 0:
            continue
        shown = _MEASURE_EN.get(name, name) if language == "en" else name
        parts.append(f"'{shown}' {measure_amount(name, magnitude)}")
    joiner = " and " if language == "en" else " en "
    return joiner.join(parts)


def describe_package_found(input, best) -> str:
    """De vraag en het antwoord in één zin: eisen, pakket, prijs, en wat geen prijs heeft."""
    language = input.language
    event = _event_phrase(input, language)
    requirements = _requirement_clauses(input, language)
    measures = _measures_phrase(best.quantities, language)

    priceless = [name for name in best.priceless]
    if priceless:
        # met de maatvoering erbij: de bijzin hoort bij dit antwoord, niet bij elk antwoord
        def with_amount(name):
            shown = _MEASURE_EN.get(name, name) if language == "en" else name
            unit = _MEASURE_UNIT.get(name, "")
            words, scale = _REGION_UNIT.get(unit, (unit, 1.0))
            amount = round_significant(best.quantities.get(name, 0.0) * scale, 2)
            return f"'{shown}' ({amount:g} {words})"

        shown = [with_amount(name) for name in priceless]
        words = sorted(
            {
                _PRICELESS_WORD[name][1 if language == "en" else 0]
                for name in priceless
                if name in _PRICELESS_WORD
            }
        )
        joiner = " and " if language == "en" else " en "
        priceless_names = joiner.join(shown)
        priceless_words = joiner.join(words)

    if best.cost > 0:
        low, high = best.priced_cost_range
        band = (
            f" ({low / 1e6:.1f} {'to' if language == 'en' else 'tot'} {high / 1e6:.1f} "
            f"{'over the priced part' if language == 'en' else 'over het geprijsde deel'})"
            if high > low
            else ""
        )
        if language == "en":
            tail = f", together EUR {best.cost / 1e6:.1f} million{band}"
            if priceless:
                tail += f"; {priceless_names} costs no euros but {priceless_words}"
        else:
            tail = f", samen {best.cost / 1e6:.1f} miljoen euro{band}"
            if priceless:
                kost = "kost" if len(priceless) == 1 else "kosten"
                tail += f"; {priceless_names} {kost} geen euro's maar {priceless_words}"
    else:
        # niets in dit pakket heeft een bedrag; "0,0 miljoen" zou als gratis lezen
        tail = (
            f" - no investment amount; what {priceless_names} costs is "
            f"{priceless_words}, see `priceless`"
            if language == "en"
            else f" - zonder investeringsbedrag; wat {priceless_names} kost is "
            f"{priceless_words}, zie `priceless`"
        )

    if language == "en":
        return f"To {requirements} in {event}: {measures}{tail}."
    return f"Om bij {event} {requirements}: {measures}{tail}."


def describe_no_measure_needed(input, best, dh_reference_m: float) -> str:
    """Het gebied haalt de eisen al - met per eis het getal en de grens ernaast."""
    language = input.language
    event = _event_phrase(input, language)
    clauses = []
    if input.max_dh_total_m is not None:
        clauses.append(
            f"the water level rises {dh_reference_m * 100:.0f} cm "
            f"(limit {input.max_dh_total_m * 100:.0f} cm)"
            if language == "en"
            else f"de waterstand stijgt {dh_reference_m * 100:.0f} cm "
            f"(eis {input.max_dh_total_m * 100:.0f} cm)"
        )
    if input.min_storage_mm is not None:
        clauses.append(
            f"storage is {round_significant(best.storage_mm, 2):g} mm "
            f"(requirement {input.min_storage_mm:g} mm)"
            if language == "en"
            else f"de voorraad is {round_significant(best.storage_mm, 2):g} mm "
            f"(eis {input.min_storage_mm:g} mm)"
        )
    if input.max_shortfall_mm is not None and best.shortfall_mm is not None:
        clauses.append(
            f"the unmet demand is {round_significant(best.shortfall_mm, 2):g} mm "
            f"(requirement {input.max_shortfall_mm:g} mm)"
            if language == "en"
            else f"het onvervulde tekort is {round_significant(best.shortfall_mm, 2):g} mm "
            f"(eis {input.max_shortfall_mm:g} mm)"
        )
    listed = "; ".join(clauses)
    if language == "en":
        return (
            f"In {event} the area already meets the requirements: {listed}. "
            f"No measure is needed."
        )
    return (
        f"Bij {event} haalt het gebied de eisen al: {listed}. "
        f"Er is geen maatregel nodig."
    )


_ALONE_NL = {
    "inundatie": (
        "de inundatie-eis van {req:g} cm kan op zichzelf tot {bound:g} cm worden gebracht",
        "de inundatie-eis van {req:g} cm is ook op zichzelf niet haalbaar: lager dan "
        "{bound:g} cm komt de waterstand met deze maatregelen niet",
    ),
    "voorraad": (
        "de voorraadeis van {req:g} mm kan op zichzelf tot {bound:g} mm worden gebracht",
        "de voorraadeis van {req:g} mm is ook op zichzelf niet haalbaar: meer dan "
        "{bound:g} mm voorraad maken deze maatregelen niet",
    ),
    "tekort": (
        "de tekort-eis van {req:g} mm kan op zichzelf tot {bound:g} mm worden gebracht",
        "de tekort-eis van {req:g} mm is ook op zichzelf niet haalbaar: onder {bound:g} mm "
        "komt het tekort met deze maatregelen niet",
    ),
}
_ALONE_EN = {
    "inundatie": (
        "the inundation limit of {req:g} cm can be brought to {bound:g} cm on its own",
        "the inundation limit of {req:g} cm is infeasible even on its own: these measures "
        "cannot bring the water level below {bound:g} cm",
    ),
    "voorraad": (
        "the storage requirement of {req:g} mm can be brought to {bound:g} mm on its own",
        "the storage requirement of {req:g} mm is infeasible even on its own: these "
        "measures cannot create more than {bound:g} mm",
    ),
    "tekort": (
        "the shortfall limit of {req:g} mm can be brought to {bound:g} mm on its own",
        "the shortfall limit of {req:g} mm is infeasible even on its own: these measures "
        "cannot bring the shortfall below {bound:g} mm",
    ),
}


def describe_infeasible(input, misses, examined: int) -> str:
    """Waarom er geen pakket is - met per eis de echte grens, en de conflictdiagnose.

    De grens per as komt uit een eigen doorrekening die de as zelf optimaliseert
    (`best_on_axis`), en is dus hard: verder komt het met deze maatregelen niet. Is elke
    eis op zichzelf haalbaar en is er toch geen pakket, dan conflicteren de eisen - en dat
    is een ander gesprek dan "het kan niet", want een van de eisen versoepelen kan dan
    genoeg zijn.
    """
    language = input.language
    table = _ALONE_EN if language == "en" else _ALONE_NL
    clauses = []
    for miss in misses:
        scale = 100.0 if miss.requirement == "inundatie" else 1.0
        feasible_text, infeasible_text = table[miss.requirement]
        template = feasible_text if miss.alone_feasible else infeasible_text
        clauses.append(
            template.format(
                req=round_significant(miss.required * scale, 2),
                bound=round_significant(miss.achievable_alone * scale, 2),
            )
        )
    listed = "; ".join(clauses)
    conflict = bool(misses) and all(miss.alone_feasible for miss in misses)
    if language == "en":
        text = (
            f"None of the {examined} combinations examined meets the requirements at "
            f"the same time"
        )
        if conflict:
            text += " - the requirements conflict"
        return f"{text}: {listed}." if listed else f"{text}."
    text = f"Geen van de {examined} onderzochte combinaties haalt de eisen tegelijk"
    if conflict:
        text += " - de eisen conflicteren"
    return f"{text}: {listed}." if listed else f"{text}."

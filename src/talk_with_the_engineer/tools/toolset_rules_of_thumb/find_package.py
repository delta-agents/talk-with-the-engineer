"""De pakketzoeker als tool: welk maatregelpakket haalt de eisen, en wat kost het.

De tien maatregeltools rekenen een gegeven maatregel door. Deze tool stelt de vraag die een
waterbeheerder werkelijk heeft - welke combinatie moet ik nemen - en beantwoordt hem in een
aanroep, in plaats van de agent tien aanroepen te laten componeren.

Wat er teruggegeven wordt is bewust het GEBIED en niet alleen het punt. De maatvoering van
een optimum is de minst robuuste uitspraak die uit een optimalisatie komt: de rangorde van
maatregelen blijft staan waar de hectares een factor honderd bewegen. Daarom staan naast het
goedkoopste pakket de niet te onderscheiden alternatieven, de vrije maatvoering per
maatregel, en de maatregelen die geen prijs hebben.
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
    model_caveats,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.optimize import (
    MeasureQuantity,
    MeasureRangeReading,
    OptimizeInput,
    OptimizeOutput,
    PackageReading,
    RequirementMiss,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    PricelessPost,
    SolveStatus,
    round_significant,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    append_assumptions,
    describe_region,
    describe_step_cost_plateau,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.optimize import (
    DEFAULT_ACTIONS,
    Constraints,
    cost_epsilon,
    indistinguishable_under_step_cost,
    optimize,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    simulate,
    storm_shape,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.supply import Deficit
from talk_with_the_engineer.utils.logging_utils import log_tool_call

PRICELESS_COST = {
    "peilopzet": (
        "Drooglegging: een hoger streefpeil betekent landbouwschade en functiebeperking, en "
        "dat is een verdringingsvraagstuk en geen investeringspost. In dit antwoord betaal "
        "je hem bovendien al in de waterstand - de opzet telt mee in de gerapporteerde "
        "stijging, dus elke centimeter opzet is een centimeter minder marge tot inundatie."
    ),
    "aanvoeren": (
        "Het water, niet het kunstwerk. Wat aanvoer in een tekort kost is een verdelingsvraag "
        "- de verdringingsreeks rantsoeneert landelijk - en een bedrag verzinnen zou hier "
        "erger zijn dan geen bedrag."
    ),
}
"""Wat een prijsloze maatregel in plaats van euro's kost.

Op de maatregelen die de ZOEKER kiest, en niet op de peilband die de beller opgeeft: welke
post hier hoort, blijkt pas uit het gekozen pakket.
"""

REQUIREMENTS = (
    ("max_dh_total_m", "inundatie", lambda package: package.dh_total_m, 1),
    ("min_storage_mm", "voorraad", lambda package: package.storage_mm, -1),
    ("max_shortfall_mm", "tekort", lambda package: package.shortfall_mm, 1),
)
"""De drie eisen: invoerveld, naam in de uitvoer, waar hij in een pakket te lezen valt, en
het teken dat van die uitlezing een overschrijding maakt.

Een tabel en geen keten van if/elif op de veldnaam: de eis, zijn label en zijn uitlezing horen
bij elkaar en moeten op een plek staan, anders raken ze los zodra er een vierde eis bij komt.
`sign * (uitlezing - eis)` is positief zodra de eis wordt gemist, in beide richtingen - de
voorraadeis is een ondergrens en de andere twee zijn bovengrenzen.
"""


def _constraints(input: OptimizeInput) -> Constraints:
    return Constraints(**{field: getattr(input, field) for field, *_ in REQUIREMENTS})


def _deficit(input: OptimizeInput) -> Deficit | None:
    """De droogte zoals de rekenkern hem verwacht, of geen droogte.

    Zonder tekort is er niets om een tekort-eis op te meten, en dan blijft aanvoeren inert:
    de statische voorraadeis leest een inlaat niet.
    """
    if input.deficit_mm_per_day is None:
        return None
    return Deficit(
        deficit_mm_per_day=input.deficit_mm_per_day,
        length_days=input.length_days,
    )


def _unit_of(name_nl: str) -> str:
    return next(action.unit for action in DEFAULT_ACTIONS if action.name_nl == name_nl)


def _others_than(best, packages) -> list:
    """De pakketten die een ANDERE maatregelmix zijn dan het goedkoopste.

    Het goedkoopste pakket zit zelf in het gebied dat eromheen wordt gemeld, en het staat al
    in `best`. Wat een beller wil weten is wat er NAAST dat pakket even goed is; een lijst die
    met een kopie van het antwoord begint, verbergt precies dat.
    """
    chosen = {name for name, value in best.quantities.items() if value > 0}
    return [
        package
        for package in packages
        if {name for name, value in package.quantities.items() if value > 0} != chosen
    ]


def _reading(package) -> PackageReading:
    """Een pakket zoals de tool het rapporteert: alleen de maatregelen die erin zitten.

    Afgerond op significante cijfers, want de vraag is welke maatregelen het zijn en in welke
    ordegrootte - niet op welke bit de zoeker uitkwam.
    """
    return PackageReading(
        measures=[
            MeasureQuantity(
                name_nl=name,
                unit=_unit_of(name),
                magnitude=round_significant(magnitude),
            )
            for name, magnitude in sorted(package.quantities.items())
            if magnitude > 0
        ],
        cost=package.cost,
        cost_range=package.cost_range,
        replacement_cost=package.replacement_cost,
        binding=list(package.binding),
        priceless=list(package.priceless),
        dh_total_m=package.dh_total_m,
        storage_mm=package.storage_mm,
        shortfall_mm=package.shortfall_mm,
        feasible=package.feasible,
    )


def _missed(input: OptimizeInput, packages) -> list[RequirementMiss]:
    """Per eis de kleinste overschrijding over alle onderzochte combinaties.

    Het antwoord "het kan niet" hoort net zo navolgbaar te zijn als "het kan": zonder dit
    getal weet een beller niet of hij twee centimeter of twee meter tekortkomt, en dus ook
    niet of een soepelere eis of een heel ander plan het gesprek is.

    Per eis afzonderlijk, dus twee overschrijdingen kunnen van twee verschillende combinaties
    komen. Ze zijn daarom niet bij elkaar op te tellen tot de afstand van een pakket; wat er
    staat is per eis de dichtstbijzijnde die er is.
    """
    misses = []
    for field, label, reading_of, sign in REQUIREMENTS:
        required = getattr(input, field)
        if required is None:
            continue
        readings = [
            reading_of(package)
            for package in packages
            if reading_of(package) is not None
        ]
        if not readings:
            continue
        reached = min(readings, key=lambda value: sign * (value - required))
        smallest = sign * (reached - required)
        if smallest <= 0:
            # Deze eis is wel te halen; hij is niet de reden dat er geen pakket is.
            continue
        misses.append(
            RequirementMiss(
                requirement=label,
                required=required,
                reached=reached,
                missed_by=smallest,
            )
        )
    return misses


def _priceless_posts(package) -> list[PricelessPost]:
    """De prijsloze maatregelen in dit pakket, met wat ze in plaats van euro's kosten."""
    return [
        PricelessPost(
            topic=name,
            magnitude=f"{round_significant(package.quantities[name]):g} {_unit_of(name)}",
            what_it_costs=PRICELESS_COST[name],
        )
        for name in package.priceless
        if name in PRICELESS_COST
    ]


def _describe_no_package(input, misses) -> str:
    """Waarom er geen pakket is, en hoeveel het scheelt."""
    listed = ", ".join(
        f"{miss.requirement} komt {round_significant(miss.missed_by):g} tekort"
        for miss in misses
    )
    if input.language == "en":
        text = (
            "No combination of these five measures meets the requirements at the same "
            "time."
        )
        if listed:
            text += f" Closest miss: {listed}."
        return text
    text = "Geen enkele combinatie van deze vijf maatregelen haalt de eisen tegelijk."
    if listed:
        text += f" Het scheelt het minst op: {listed}."
    return text


def _describe(result, indistinguishable, input, assumptions, misses) -> str:
    """De zinnen bij dit antwoord: het gebied, de twee kostenlezingen, en de aannames."""
    language = input.language
    if result.best is None:
        return append_assumptions(
            _describe_no_package(input, misses), assumptions, language
        )

    if not any(magnitude > 0 for magnitude in result.best.quantities.values()):
        # Zonder maatregel in het pakket zeggen "deze maatregelen dragen niet bij" en "dit
        # pakket kost nul" allebei het verkeerde: het gebied haalt de eis al zoals het er nu
        # voor staat, en dat is het hele antwoord.
        text = (
            "The area already meets the requirements as it stands; no measure is needed. "
            "Check whether the requirement is the one you meant before reporting this."
            if language == "en"
            else "Het gebied haalt de eisen al zoals het er nu voor staat; er is geen "
            "maatregel nodig. Ga na of de eis is wat je bedoelde voordat je dit doorgeeft."
        )
        return append_assumptions(text, assumptions, language)

    parts = [describe_region(result.ranges, language)]
    if result.best.cost > 0:
        parts.append(
            describe_step_cost_plateau(result.best, indistinguishable, language)
        )
    else:
        # De twee kostenlezingen zouden hier "0,0 miljoen euro" melden, en dat leest als
        # gratis. Een pakket zonder geprijsde maatregel HEEFT geen bedrag: wat het kost staat
        # in `priceless`, en dat is de enige eerlijke zin op deze plek.
        listed = ", ".join(result.best.priceless)
        parts.append(
            f"This package carries no price tag at all: {listed} costs no euros. What it "
            "costs instead is in `priceless`; reporting it as cheap without that post "
            "presents it as free."
            if language == "en"
            else f"Dit pakket heeft helemaal geen bedrag: {listed} kost geen euro's. Wat het "
            "in plaats daarvan kost staat in `priceless`; zonder die post doorgeven "
            "presenteert het als gratis."
        )
    return append_assumptions(
        " ".join(part for part in parts if part), assumptions, language
    )


@log_tool_call
async def find_package_given_protection(ctx, input: OptimizeInput) -> OptimizeOutput:
    """Welk maatregelpakket haalt de gestelde eisen, en wat kost het?

    Zoekt over alle combinaties van de vijf maatregelen - vasthouden, bergen, afvoeren,
    peilopzet en aanvoeren - en geeft het goedkoopste pakket terug plus het gebied eromheen.
    """
    state = PolderState.from_water_system_input(input)
    constraints = _constraints(input)
    deficit = _deficit(input)

    result = optimize(state, input, constraints, deficit=deficit)

    best = result.best
    indistinguishable = indistinguishable_under_step_cost(result)
    assumptions = assumed_defaults(input)

    misses = [] if best is not None else _missed(input, result.packages)
    if best is None:
        # De zoektocht is altijd volledig - alle combinaties van de vijf maatregelen -
        # dus "geen pakket" betekent hier werkelijk: geen enkele combinatie haalt het.
        status = SolveStatus.PROBLEM_INFEASIBLE
    elif not any(magnitude > 0 for magnitude in best.quantities.values()):
        status = SolveStatus.NO_MEASURE_NEEDED
    else:
        status = SolveStatus.EXACT

    reference = simulate(state, input)
    data = {
        **storm_shape(reference, input),
        "requirements_set": list(input.requirements_set),
        "mixes_examined": len(result.packages),
        "dh_without_measure_m": reference.dh_max_m,
        "deficit_mm_per_day": input.deficit_mm_per_day,
        "cumulative_deficit_mm": input.cumulative_deficit_mm,
        "length_days": input.length_days if deficit else None,
    }

    return OptimizeOutput(
        data=data,
        description=_describe(result, indistinguishable, input, assumptions, misses),
        status=status,
        best=None if best is None else _reading(best),
        near_optimal=[
            _reading(package)
            for package in (
                [] if best is None else _others_than(best, result.near_optimal)
            )
        ],
        cost_epsilon=0.0 if best is None else cost_epsilon(best),
        ranges=[
            MeasureRangeReading(
                name_nl=measure.name_nl,
                unit=measure.unit,
                magnitude_min=round_significant(measure.magnitude_min),
                magnitude_max=round_significant(measure.magnitude_max),
                role=measure.role,
            )
            for measure in result.ranges
        ],
        indistinguishable_as_replacement=[
            _reading(package)
            for package in (
                [] if best is None else _others_than(best, indistinguishable)
            )
        ],
        missed=misses,
        packages=(
            [_reading(package) for package in result.packages] if input.detail else []
        ),
        assumptions=assumptions,
        caveats=model_caveats(input, has_cost=best is not None and best.cost > 0),
        priceless=[] if best is None else _priceless_posts(best),
    )

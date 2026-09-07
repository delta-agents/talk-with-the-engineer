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

from talk_with_the_engineer.epistemics.assumptions import assumed_defaults
from talk_with_the_engineer.epistemics.caveats import model_caveats
from talk_with_the_engineer.epistemics.priceless import priceless_posts
from talk_with_the_engineer.interface.schemas.optimize import (
    MeasureQuantity,
    MeasureRangeReading,
    OptimizeInput,
    OptimizeOutput,
    PackageReading,
    RequirementMiss,
)
from talk_with_the_engineer.core.results import (
    MeasureRole,
    SolveStatus,
    round_significant,
)
from talk_with_the_engineer.interface.schemas.output import PricelessPost
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.interface.descriptions import (
    append_assumptions,
    describe_infeasible,
    describe_no_measure_needed,
    describe_package_found,
    describe_region,
    describe_step_cost_plateau,
    measure_amount,
)
from talk_with_the_engineer.core.package import (
    DEFAULT_ACTIONS,
    Constraints,
    best_on_axis,
    can_improve_a_requirement,
    cost_epsilon,
    indistinguishable_under_step_cost,
    optimize,
)
from talk_with_the_engineer.core.transition import (
    simulate,
    storm_shape,
)
from talk_with_the_engineer.interface.tools.supply import Deficit
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

FEASIBILITY_MARGIN = 1e-6
"""Hoe ver een as-grens de eis mag missen om nog 'op zichzelf haalbaar' te heten.

Dezelfde orde als de haalbaarheidstoets van de kern: strak, want 'haalbaar' beweren op
basis van een optimalisatierestje is erger dan een haalbare eis heel af en toe
onhaalbaar noemen.
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


def _absent_reasons(result, state, input, constraints, deficit) -> dict:
    """Per afwezige maatregel de gemeten reden: draagt niet bij, of past niet in de band."""
    if result.best is None:
        return {}
    quantities = [
        result.best.quantities.get(action.name_nl, 0.0) for action in DEFAULT_ACTIONS
    ]
    reasons = {}
    for index, action in enumerate(DEFAULT_ACTIONS):
        name = action.name_nl
        if any(
            r.name_nl == name and r.role is not MeasureRole.ABSENT
            for r in result.ranges
        ):
            continue
        reasons[name] = (
            "buiten_prijsband"
            if can_improve_a_requirement(
                state, input, DEFAULT_ACTIONS, quantities, constraints, index, deficit
            )
            else "draagt_niet_bij"
        )
    return reasons


def _range_reading(measure, state, absent_reasons=None) -> MeasureRangeReading:
    """Een interval met de herkomst van zijn bovengrens erbij.

    De herkomst is af te lezen zonder de kern te vragen: raakt de bovenkant de zoekgrens
    van de maatregel, dan heeft niets anders hem gestopt; anders was het de prijsband
    (geprijsde maatregel) of de eis (prijsloze). Zonder die herkomst leest een zoekgrens
    als een koopadvies - een inlaat "tot 20 m3/s" is het tienvoudige van wat de eis vraagt.
    """
    if measure.role is MeasureRole.ABSENT:
        source = None
        reason = (absent_reasons or {}).get(measure.name_nl)
    else:
        reason = None
        action = next(a for a in DEFAULT_ACTIONS if a.name_nl == measure.name_nl)
        if measure.magnitude_max >= action.upper_bound(state) - 1e-6:
            source = "zoekgrens"
        elif action.unit_cost is not None:
            source = "prijsband"
        else:
            source = "eis"
    return MeasureRangeReading(
        name_nl=measure.name_nl,
        unit=measure.unit,
        magnitude_min=round_significant(measure.magnitude_min),
        magnitude_max=round_significant(measure.magnitude_max),
        magnitude_max_source=source,
        absent_reason=reason,
        role=measure.role,
    )


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


def _missed(input: OptimizeInput, packages, state, deficit) -> list[RequirementMiss]:
    """Per gestelde eis: wat de gezamenlijke zoektocht zag, en wat er op die as echt kan.

    Twee verschillende getallen, en het verschil is de hele reden dat dit een eigen
    doorrekening heeft. De pakketten uit de gezamenlijke zoektocht zijn op kosten
    geoptimaliseerd en zeggen bij onhaalbaarheid niets over de as zelf; `best_on_axis`
    optimaliseert de as en levert dus een echte grens. Die grens draagt bovendien een
    diagnose die de gezamenlijke zoektocht niet kan leveren: is elke eis op zichzelf
    haalbaar, dan conflicteren de eisen - versoepelen kan dan genoeg zijn, waar 'het kan
    niet' een ander plan vraagt.
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
        bound = best_on_axis(state, input, label, deficit=deficit)
        misses.append(
            RequirementMiss(
                requirement=label,
                required=required,
                reached=reached,
                missed_by=smallest,
                achievable_alone=bound,
                alone_feasible=sign * (bound - required) <= FEASIBILITY_MARGIN,
            )
        )
    return misses


def _priceless_posts(input, package) -> list[PricelessPost]:
    """Alles in dit antwoord zonder bedrag: de gekozen maatregelen én de opgegeven context.

    De context weegt even zwaar als de maatregel. Een opgegeven peilmarge van 30 cm maakt
    hetzelfde pakket ruim een kwart goedkoper, en zonder post leest dat als gratis winst -
    terwijl het bedrijfsvoering en drooglegging kost. Deelt een contextpost zijn onderwerp
    met een gekozen maatregel (een polder die al is opgezet en er opzet bij krijgt), dan
    worden ze één post die beide maatvoeringen draagt.
    """
    posts = {}
    for name in package.priceless:
        if name in PRICELESS_COST:
            posts[name] = PricelessPost(
                topic=name,
                magnitude=f"{measure_amount(name, package.quantities[name])} als maatregel",
                what_it_costs=PRICELESS_COST[name],
            )
    for given in priceless_posts(input, None):
        topic = given["topic"]
        if topic in posts:
            posts[topic] = posts[topic].model_copy(
                update={
                    "magnitude": (
                        f"{posts[topic].magnitude}, bovenop de {given['magnitude']} "
                        "die er al staat"
                    )
                }
            )
        else:
            posts[topic] = PricelessPost(**given)
    return list(posts.values())


def _describe(input, status, result, indistinguishable, ranges, misses) -> str:
    """De zinnen bij dit antwoord, per status uit het bijbehorende sjabloon."""
    language = input.language
    if status is SolveStatus.PROBLEM_INFEASIBLE:
        text = describe_infeasible(input, misses, examined=len(result.packages))
    elif status is SolveStatus.NO_MEASURE_NEEDED:
        text = describe_no_measure_needed(
            input, result.best, dh_reference_m=result.best.dh_total_m
        )
    else:
        parts = [
            describe_package_found(input, result.best),
            describe_region(ranges, language),
            describe_step_cost_plateau(result.best, indistinguishable, language),
        ]
        text = " ".join(part for part in parts if part)
    return text


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

    misses = [] if best is not None else _missed(input, result.packages, state, deficit)
    if best is None:
        # De zoektocht is altijd volledig - alle combinaties van de vijf maatregelen -
        # dus "geen pakket" betekent hier werkelijk: geen enkele combinatie haalt het.
        status = SolveStatus.PROBLEM_INFEASIBLE
    elif not any(magnitude > 0 for magnitude in best.quantities.values()):
        status = SolveStatus.NO_MEASURE_NEEDED
    else:
        status = SolveStatus.EXACT

    if status is SolveStatus.NO_MEASURE_NEEDED:
        # Zonder gevraagde maatregel is er geen gebied om rollen in te geven; vijf keer
        # "absent" zou lezen als "draagt niet bij" waar niets gevraagd is.
        ranges = []
    else:
        reasons = _absent_reasons(result, state, input, constraints, deficit)
        ranges = [_range_reading(measure, state, reasons) for measure in result.ranges]

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
        description=append_assumptions(
            _describe(input, status, result, indistinguishable, ranges, misses),
            assumptions,
            input.language,
        ),
        status=status,
        best=None if best is None else _reading(best),
        near_optimal=[
            _reading(package)
            for package in (
                [] if best is None else _others_than(best, result.near_optimal)
            )
        ],
        priced_cost_range=(
            best.priced_cost_range
            if best is not None
            and best.priced_cost_range[1] > best.priced_cost_range[0]
            else None
        ),
        cost_epsilon=0.0 if best is None else cost_epsilon(best),
        ranges=ranges,
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
        priceless=[] if best is None else _priceless_posts(input, best),
    )

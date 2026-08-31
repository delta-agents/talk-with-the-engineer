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

from itertools import combinations

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
    SwitchPriceReading,
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
    switch_price_of,
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

REQUIREMENT_LABELS = {
    "max_dh_total_m": "inundatie",
    "min_storage_mm": "voorraad",
    "max_shortfall_mm": "tekort",
}


def _constraints(input: OptimizeInput) -> Constraints:
    return Constraints(
        max_dh_total_m=input.max_dh_total_m,
        min_storage_mm=input.min_storage_mm,
        max_shortfall_mm=input.max_shortfall_mm,
    )


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
    """
    misses = []
    for field, label in REQUIREMENT_LABELS.items():
        required = getattr(input, field)
        if required is None:
            continue
        if field == "max_dh_total_m":
            overshoot = [(p.dh_total_m - required, p.dh_total_m) for p in packages]
        elif field == "min_storage_mm":
            overshoot = [(required - p.storage_mm, p.storage_mm) for p in packages]
        else:
            overshoot = [
                (p.shortfall_mm - required, p.shortfall_mm)
                for p in packages
                if p.shortfall_mm is not None
            ]
        if not overshoot:
            continue
        smallest, reached = min(overshoot, key=lambda pair: pair[0])
        if smallest <= 0:
            # Deze eis is wel te halen; hij is niet de reden dat het pakket niet bestaat.
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


def _unexplored_mixes(input: OptimizeInput) -> list[list[str]]:
    """De combinaties die buiten `max_mix_size` vallen.

    Stil begrenzen leest als "alles gedekt", en juist de grotere combinaties zijn waar de
    trits ontstaat.
    """
    if input.max_mix_size is None:
        return []
    names = [action.name_nl for action in DEFAULT_ACTIONS]
    return [
        sorted(mix)
        for size in range(input.max_mix_size + 1, len(names) + 1)
        for mix in combinations(names, size)
    ]


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


def _switch_prices(
    state, input, constraints, deficit, package
) -> list[SwitchPriceReading]:
    """De prijs waarbij elke prijsloze maatregel het antwoord omslaat.

    Kost veertien nieuwe zoektochten per maatregel en gebeurt daarom alleen op verzoek.
    """
    readings = []
    for name in package.priceless:
        price = switch_price_of(
            state,
            input,
            constraints,
            name,
            max_mix_size=input.max_mix_size,
            deficit=deficit,
        )
        readings.append(
            SwitchPriceReading(
                measure_nl=price.measure_nl,
                unit=price.unit,
                price_low=price.price_low,
                price_high=price.price_high,
                package_below=list(price.package_below),
                package_above=list(price.package_above),
                changed=price.changed,
                searched_up_to=price.searched_up_to,
            )
        )
    return readings


def _describe_no_package(input, packages, unexplored) -> str:
    """Waarom er geen pakket is, en hoeveel het scheelt.

    Met een begrensde mix is dit uitdrukkelijk niet "het kan niet": de combinaties die niet
    zijn onderzocht staan erbij, want een grotere combinatie kan het nog halen.
    """
    misses = _missed(input, packages)
    listed = ", ".join(
        f"{miss.requirement} komt {round_significant(miss.missed_by):g} tekort"
        for miss in misses
    )
    if input.language == "en":
        text = (
            f"None of the {len(packages)} combinations searched meets the requirements at "
            "the same time."
            if unexplored
            else "No combination of these five measures meets the requirements at the same time."
        )
        if listed:
            text += f" Closest miss: {listed}."
        if unexplored:
            text += (
                f" Note that max_mix_size left {len(unexplored)} larger combinations "
                "unexamined; raise it before concluding this cannot be done."
            )
        return text

    text = (
        f"Geen van de {len(packages)} onderzochte combinaties haalt de eisen tegelijk."
        if unexplored
        else "Geen enkele combinatie van deze vijf maatregelen haalt de eisen tegelijk."
    )
    if listed:
        text += f" Het scheelt het minst op: {listed}."
    if unexplored:
        text += (
            f" Let op dat `max_mix_size` {len(unexplored)} grotere combinaties buiten de "
            "zoektocht heeft gelaten; verhoog hem voordat je concludeert dat het niet kan."
        )
    return text


def _describe(result, indistinguishable, input, assumptions, unexplored) -> str:
    """De zinnen bij dit antwoord: het gebied, de twee kostenlezingen, en de aannames."""
    language = input.language
    if result.best is None:
        return append_assumptions(
            _describe_no_package(input, result.packages, unexplored),
            assumptions,
            language,
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

    parts = [
        describe_region(result.ranges, language),
        describe_step_cost_plateau(result.best, indistinguishable, language),
    ]
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

    result = optimize(
        state,
        input,
        constraints,
        max_mix_size=input.max_mix_size,
        deficit=deficit,
    )

    best = result.best
    indistinguishable = indistinguishable_under_step_cost(result)
    assumptions = assumed_defaults(input)

    unexplored = _unexplored_mixes(input)
    if best is None:
        # ONOPLOSBAAR betekent "geen enkel pakket haalt dit", en die uitspraak is niet gedaan
        # zodra `max_mix_size` combinaties buiten de zoektocht heeft gelaten. Dan is het de
        # zwakkere uitspraak: wat er is onderzocht haalt het niet, een grotere combinatie
        # misschien wel.
        status = (
            SolveStatus.ACTION_INFEASIBLE
            if unexplored
            else SolveStatus.PROBLEM_INFEASIBLE
        )
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
        description=_describe(
            result, indistinguishable, input, assumptions, unexplored
        ),
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
        switch_prices=(
            _switch_prices(state, input, constraints, deficit, best)
            if input.switch_prices and best is not None
            else []
        ),
        missed=[] if best is not None else _missed(input, result.packages),
        unexplored_mixes=unexplored,
        packages=(
            [_reading(package) for package in result.packages] if input.detail else []
        ),
        assumptions=assumptions,
        caveats=model_caveats(input, has_cost=best is not None and best.cost > 0),
        priceless=[] if best is None else _priceless_posts(best),
    )

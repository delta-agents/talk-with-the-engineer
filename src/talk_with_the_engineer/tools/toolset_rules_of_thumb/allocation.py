"""Watertekort op systeemschaal: wie krijgt wat als meerdere gebieden één bron delen.

De tiende tool, en de droge tegenhanger van `calculate_cascade_given_excess`. Daar is de
afvoercapaciteit de klem en gaat het over drainage; hier is de bron de klem en gaat het
over verdelen. Hij geeft geen
rij per afnemer terug maar de bindende categorie, de trap, en één onderscheid dat een model
per gebied niet kan maken: of het tekort door de BRON komt of door de INLATEN. Dat zijn twee
verschillende adviezen - in het eerste geval helpt meer water aanvoeren, in het tweede alleen
een grotere inlaat - en het is precies het verschil dat de eenpolder-aanvoertools moeten
aannemen omdat ze maar één gebied zien.
"""

import numpy as np
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.allocation import (
    AllocationInput,
    AllocationOutput,
    ThetaStep,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
    model_caveats,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.system import SystemState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.allocate import (
    WithinShellRule,
    allocate,
    theta_table,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    describe_allocation,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SECONDS_PER_DAY = 86_400.0
MM_TO_M = 1e-3
HECTARE_TO_M2 = 1e4


def _system_of(input: AllocationInput) -> SystemState:
    """De selectie als graaf; dezelfde vorm als `region._system_of`, andere richting.

    De verbinding is hetzelfde object: `draws_from` vult `Connection.to` en de
    inlaatcapaciteit vult `capacity_in_m3_per_sec`. Dat is §5.2 van het ontwerpdocument in
    de praktijk - een gemaal en een inlaat hangen aan dezelfde kant, en de cascade is geen
    uitbreiding van het model maar dezelfde verbinding met een andere bestemming.
    """
    known = {node.name for node in input.nodes}
    polders = []
    for node in input.nodes:
        if node.draws_from is not None and node.draws_from not in known:
            raise ModelRetry(
                f"Gebied {node.name!r} laat in uit {node.draws_from!r}, en dat gebied zit "
                "niet in de selectie. Voeg het toe, of laat `draws_from` weg als het "
                "rechtstreeks uit de bron trekt."
            )
        polders.append(
            PolderState(
                area_ha=node.area_ha,
                # de natte kant doet in een verdelingsvraag niet mee, maar `PolderState`
                # heeft een open-wateraandeel nodig om te bestaan
                pct_open_water=3.5,
                connections=(
                    Connection(
                        to=node.draws_from or OUTSIDE,
                        capacity_in_m3_per_sec=node.intake_capacity_m3_per_sec,
                    ),
                ),
            )
        )
    try:
        return SystemState.from_polders(
            polders, names=[node.name for node in input.nodes]
        )
    except ValueError as error:
        raise ModelRetry(f"Deze selectie is geen geldige verdeling: {error}") from error


def _demand_m3(input: AllocationInput) -> np.ndarray:
    """De watervraag per gebied over de hele periode [m3].

    In volumes en niet in debieten, want een bron is eindig in volume. Dat is de hele reden
    dat WP12 het volume naast het debiet zette: een debiet klinkt haalbaar en een volume
    nodigt uit tot narekenen.
    """
    return np.array(
        [
            node.deficit_mm_per_day
            * MM_TO_M
            * node.area_ha
            * HECTARE_TO_M2
            * input.length_days
            for node in input.nodes
        ]
    )


def _coverage_range(primary, alternative, categories, category) -> list[float]:
    """De laagste en hoogste dekking van een individuele afnemer, over beide verdelingen.

    Beide vormen verdelen hetzelfde volume, dus dit is puur de vraag wie het tekort draagt -
    en daar zegt de wet niets over. Melden als band is dus geen vaagheid maar precisie: het
    is exact wat wij wel weten.
    """
    selection = categories == category
    if not selection.any():
        return [1.0, 1.0]
    values = [
        float(result.coverage[selection].min()) for result in (primary, alternative)
    ] + [float(result.coverage[selection].max()) for result in (primary, alternative)]
    return [min(values), max(values)]


@log_tool_call
async def calculate_allocation_given_shortage(
    ctx, input: AllocationInput
) -> AllocationOutput:
    """Wie krijgt wat als meerdere gebieden om dezelfde eindige bron concurreren?

    Allocation = watertekort op systeemschaal, verdeeld volgens de verdringingsreeks.
    """
    system = _system_of(input)
    demand = _demand_m3(input)
    total_demand = float(demand.sum())
    if total_demand <= 0.0:
        raise ModelRetry(
            "Geen van de gebieden heeft een watervraag, dus er is niets te verdelen. Geef "
            "minstens een gebied een `deficit_mm_per_day` groter dan nul."
        )

    categories = np.array([node.category for node in input.nodes])
    unlimited = input.available_source_volume_m3 is None
    available = float("inf") if unlimited else float(input.available_source_volume_m3)
    rule = WithinShellRule.PROPORTIONAL

    result = allocate(system, demand, categories, available, input.length_days, rule)
    # De tweede verdedigbare verdeling binnen een schil. Niet om te kiezen, maar om de
    # BAND te melden: het categorietotaal is in beide vormen gelijk, de verdeling niet.
    alternative = allocate(
        system,
        demand,
        categories,
        available,
        input.length_days,
        WithinShellRule.MAXIMIN,
    )

    # Komt het tekort door de bron of door de inlaten? Hetzelfde nog eens met een onbeperkte
    # bron: blijft het tekort gelijk, dan zijn de inlaten de klem en helpt meer water niet.
    with_infinite_source = allocate(
        system, demand, categories, float("inf"), input.length_days, rule
    )
    capacity_bound = bool(
        with_infinite_source.granted_m3.sum() <= result.granted_m3.sum() + 1.0
    )

    present = sorted(set(int(category) for category in categories))
    bands = {
        category: _coverage_range(result, alternative, categories, category)
        for category in present
    }
    steps = [
        ThetaStep(
            theta_low=regime.theta_low,
            theta_high=regime.theta_high,
            coverage={str(k): v for k, v in regime.coverage.items()},
            binding_category=regime.binding_category,
        )
        for regime in theta_table(system, demand, categories, input.length_days, rule)
    ]

    assumptions = assumed_defaults(input)
    caveats = model_caveats(
        input,
        is_drought=True,
        allocation_rule=rule.value,
        source_volume_given=not unlimited,
    )
    return AllocationOutput(
        description=describe_allocation(
            result,
            node_count=system.size,
            theta=None if unlimited else available / total_demand,
            capacity_bound=capacity_bound,
            spread=bands.get(result.binding_category),
        ),
        assumptions=assumptions,
        caveats=caveats,
        node_count=system.size,
        depth=len(system.topological_levels()),
        within_shell_rule=rule.value,
        total_demand_m3=total_demand,
        total_granted_m3=float(result.granted_m3.sum()),
        total_shortfall_m3=float(result.shortfall_m3.sum()),
        theta=None if unlimited else available / total_demand,
        coverage_per_category={
            str(category): result.coverage_of_category(category) for category in present
        },
        individual_coverage_range_per_category={
            str(category): band for category, band in bands.items()
        },
        binding_category=result.binding_category,
        binding_is_capacity_not_availability=capacity_bound,
        theta_steps=steps,
    )

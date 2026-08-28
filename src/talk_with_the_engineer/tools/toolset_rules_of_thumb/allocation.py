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

from dataclasses import dataclass

import numpy as np
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.allocation import (
    MAX_NODES,
    AllocationInput,
    AllocationOutput,
    ThetaStep,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.demand import (
    DEMAND_POST_CATEGORY,
    DEMAND_POSTS,
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
    binding_is_capacity,
    theta_table,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    describe_allocation,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SECONDS_PER_DAY = 86_400.0
MM_TO_M = 1e-3
HECTARE_TO_M2 = 1e4


@dataclass(frozen=True)
class _Consumer:
    """Een afnemer zoals de rekenkern hem ziet.

    Meestal is dat een knoop uit de selectie, een op een. Vraagt een knoop om de regionale
    vraagposten, dan wordt hij een doorvoerknoop met de posten eronder, en dan is dit de
    tussenlaag waarin die twee gevallen dezelfde vorm hebben.
    """

    name: str
    area_ha: float
    deficit_mm_per_day: float
    category: int
    intake_capacity_m3_per_sec: float
    draws_from: str | None
    demand_post: str | None


def _posts_below(node, shares) -> list[_Consumer]:
    """De knoop als doorvoer, met de vier vraagposten eronder.

    De inlaat blijft waar hij hoort: op de knoop zelf. De posten hangen erachter en dragen
    dezelfde capaciteit, want ze delen die keel en geen van hen kan er meer door krijgen dan
    de knoop zelf. Zouden ze de capaciteit elk als eigen keel meenemen, dan zou het splitsen
    van de vraag de inlaat verviervoudigen.

    Het opgegeven tekort is de BEREGENINGSpost. De andere drie volgen uit de verhouding die
    de werkopgave voor deze regio geeft, dus ze zijn een uitspraak over hoe groot de
    watervraag om dit gebied heen is en niet over het gewas.
    """
    irrigation_share = shares.demand_share.get("beregening")
    if not irrigation_share:
        raise ModelRetry(
            f"In deze regio heeft beregening volgens de werkopgave geen aandeel in de "
            f"watervraag, dus er is geen verhouding om het tekort van {node.name!r} mee op "
            "te schalen naar de andere posten. Kies een regio waar beregening voorkomt, of "
            "geef de posten als eigen gebieden op met `demand_post`."
        )
    total = node.deficit_mm_per_day / irrigation_share
    consumers = [
        _Consumer(
            name=node.name,
            area_ha=node.area_ha,
            # de knoop zelf vraagt niets meer: zijn vraag zit in de posten eronder
            deficit_mm_per_day=0.0,
            category=node.category,
            intake_capacity_m3_per_sec=node.intake_capacity_m3_per_sec,
            draws_from=node.draws_from,
            demand_post=None,
        )
    ]
    for post in DEMAND_POSTS:
        share = shares.demand_share.get(post) or 0.0
        consumers.append(
            _Consumer(
                name=f"{node.name} - {post}",
                area_ha=node.area_ha,
                deficit_mm_per_day=total * share,
                category=node.category
                if post == "beregening"
                else DEMAND_POST_CATEGORY[post],
                intake_capacity_m3_per_sec=node.intake_capacity_m3_per_sec,
                draws_from=node.name,
                demand_post=post,
            )
        )
    return consumers


def _consumers(input: AllocationInput) -> list[_Consumer]:
    """De selectie, met de vraagposten erbij waar erom gevraagd is.

    De begrenzing op `MAX_NODES` geldt na het uitsplitsen: vijf knopen die elk om hun posten
    vragen zijn vijfentwintig afnemers, en dat is wat er in het antwoord te lezen valt.
    """
    consumers = []
    for node in input.nodes:
        if node.add_regional_demand_posts:
            consumers.extend(_posts_below(node, input.demand_posts))
        else:
            consumers.append(
                _Consumer(
                    name=node.name,
                    area_ha=node.area_ha,
                    deficit_mm_per_day=node.deficit_mm_per_day,
                    category=node.category,
                    intake_capacity_m3_per_sec=node.intake_capacity_m3_per_sec,
                    draws_from=node.draws_from,
                    demand_post=node.demand_post,
                )
            )
    names = [consumer.name for consumer in consumers]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        listed = ", ".join(repr(name) for name in duplicates)
        raise ModelRetry(
            f"Het uitsplitsen in vraagposten levert een naam op die al bestaat: {listed}. "
            "Hernoem dat gebied; een post heet naar het gebied waar hij bij hoort."
        )
    if len(consumers) > MAX_NODES:
        raise ModelRetry(
            f"Met de vraagposten erbij zijn dit {len(consumers)} afnemers en er passen "
            f"{MAX_NODES} in een antwoord. Elke knoop die om zijn posten vraagt levert er "
            "vijf op; splits de vraag in kleinere selecties."
        )
    return consumers


def _system_of(consumers: list[_Consumer]) -> SystemState:
    """De selectie als graaf; dezelfde vorm als `region._system_of`, andere richting.

    De verbinding is hetzelfde object: `draws_from` vult `Connection.to` en de
    inlaatcapaciteit vult `capacity_in_m3_per_sec`. Dat is §5.2 van het ontwerpdocument in
    de praktijk - een gemaal en een inlaat hangen aan dezelfde kant, en de cascade is geen
    uitbreiding van het model maar dezelfde verbinding met een andere bestemming.
    """
    known = {node.name for node in consumers}
    polders = []
    for node in consumers:
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
            polders, names=[node.name for node in consumers]
        )
    except ValueError as error:
        raise ModelRetry(f"Deze selectie is geen geldige verdeling: {error}") from error


def _demand_m3(consumers: list[_Consumer], length_days: int) -> np.ndarray:
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
            * length_days
            for node in consumers
        ]
    )


def _coverage_range(primary, alternative, categories, category) -> list[float]:
    """De laagste en hoogste dekking van een individuele afnemer, over beide verdelingen.

    Beide vormen verdelen hetzelfde volume, dus dit is puur de vraag wie het tekort draagt -
    en daar zegt de wet niets over. Melden als band is dus geen vaagheid maar precisie: het
    is exact wat wij wel weten.

    **Knopen zonder watervraag tellen niet mee.** Een boezem die alleen als doorvoer in de
    selectie zit heeft `deficit_mm_per_day: 0` maar wel een categorie.
    `AllocationResult.coverage` zet zo'n knoop op 1,0 - terecht, want 0 van 0 gevraagd is
    volledig bediend - maar in een band over INDIVIDUELE afnemers trekt dat de bovengrens
    naar 100 %, en dan leest de zin als "de dekking loopt van 71 % tot 100 %": er zou een
    verdeling bestaan waarbij deze afnemer volledig bediend wordt. Die is er niet.

    Een doorvoerknoop is geen exotisch geval maar het normale gebruik - hij is structureel
    nodig zodra `draws_from` in het spel is.

    Blijft er na die uitsluiting niemand over, dan is er in deze categorie geen afnemer met
    een vraag en is de band leeg; `[1.0, 1.0]` is dan hetzelfde antwoord als bij een
    categorie die helemaal niet voorkomt.
    """
    asking = primary.demand_m3 > 0.0
    selection = (categories == category) & asking
    if not selection.any():
        return [1.0, 1.0]
    values = [
        float(result.coverage[selection].min()) for result in (primary, alternative)
    ] + [float(result.coverage[selection].max()) for result in (primary, alternative)]
    return [min(values), max(values)]


def _coverage_per_post(result, consumers) -> dict:
    """De dekkingsfractie per watervraagpost.

    Leeg zodra geen enkele afnemer een post draagt; een blok met vier keer 1,0 zou dan
    suggereren dat de posten hebben meegedaan. Waar een post wel voorkomt is dit de
    uitlezing waar de indeling voor bedoeld is: peilbeheer komt vol en beregening niet.
    """
    posts = {}
    for post in DEMAND_POSTS:
        selection = np.array(
            [consumer.demand_post == post for consumer in consumers], dtype=bool
        )
        if not selection.any():
            continue
        demand = float(result.demand_m3[selection].sum())
        granted = float(result.granted_m3[selection].sum())
        posts[post] = 1.0 if demand <= 0.0 else granted / demand
    return posts


def _demand_post_context(input, consumers) -> dict:
    """Wat de vraagpost-caveats nodig hebben om zichzelf te schrijven."""
    chosen = input.demand_post_choice
    posts = input.demand_posts
    used = sorted(
        {consumer.demand_post for consumer in consumers if consumer.demand_post}
    )
    context = {"demand_posts_used": used} if used else {}
    if not chosen or posts is None:
        return context
    return {
        **context,
        "demand_post_choice": chosen,
        "demand_share": posts.demand_share,
        "demand_share_is_coarse": posts.is_coarse,
        "demand_share_resolution": posts.share_resolution,
    }


def _contains(regime, theta: float | None) -> bool:
    """Valt het opgegeven aanbod in deze trede?

    De beller hoefde dit eerder zelf te matchen, en juist daar ging het mis: wie zijn theta
    in een trede opzocht en de dekking van die trede overnam, las de waarde op de bovengrens
    in plaats van die bij zijn eigen aanbod.

    De bovengrens telt mee en de ondergrens niet, zodat een knikpunt bij precies één trede
    hoort. Bij theta = 0 is er geen trede eronder, dus die valt in de eerste.
    """
    if theta is None:
        return False
    return regime.theta_low <= theta <= regime.theta_high and (
        theta > regime.theta_low or regime.theta_low == 0.0
    )


@log_tool_call
async def calculate_allocation_given_shortage(
    ctx, input: AllocationInput
) -> AllocationOutput:
    """Wie krijgt wat als meerdere gebieden om dezelfde eindige bron concurreren?

    Allocation = watertekort op systeemschaal, verdeeld volgens de verdringingsreeks.
    """
    consumers = _consumers(input)
    system = _system_of(consumers)
    demand = _demand_m3(consumers, input.length_days)
    total_demand = float(demand.sum())
    if total_demand <= 0.0:
        raise ModelRetry(
            "Geen van de gebieden heeft een watervraag, dus er is niets te verdelen. Geef "
            "minstens een gebied een `deficit_mm_per_day` groter dan nul."
        )

    categories = np.array([node.category for node in consumers])
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
    capacity_bound = binding_is_capacity(result, with_infinite_source)

    present = sorted(set(int(category) for category in categories))
    bands = {
        category: _coverage_range(result, alternative, categories, category)
        for category in present
    }
    theta = None if unlimited else available / total_demand
    steps = [
        ThetaStep(
            theta_low=regime.theta_low,
            theta_high=regime.theta_high,
            coverage_at_low={str(k): v for k, v in regime.coverage_at_low.items()},
            coverage_at_high={str(k): v for k, v in regime.coverage_at_high.items()},
            binding_category=regime.binding_category,
            binding_is_capacity_not_availability=regime.binding_is_capacity_not_availability,
            contains_current_theta=_contains(regime, theta),
        )
        for regime in theta_table(system, demand, categories, input.length_days, rule)
    ]

    assumptions = assumed_defaults(input)
    availability = input.source_availability
    caveats = model_caveats(
        input,
        is_drought=True,
        allocation_rule=rule.value,
        source_volume_given=not unlimited,
        salinisation_is_the_next_step=True,
        **_demand_post_context(input, consumers),
        **(
            {
                "source_volume_from_statistic": True,
                "source_river": input.source_river,
                "source_availability_fraction": availability.fraction,
                "source_spread_factor": [
                    availability.spread_low,
                    availability.spread_high,
                ],
                "source_fit_r": availability.fit_r,
            }
            if availability is not None
            else {}
        ),
    )
    return AllocationOutput(
        description=describe_allocation(
            result,
            node_count=system.size,
            theta=theta,
            capacity_bound=capacity_bound,
            spread=bands.get(result.binding_category),
            language=input.language,
        ),
        assumptions=assumptions,
        caveats=caveats,
        node_count=system.size,
        depth=len(system.topological_levels()),
        within_shell_rule=rule.value,
        available_source_volume_m3=None if unlimited else available,
        total_demand_m3=total_demand,
        total_granted_m3=float(result.granted_m3.sum()),
        total_shortfall_m3=float(result.shortfall_m3.sum()),
        theta=theta,
        coverage_per_category={
            str(category): result.coverage_of_category(category) for category in present
        },
        individual_coverage_range_per_category={
            str(category): band for category, band in bands.items()
        },
        coverage_per_demand_post=_coverage_per_post(result, consumers),
        demand_share_per_post=(
            dict(input.demand_posts.demand_share)
            if any(node.add_regional_demand_posts for node in input.nodes)
            else {}
        ),
        binding_category=result.binding_category,
        binding_is_capacity_not_availability=capacity_bound,
        theta_steps=steps,
    )

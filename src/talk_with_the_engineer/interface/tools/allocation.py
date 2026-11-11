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
from operator import attrgetter

import numpy as np
from pydantic_ai import ModelRetry

from talk_with_the_engineer.interface.schemas.allocation import (
    MAX_NODES,
    AllocationInput,
    AllocationOutput,
    ThetaStep,
)
from talk_with_the_engineer.interface.schemas.demand import (
    DEMAND_POST_CATEGORY,
    DEMAND_POSTS,
)
from talk_with_the_engineer.epistemics.assumptions import assumed_defaults
from talk_with_the_engineer.epistemics.caveats import model_caveats
from talk_with_the_engineer.core.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.interface.schemas.output import PricelessPost
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.system import SystemState
from talk_with_the_engineer.core.allocation import (
    WithinShellRule,
    allocate,
    binding_is_capacity,
    theta_table,
)
from talk_with_the_engineer.interface.descriptions import (
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
    storage_m3: float = 0.0
    """De eigen voorraad van dit gebied: peilband maal open water."""
    percentage_open_water: float = 3.5
    """Het open-wateraandeel; `PolderState` heeft er een nodig om te bestaan."""
    drawdown_available_m: float = 0.0
    """De peilband die dit gebied inzet [m]; staat in de prijsloze post."""


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
            # De voorraad gaat MEE NAAR DE POSTEN en blijft niet op de knoop staan. Het zijn
            # de sloten van deze polder, en de posten zijn de vraag van diezelfde polder -
            # dus dat water hoeft niet door de eigen inlaat. Bleef het hier staan, dan zou een
            # knoop zonder eigen vraag het aan de hele selectie delen en moest het daarna
            # alsnog door zijn keel, en dan levert de voorraad bij een klemmende inlaat niets.
            storage_m3=0.0,
            percentage_open_water=node.percentage_open_water,
            drawdown_available_m=node.drawdown_available_m,
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
                # naar rato van de vraag, zodat de hele voorraad van de polder aan zijn eigen
                # posten opgaat en er niets van naar de selectie lekt
                storage_m3=node.storage_m3 * share,
                percentage_open_water=node.percentage_open_water,
                drawdown_available_m=node.drawdown_available_m,
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
                    storage_m3=node.storage_m3,
                    percentage_open_water=node.percentage_open_water,
                    drawdown_available_m=node.drawdown_available_m,
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
                pct_open_water=node.percentage_open_water,
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

    In volumes en niet in debieten, want een bron is eindig in volume. Dat is ook de reden
    dat het volume naast het debiet in de uitvoer staat: een debiet klinkt haalbaar en een
    volume nodigt uit tot narekenen.
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


@dataclass(frozen=True)
class _Storage:
    """De voorraadboekhouding van de selectie, voordat er iets verdeeld wordt.

    Eerst de eigen vraag, dan de pot. Dat is een regel die twee gevallen dekt: een polder
    houdt zijn slootwater voor zichzelf, en een bergingsgebied - dat geen eigen vraag heeft -
    geeft zijn hele voorraad aan de selectie. Zo is een berging geen nieuw knooptype maar een
    knoop met veel open water en een vraag van nul.

    De rekenkern wordt hiervoor niet aangeraakt: de eigen voorraad gaat er als een LAGERE
    vraag in en de gedeelde voorraad als een GROTER bronvolume.
    """

    per_node_m3: np.ndarray
    """De voorraad van elk gebied [m3]."""
    own_m3: np.ndarray
    """Wat elk gebied uit zijn eigen voorraad dekt: `min(voorraad, vraag)`."""

    @property
    def total_m3(self) -> float:
        return float(self.per_node_m3.sum())

    @property
    def own_total_m3(self) -> float:
        return float(self.own_m3.sum())

    @property
    def shared_m3(self) -> float:
        """Wat er bij het bronvolume komt: de voorraad van wie er zelf geen vraag voor heeft."""
        return float((self.per_node_m3 - self.own_m3).sum())


def _storage_of(consumers, demand_m3) -> _Storage:
    """De voorraden naast de vraag gelegd."""
    per_node = np.array([consumer.storage_m3 for consumer in consumers], dtype=float)
    return _Storage(per_node_m3=per_node, own_m3=np.minimum(per_node, demand_m3))


def _coverage_of_category(granted_m3, demand_m3, categories, category) -> float:
    """De dekking van een categorie, gemeten tegen de vraag die de gebieden ECHT hebben.

    De eigen voorraad gaat als een lagere vraag de rekenkern in, dus de dekking die daar
    uitkomt is er een van de RESTvraag. Wie zijn sloten leegtrekt en de rest toegewezen
    krijgt is voor honderd procent gedekt, en dat is wat hier staat.
    """
    selection = categories == category
    demand = float(demand_m3[selection].sum())
    if demand <= 0.0:
        return 1.0
    return float(granted_m3[selection].sum() / demand)


def _days_covered(storage: _Storage, shortfall_without_m3, length_days) -> float | None:
    """Het tekort van hoeveel dagen deze voorraden dekken.

    Een deling en geen doorrekening: de voorraad gedeeld door het tekort per dag dat er
    zonder haar zou zijn. Dat is de uitspraak waarin een waterschap over een berging praat -
    "hier kopen we een week mee" - en het is dezelfde vorm als `days_until_buffer_empty` op de
    aanvoertools.

    `None` als er geen voorraad is, en ook als er zonder voorraad geen tekort zou zijn: dan
    zijn er geen dagen te kopen.
    """
    if storage.total_m3 <= 0.0 or shortfall_without_m3 <= 0.0:
        return None
    return storage.total_m3 / (shortfall_without_m3 / length_days)


def _storage_post(consumers, storage: _Storage):
    """De peilband die de selectie inzet: geen bedrag, wel een prijs.

    Twee prijzen op dezelfde centimeters. De marge onder het streefpeil is bedrijfsvoering en
    drooglegging, zoals op de aanvoertools. En bij een gebied dat vooral water is komt er een
    tweede bij die zwaarder weegt: een bergingsgebied dat volstaat voor de droogte is niet
    beschikbaar voor de bui waarvoor hij is aangelegd. Dezelfde centimeters twee keer
    verkopen kan niet.
    """
    if storage.total_m3 <= 0.0:
        return None
    deepest = max(consumers, key=attrgetter("drawdown_available_m"))
    return PricelessPost(
        topic="de peilband die je inzet",
        magnitude=f"{storage.total_m3 / 1e6:.2f} mln m3 voorraad",
        what_it_costs=(
            "Bedrijfsvoering en drooglegging: de diepte die je onder het streefpeil "
            "vrijmaakt is zomervoorraad die je daarna niet meer hebt, en in "
            f"{deepest.name!r} is dat {deepest.drawdown_available_m * 100:.0f} cm. Zet je "
            "een gebied vol dat als bergingsgebied is aangelegd, dan komt daar de "
            "bergingsfunctie zelf bij: vol voor de droogte is niet beschikbaar voor de bui, "
            "en dat zijn dezelfde centimeters. Deze prijs staat in geen enkel bedrag."
        ),
    )


def _coverage_per_post(granted_m3, demand_m3, consumers) -> dict:
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
        demand = float(demand_m3[selection].sum())
        granted = float(granted_m3[selection].sum())
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

    # De voorraden gaan de rekenkern in als een lagere vraag en een groter bronvolume; de
    # kern zelf verandert niet. Zie `_Storage`.
    storage = _storage_of(consumers, demand)
    remaining_demand = demand - storage.own_m3
    pool = available if unlimited else available + storage.shared_m3

    result = allocate(
        system, remaining_demand, categories, pool, input.length_days, rule
    )
    # De tweede verdedigbare verdeling binnen een schil. Niet om te kiezen, maar om de
    # BAND te melden: het categorietotaal is in beide vormen gelijk, de verdeling niet.
    alternative = allocate(
        system,
        remaining_demand,
        categories,
        pool,
        input.length_days,
        WithinShellRule.MAXIMIN,
    )

    # Komt het tekort door de bron of door de inlaten? Hetzelfde nog eens met een onbeperkte
    # bron: blijft het tekort gelijk, dan zijn de inlaten de klem en helpt meer water niet.
    with_infinite_source = allocate(
        system, remaining_demand, categories, float("inf"), input.length_days, rule
    )
    capacity_bound = binding_is_capacity(result, with_infinite_source)

    # En hoeveel dagen de voorraden kopen: dezelfde verdeling zonder hen, zodat het tekort
    # per dag bekend is dat ze wegnemen.
    without_storage = allocate(
        system, demand, categories, available, input.length_days, rule
    )

    # de dekking tegen de vraag die de gebieden ECHT hebben, dus met hun eigen voorraad erin
    granted = result.granted_m3 + storage.own_m3
    present = sorted(set(int(category) for category in categories))
    bands = {
        category: _coverage_range(result, alternative, categories, category)
        for category in present
    }
    # theta en de trap gaan over wat de BRON nog moet doen: de vraag na de eigen voorraden,
    # tegen het aanbod plus wat de gebieden zonder eigen vraag delen. Zou theta op de volle
    # vraag staan en de trap op de restvraag, dan zou `contains_current_theta` de verkeerde
    # trede aanwijzen.
    remaining_total = float(remaining_demand.sum())
    theta = (
        None
        if unlimited or remaining_total <= 0.0
        else min(pool / remaining_total, 1.0)
    )
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
        for regime in theta_table(
            system, remaining_demand, categories, input.length_days, rule
        )
    ]

    assumptions = assumed_defaults(input)
    availability = input.source_availability
    caveats = model_caveats(
        input,
        is_drought=True,
        allocation_rule=rule.value,
        source_volume_given=not unlimited,
        salinisation_is_the_next_step=True,
        storage_m3=storage.total_m3,
        storage_shared_m3=storage.shared_m3,
        days_of_shortfall_covered=_days_covered(
            storage, float(without_storage.shortfall_m3.sum()), input.length_days
        ),
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

    def coverage_of(category) -> float:
        return _coverage_of_category(granted, demand, categories, category)

    return AllocationOutput(
        description=describe_allocation(
            result,
            node_count=system.size,
            theta=theta,
            capacity_bound=capacity_bound,
            spread=bands.get(result.binding_category),
            language=input.language,
            coverage_of_category=coverage_of,
        ),
        assumptions=assumptions,
        caveats=caveats,
        node_count=system.size,
        depth=len(system.topological_levels()),
        within_shell_rule=rule.value,
        available_source_volume_m3=None if unlimited else available,
        total_demand_m3=total_demand,
        total_storage_m3=storage.total_m3,
        storage_for_own_demand_m3=storage.own_total_m3,
        storage_shared_m3=storage.shared_m3,
        days_of_shortfall_covered=_days_covered(
            storage, float(without_storage.shortfall_m3.sum()), input.length_days
        ),
        total_granted_m3=float(granted.sum()),
        total_shortfall_m3=float(result.shortfall_m3.sum()),
        theta=theta,
        coverage_per_category={
            str(category): _coverage_of_category(granted, demand, categories, category)
            for category in present
        },
        individual_coverage_range_per_category={
            str(category): band for category, band in bands.items()
        },
        coverage_per_demand_post=_coverage_per_post(granted, demand, consumers),
        demand_share_per_post=(
            dict(input.demand_posts.demand_share)
            if any(node.add_regional_demand_posts for node in input.nodes)
            else {}
        ),
        binding_category=result.binding_category,
        binding_is_capacity_not_availability=capacity_bound,
        theta_steps=steps,
        priceless=[
            post for post in (_storage_post(consumers, storage),) if post is not None
        ],
    )

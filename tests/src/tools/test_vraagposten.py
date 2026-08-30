"""De watervraag is vier posten en dit model rekent er een.

Wat hier wordt vastgelegd:

* de vraagverdeling is CONTEXT en geen forcering: hem opvragen verandert geen enkel getal in
  de doorrekening;
* wat er wel verandert is dat het antwoord zegt welk deel van de regionale vraag het beslaat,
  en dat het niet zomaar naast een werkopgave-getal te leggen is;
* op de verdelingstool valt de vraag echt uiteen, en dan verdringt peilbeheer de beregening -
  dezelfde uitkomst als in de zomer van 2026 in het westen werkelijk is gekozen;
* alleen verhoudingen komen de code in, want de bron staat in Mm3 per regio en dit model in
  mm over een gebied.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import (
    AllocationInput,
    AllocationNode,
    SupplyInputGivenH,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.demand import (
    DEMAND_POST_CATEGORY,
    DEMAND_POSTS,
    DEMAND_REGIONS,
    DEMAND_RETURN_PERIODS,
    DEMAND_SCENARIOS,
)
from talk_with_the_engineer.tools import (
    calculate_allocation_given_shortage,
    calculate_supply_given_h,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_demand import (
    available_demand_regions,
    available_demand_return_periods,
    available_demand_scenarios,
    demand_posts,
    demand_posts_source,
)

POLDER = {"area_ha": 4000, "deficit_mm_per_day": 4, "drawdown_available_m": 0.3}
WEST = {
    "demand_region": "West",
    "demand_scenario": "REF2017",
    "demand_return_period": 20,
}


# --- de data zegt hetzelfde als de keuzelijsten --------------------------------------


def test_the_choice_lists_match_the_data_file():
    """Een keuzelijst die uit de data loopt, laat een agent een regio kiezen die niet bestaat."""
    assert list(DEMAND_REGIONS) == available_demand_regions()
    assert list(DEMAND_SCENARIOS) == available_demand_scenarios()
    assert tuple(DEMAND_RETURN_PERIODS) == available_demand_return_periods()


def test_the_return_periods_stop_at_twenty():
    """T20 is de bovengrens van de methode en niet van onze keuze.

    De frequentiecurve is per regio afgeleid uit de jaren van de reeks zelf, en per
    herhaaltijd zijn de vier jaren met de dichtstbijzijnde herhaaltijd gemiddeld. Doortrekken
    naar T50 vraagt een andere methode; het schema hoort die keuze dus niet aan te bieden.
    """
    assert max(DEMAND_RETURN_PERIODS) == 20


@pytest.mark.parametrize("region", DEMAND_REGIONS)
def test_every_share_block_is_a_ratio_that_closes(region):
    """De aandelen sommeren tot 1, in elke regio en elk scenario.

    Zonder die eigenschap is een aandeel geen verhouding en levert het uitsplitsen van een
    vraag over de posten een andere totale vraag dan er in ging. De bron is op hele Mm3
    afgerond en sluit daardoor zelf tot enkele procenten niet; hoe grof dat per regio is
    staat in `share_resolution`.
    """
    for scenario in DEMAND_SCENARIOS:
        for period in DEMAND_RETURN_PERIODS:
            found = demand_posts(region, scenario, period)
            if found is None:
                continue
            assert set(found.demand_share) == set(DEMAND_POSTS)
            assert sum(found.demand_share.values()) == pytest.approx(1.0, abs=5e-4)


def test_no_absolute_volume_reaches_the_code():
    """Alleen verhoudingen, want de bron is zonder regio-oppervlakken niet om te rekenen.

    De werkopgave staat in Mm3 per zomer per regio en dit model in mm over een gebied. Een
    volume overnemen zou een oppervlak veronderstellen dat we niet hebben; een aandeel is
    dimensieloos en dus wel overzetbaar. Alles wat deze kant op komt hoort daarom tussen nul
    en een te liggen.
    """
    found = demand_posts("West", "REF2017", 20)
    values = [
        *found.demand_share.values(),
        *[value for value in found.coverage.values() if value is not None],
        found.total_coverage,
    ]
    assert all(0.0 <= value <= 1.0 for value in values), values


def test_the_source_names_the_climate_gap():
    """De bron zegt zelf dat hij op een ander klimaatproduct rust dan de droogtestatistiek."""
    meta = demand_posts_source()
    assert "KNMI'14" in meta["climate"]
    assert "KNMI'23" in meta["climate"]
    assert "1,42" in meta["climate"]


def test_west_reproduces_the_published_composition():
    """Het ankergetal: in West is doorspoeling de grootste post en beregening de kleinste.

    Dit is de uitspraak waar de rest van dit bestand op rust, en hij is de reden dat de
    vraagkant te smal is: wat dit model rekent is de post van 7 %.
    """
    found = demand_posts("West", "REF2017", 20)
    shares = found.demand_share
    assert shares["doorspoeling_boezem"] == pytest.approx(0.40, abs=0.01)
    assert shares["peilbeheer"] == pytest.approx(0.46, abs=0.01)
    assert shares["beregening"] == pytest.approx(0.066, abs=0.005)
    assert shares["beregening"] == min(shares.values())


# --- op de aanvoertools is het context en geen forcering ------------------------------


@pytest.mark.asyncio
async def test_asking_for_the_split_changes_no_number(test_context):
    """De scherpste toets: de verdeling verandert de doorrekening niet.

    Zou ze dat wel doen, dan was ze een tweede forcering naast het tekort en zou niet meer te
    zien zijn welke van de twee het antwoord stuurt.
    """
    plain = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**POLDER, length_days=30)
    )
    with_posts = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**POLDER, length_days=30, **WEST)
    )

    assert with_posts.supply_capacity_m3_per_sec == plain.supply_capacity_m3_per_sec
    assert with_posts.shortfall_mm == plain.shortfall_mm
    assert with_posts.buffer_mm == plain.buffer_mm


@pytest.mark.asyncio
async def test_the_answer_says_which_post_it_computes(test_context):
    """Wat er wel verandert: het antwoord noemt zijn aandeel en zijn herkomst."""
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**POLDER, length_days=30, **WEST)
    )
    block = result.data["demand_posts"]
    assert block["demand_region"] == "West"
    assert block["demand_share"]["beregening"] == pytest.approx(0.066, abs=0.005)
    assert "beregening" in block["which_post_this_model_computes"]
    assert "peilbeheer" in block["which_post_this_model_computes"]

    caveat = next(
        item for item in result.caveats if "vier watervraagposten" in item.topic
    )
    # het aandeel van deze regio en niet de landelijke band, want er staat een regio bij
    assert "West" in caveat.what
    assert "KNMI" in caveat.consequence


@pytest.mark.asyncio
async def test_without_a_region_the_caveat_still_names_the_narrowness(test_context):
    """De smalte is een eigenschap van het model en niet van de aanroep."""
    result = await calculate_supply_given_h(
        test_context, SupplyInputGivenH(**POLDER, length_days=30)
    )
    caveat = next(
        item for item in result.caveats if "vier watervraagposten" in item.topic
    )
    assert "beregening" in caveat.what


def test_half_a_demand_triple_is_refused():
    """Half een verdeling kiezen bestaat niet, net als bij de droogte."""
    with pytest.raises(ModelRetry) as error:
        SupplyInputGivenH(**POLDER, demand_region="West")
    assert "demand_scenario" in str(error.value)
    assert "demand_return_period" in str(error.value)


def test_a_region_without_demand_is_refused_instead_of_zero():
    """Een regio zonder watervraag heeft geen verdeling, en nul zou een aandeel suggereren."""
    empty = [
        (region, scenario, period)
        for region in DEMAND_REGIONS
        for scenario in DEMAND_SCENARIOS
        for period in DEMAND_RETURN_PERIODS
        if demand_posts(region, scenario, period) is None
    ]
    if not empty:
        pytest.skip("geen regio zonder watervraag in de huidige data")
    region, scenario, period = empty[0]
    with pytest.raises(ModelRetry) as error:
        SupplyInputGivenH(
            **POLDER,
            demand_region=region,
            demand_scenario=scenario,
            demand_return_period=period,
        )
    assert "geen watervraag" in str(error.value)


# --- op de verdelingstool valt de vraag echt uiteen -----------------------------------


@pytest.mark.asyncio
async def test_a_post_carries_its_own_category(test_context):
    """De beller hoeft de categorie niet te verzinnen; de post draagt hem.

    Peilbeheer houdt onomkeerbare schade tegen - uitdrogende keringen, veenoxidatie - en staat
    daarmee in categorie 1. Beregening is een overig belang en staat in 4.
    """
    result = await calculate_allocation_given_shortage(
        test_context,
        AllocationInput(
            length_days=30,
            # schaars genoeg dat categorie 4 het tekort draagt, ook met de sloten erbij
            available_source_volume_m3=1_200_000,
            nodes=[
                AllocationNode(
                    name="peilhandhaving",
                    percentage_open_water=3.5,
                    drawdown_available_m=0.30,
                    area_ha=2000,
                    deficit_mm_per_day=2,
                    intake_capacity_m3_per_sec=2.0,
                    demand_post="peilbeheer",
                ),
                AllocationNode(
                    name="landbouw",
                    percentage_open_water=3.5,
                    drawdown_available_m=0.30,
                    area_ha=2000,
                    deficit_mm_per_day=2,
                    intake_capacity_m3_per_sec=2.0,
                    demand_post="beregening",
                ),
            ],
        ),
    )
    assert set(result.coverage_per_demand_post) == {"peilbeheer", "beregening"}
    # categorie 1 gaat voor, en dat is niet een weging maar een ondoordringbare schil
    assert result.coverage_per_demand_post["peilbeheer"] == pytest.approx(1.0)
    assert result.coverage_per_demand_post["beregening"] < 1.0
    assert result.binding_category == 4

    caveat = next(
        item for item in result.caveats if "categorie per vraagpost" in item.topic
    )
    assert "onomkeerbare schade" in caveat.what


def test_a_post_next_to_a_different_category_is_refused():
    """Een post en een categorie die iets anders zeggen: dan stuurt er een, en welke?

    Zeggen ze hetzelfde, dan is er geen tegenspraak en wordt de aanroep gewoon geaccepteerd -
    anders zou een knoop die twee keer valideert zichzelf weigeren.
    """
    with pytest.raises(ModelRetry) as error:
        AllocationNode(
            name="polder",
            percentage_open_water=3.5,
            drawdown_available_m=0.30,
            area_ha=100,
            deficit_mm_per_day=2,
            intake_capacity_m3_per_sec=1.0,
            demand_post="peilbeheer",
            category=4,
        )
    message = str(error.value)
    assert "peilbeheer" in message
    # de melding noemt de categorie die de post draagt, zodat weglaten een keuze is
    assert str(DEMAND_POST_CATEGORY["peilbeheer"]) in message

    agreeing = AllocationNode(
        name="polder",
        percentage_open_water=3.5,
        drawdown_available_m=0.30,
        area_ha=100,
        deficit_mm_per_day=2,
        intake_capacity_m3_per_sec=1.0,
        demand_post="peilbeheer",
        category=DEMAND_POST_CATEGORY["peilbeheer"],
    )
    assert agreeing.category == DEMAND_POST_CATEGORY["peilbeheer"]


def test_a_node_without_any_category_is_refused():
    """Zonder categorie is er geen rangorde en dus niets te verdringen."""
    with pytest.raises(ModelRetry) as error:
        AllocationNode(
            name="polder",
            percentage_open_water=3.5,
            drawdown_available_m=0.30,
            area_ha=100,
            deficit_mm_per_day=2,
            intake_capacity_m3_per_sec=1.0,
        )
    assert "geen categorie" in str(error.value)


@pytest.mark.asyncio
async def test_the_regional_posts_make_the_crowding_out_visible(test_context):
    """Het opgegeven tekort is de beregeningspost; de rest komt uit de regionale verhouding.

    Dit is de uitkomst waar de hele splitsing om gaat. In West is beregening 6 % van de vraag
    en peilbeheer plus doorspoeling de rest, en die rest staat in categorie 1. Bij een aanbod
    dat categorie 1 niet eens dekt, krijgt de landbouw niets - en dat is precies de afweging
    die in de zomer van 2026 in het westen is gemaakt.
    """
    result = await calculate_allocation_given_shortage(
        test_context,
        AllocationInput(
            length_days=90,
            available_source_volume_m3=4_000_000,
            demand_region="West",
            demand_scenario="REF2017",
            demand_return_period=10,
            nodes=[
                AllocationNode(
                    name="polder",
                    percentage_open_water=3.5,
                    drawdown_available_m=0.30,
                    area_ha=4000,
                    deficit_mm_per_day=1.5,
                    intake_capacity_m3_per_sec=2.0,
                    add_regional_demand_posts=True,
                )
            ],
        ),
    )
    # een knoop wordt een doorvoerknoop met vier posten eronder
    assert result.node_count == 5
    assert result.depth == 2
    assert set(result.demand_share_per_post) == set(DEMAND_POSTS)
    assert result.coverage_per_demand_post["peilbeheer"] > 0.0
    assert result.binding_category == 1

    # Beregening krijgt niets UIT DE BRON, en precies wat er in zijn eigen sloten staat. Dat
    # is exact na te rekenen: de voorraad van de polder gaat naar rato van de vraag over de
    # posten, dus de dekking van elke post is de voorraad gedeeld door de totale vraag.
    assert result.coverage_per_demand_post["beregening"] == pytest.approx(
        result.total_storage_m3 / result.total_demand_m3
    )
    assert result.coverage_per_demand_post["beregening"] < 0.01


@pytest.mark.asyncio
async def test_the_regional_posts_scale_the_demand_by_the_irrigation_share(
    test_context,
):
    """De totale vraag is het opgegeven tekort gedeeld door het aandeel van beregening.

    Dat is de enige manier waarop een dimensieloos aandeel een vraag kan opschalen, en het
    maakt de uitspraak controleerbaar: 1,5 mm/dag beregening in een regio waar beregening 6 %
    is, is een totale watervraag van 25 mm/dag.
    """
    shares = demand_posts("West", "REF2017", 10).demand_share
    node = AllocationNode(
        name="polder",
        percentage_open_water=3.5,
        drawdown_available_m=0.30,
        area_ha=4000,
        deficit_mm_per_day=1.5,
        intake_capacity_m3_per_sec=2.0,
        add_regional_demand_posts=True,
    )
    result = await calculate_allocation_given_shortage(
        test_context,
        AllocationInput(
            length_days=90,
            available_source_volume_m3=4_000_000,
            demand_region="West",
            demand_scenario="REF2017",
            demand_return_period=10,
            nodes=[node],
        ),
    )
    expected_mm_per_day = 1.5 / shares["beregening"]
    expected_m3 = expected_mm_per_day * 1e-3 * 4000 * 1e4 * 90
    # de aandelen staan op vier cijfers, dus de som van de posten sluit tot op die afronding
    # en niet exact op het totaal
    assert result.total_demand_m3 == pytest.approx(expected_m3, rel=1e-3)


def test_the_regional_posts_need_a_region():
    """Zonder regio is er geen verhouding, en een landelijk gemiddelde is hier het verkeerde getal."""
    with pytest.raises(ModelRetry) as error:
        AllocationInput(
            length_days=30,
            nodes=[
                AllocationNode(
                    name="polder",
                    percentage_open_water=3.5,
                    drawdown_available_m=0.30,
                    area_ha=100,
                    deficit_mm_per_day=2,
                    intake_capacity_m3_per_sec=1.0,
                    add_regional_demand_posts=True,
                )
            ],
        )
    assert "demand_region" in str(error.value)


@pytest.mark.asyncio
async def test_the_posts_share_the_intake_instead_of_multiplying_it(test_context):
    """Vier posten achter een inlaat is een keel en geen vier kelen.

    Zouden de posten de capaciteit elk als eigen keel meenemen, dan zou het uitsplitsen van
    de vraag de inlaat verviervoudigen - en dan zou een indeling in posten stil meer water
    door het kunstwerk laten dan er in werkelijkheid door past.
    """
    common = dict(
        length_days=90,
        demand_region="West",
        demand_scenario="REF2017",
        demand_return_period=10,
    )
    node = dict(
        name="polder",
        area_ha=4000,
        percentage_open_water=3.5,
        drawdown_available_m=0.30,
        deficit_mm_per_day=1.5,
        # een keel die ruim onder de opgeschaalde vraag ligt, zodat hij bindt
        intake_capacity_m3_per_sec=0.5,
        add_regional_demand_posts=True,
    )
    limited = await calculate_allocation_given_shortage(
        test_context,
        AllocationInput(**common, nodes=[AllocationNode(**node)]),
    )
    # De inlaat bindt, en dan is wat er door de keel gaat precies EEN keel maal de tijd. De
    # eigen voorraad van de polder komt daar bovenop: die hoeft niet door de inlaat.
    assert limited.binding_is_capacity_not_availability
    assert limited.total_granted_m3 == pytest.approx(
        0.5 * 90 * 86_400 + limited.total_storage_m3, rel=1e-6
    )

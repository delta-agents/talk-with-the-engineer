"""De voorraad op de verdeeltool: de peilband, en hoeveel dagen die dekt.

Een bergingsgebied is geen nieuw knooptype maar een knoop met veel open water en geen eigen
vraag. Wat hier wordt vastgelegd:

* de voorraad is narekenbaar met twee vermenigvuldigingen: 300 ha maal 60 % maal 1,10 m is
  1,98 miljoen m3, en dat is wat er over de Nieuwe Driemanspolder gemeld is;
* eerst de eigen vraag, dan de pot - een polder houdt zijn slootwater, een berging deelt het;
* de dagen die je ermee koopt zijn een deling en geen doorrekening;
* een peilband van nul geeft het antwoord van een tool die geen voorraad kent, en de balans
  sluit met de voorraad erin;
* de voorraad levert nooit meer dan hij groot is, en het antwoord noemt zijn prijs.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import AllocationInput, AllocationNode
from talk_with_the_engineer.tools import calculate_allocation_given_shortage

MILLION = 1e6
DAYS = 14
SOURCE_M3 = 9 * MILLION

# De verdeling waarmee de zomer van 2026 is nagemeten: peilhandhaving in categorie 1,
# landbouw in categorie 4, en een bron die de twee samen niet dekt.
DIKES = {
    "name": "peilhandhaving boezem",
    "area_ha": 8000,
    "percentage_open_water": 3.5,
    "drawdown_available_m": 0.30,
    "deficit_mm_per_day": 4,
    "intake_capacity_m3_per_sec": 10.0,
    "demand_post": "peilbeheer",
}
FARMLAND = {
    "name": "landbouw",
    "area_ha": 18000,
    "percentage_open_water": 3.5,
    "drawdown_available_m": 0.30,
    "deficit_mm_per_day": 4,
    "intake_capacity_m3_per_sec": 10.0,
    "demand_post": "beregening",
}
# De Nieuwe Driemanspolder: 300 ha, ongeveer 60 % water, 1,10 m volgezet, geen eigen gewas.
STORAGE_AREA = {
    "name": "berging",
    "area_ha": 300,
    "percentage_open_water": 60.0,
    "drawdown_available_m": 1.10,
    "deficit_mm_per_day": 0,
    "category": 1,
    "intake_capacity_m3_per_sec": 10.0,
}


def _input(nodes, **overrides) -> AllocationInput:
    return AllocationInput(
        **{
            "nodes": nodes,
            "length_days": DAYS,
            "available_source_volume_m3": SOURCE_M3,
            **overrides,
        }
    )


def _without_storage(node) -> dict:
    return {**node, "drawdown_available_m": 0.0}


# --- de voorraad is narekenbaar -------------------------------------------------------


def test_the_store_is_two_multiplications():
    """Oppervlak maal open water maal peilband, en niets anders.

    Dit getal is de reden dat een berging in deze primitieven al bestond: het gemelde volume
    van de Nieuwe Driemanspolder komt eruit op twee cijfers, zonder dat er een begrip bij
    hoeft.
    """
    node = AllocationNode(**STORAGE_AREA)
    assert node.storage_m3 == pytest.approx(300 * 1e4 * 0.60 * 1.10)
    assert node.storage_m3 / MILLION == pytest.approx(1.98, abs=0.005)


def test_the_two_field_level_band_is_refused_instead_of_swallowed():
    """ "1,10 m peilopzet" is hoe erover gesproken wordt, en het veld bestaat hier niet.

    Zou pydantic het stil slikken, dan staat de voorraad op nul en ziet het antwoord er
    verder normaal uit - precies de faalmodus die een stille nul zo gevaarlijk maakt.
    """
    with pytest.raises(ModelRetry) as error:
        AllocationNode(
            name="berging",
            area_ha=300,
            percentage_open_water=60.0,
            target_level_rise_m=1.10,
            deficit_mm_per_day=0,
            category=1,
            intake_capacity_m3_per_sec=10.0,
        )
    assert "drawdown_available_m" in str(error.value)


# --- eerst de eigen vraag, dan de pot -------------------------------------------------


@pytest.mark.asyncio
async def test_an_area_with_demand_keeps_its_own_water(test_context):
    """Wie zelf vraag heeft, deelt niets: zijn sloten dekken zijn eigen tekort."""
    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND])
    )
    expected = (8000 + 18000) * 1e4 * 0.035 * 0.30
    assert result.total_storage_m3 == pytest.approx(expected)
    assert result.storage_for_own_demand_m3 == pytest.approx(expected)
    assert result.storage_shared_m3 == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_an_area_without_demand_shares_everything(test_context):
    """En dat is wat een berging IS: veel open water, geen gewas, dus alles gaat naar de rest."""
    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND, STORAGE_AREA])
    )
    assert result.storage_shared_m3 == pytest.approx(300 * 1e4 * 0.60 * 1.10)
    # en de anderen houden nog steeds hun eigen slootwater
    assert result.storage_for_own_demand_m3 == pytest.approx(
        (8000 + 18000) * 1e4 * 0.035 * 0.30
    )


@pytest.mark.asyncio
async def test_the_shared_store_reaches_the_lower_category(test_context):
    """De berging bedient wie er tekortkomt, en de dijken stonden al vol.

    Dat is de uitkomst waar de zomer van 2026 om vroeg: met de berging erbij gaat er meer
    naar de landbouw, en categorie 1 verandert niet omdat die niets tekortkwam.
    """
    without = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND])
    )
    with_storage = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND, STORAGE_AREA])
    )
    assert with_storage.coverage_per_demand_post["peilbeheer"] == pytest.approx(1.0)
    assert (
        with_storage.coverage_per_demand_post["beregening"]
        > without.coverage_per_demand_post["beregening"]
    )
    assert with_storage.total_shortfall_m3 < without.total_shortfall_m3


# --- de dagen die je ermee koopt ------------------------------------------------------


@pytest.mark.asyncio
async def test_the_days_are_a_division_anyone_can_check(test_context):
    """Voorraad gedeeld door het tekort per dag dat er zonder haar zou zijn.

    Dit is het getal waarin een waterschap over een berging praat, en het is met een
    rekenmachine na te lopen. Rijnland noemde in 2026 zeven tot tien dagen; deze selectie
    geeft dezelfde orde.
    """
    bare = await calculate_allocation_given_shortage(
        test_context,
        _input([_without_storage(DIKES), _without_storage(FARMLAND)]),
    )
    shortfall_per_day = bare.total_shortfall_m3 / DAYS

    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND])
    )
    assert result.days_of_shortfall_covered == pytest.approx(
        result.total_storage_m3 / shortfall_per_day, rel=1e-6
    )
    assert 5 < result.days_of_shortfall_covered < 8


@pytest.mark.asyncio
async def test_no_store_means_no_days_to_buy(test_context):
    """Zonder voorraad is er niets te kopen, en dan staat er geen getal maar null."""
    result = await calculate_allocation_given_shortage(
        test_context,
        _input([_without_storage(DIKES), _without_storage(FARMLAND)]),
    )
    assert result.total_storage_m3 == pytest.approx(0.0)
    assert result.days_of_shortfall_covered is None


@pytest.mark.asyncio
async def test_no_shortfall_means_no_days_either(test_context):
    """En als er zonder voorraad ook geen tekort was, zijn er geen dagen gekocht."""
    result = await calculate_allocation_given_shortage(
        test_context,
        _input([DIKES, FARMLAND], available_source_volume_m3=100 * MILLION),
    )
    assert result.total_storage_m3 > 0.0
    assert result.days_of_shortfall_covered is None


# --- de eerlijkheidstoetsen ----------------------------------------------------------


@pytest.mark.asyncio
async def test_a_level_band_of_zero_is_a_tool_without_a_store(test_context):
    """Nul is een keuze en geen stilte: dan is er geen voorraad en telt alleen de bron."""
    result = await calculate_allocation_given_shortage(
        test_context,
        _input([_without_storage(DIKES), _without_storage(FARMLAND)]),
    )
    assert result.total_storage_m3 == pytest.approx(0.0)
    assert result.total_granted_m3 == pytest.approx(SOURCE_M3)
    assert result.priceless == []
    topics = {caveat.topic for caveat in result.caveats}
    assert not any("voorraad" in topic for topic in topics)


@pytest.mark.asyncio
async def test_the_balance_closes_with_the_store_in_it(test_context):
    """Vraag = toegewezen + onvervuld, en de voorraad zit in het toegewezen deel.

    Zonder deze toets zou de voorraad de vraag stil kunnen verlagen, en dan lijkt een gebied
    met veel sloten minder te vragen in plaats van meer te kunnen.
    """
    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND, STORAGE_AREA])
    )
    assert result.total_demand_m3 == pytest.approx(
        result.total_granted_m3 + result.total_shortfall_m3
    )
    # de vraag is die van de gebieden zelf, en niet wat er na hun voorraad overblijft
    assert result.total_demand_m3 == pytest.approx((8000 + 18000) * 1e4 * 4e-3 * DAYS)


@pytest.mark.asyncio
async def test_the_store_never_delivers_more_than_it_holds(test_context):
    """De voorraad is een hoeveelheid en geen bron die blijft leveren.

    Bij een lege bron is alles wat er omgaat precies de voorraad - niet meer, en niet minder
    dan wat er aan vraag tegenover staat.
    """
    result = await calculate_allocation_given_shortage(
        test_context,
        _input([DIKES, FARMLAND, STORAGE_AREA], available_source_volume_m3=0.0),
    )
    assert result.total_granted_m3 == pytest.approx(result.total_storage_m3)


@pytest.mark.asyncio
async def test_the_answer_names_what_the_level_band_costs(test_context):
    """Geen bedrag, wel een prijs - en bij een bergingsgebied twee keer dezelfde centimeters.

    Een gebied dat volstaat voor de droogte is niet beschikbaar voor de bui waarvoor het is
    aangelegd. Dat staat in geen enkel getal, dus het hoort in `priceless`.
    """
    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND, STORAGE_AREA])
    )
    posts = {post.topic: post for post in result.priceless}
    assert "de peilband die je inzet" in posts
    costs = posts["de peilband die je inzet"].what_it_costs
    assert "bergingsfunctie" in costs
    assert "110 cm" in costs


@pytest.mark.asyncio
async def test_the_caveats_say_the_store_is_full_and_where_it_sits(test_context):
    """Twee kanttekeningen, en ze noemen allebei de richting waarin het antwoord scheef staat."""
    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND, STORAGE_AREA])
    )
    full = next(item for item in result.caveats if "vol bij het begin" in item.topic)
    assert "te gunstig" in full.consequence
    assert "één getal per seizoen" in full.consequence

    place = next(item for item in result.caveats if "plaats" in item.topic)
    assert "EXACT" in place.consequence
    assert "parallelle takken" in place.consequence


@pytest.mark.asyncio
async def test_without_sharing_there_is_no_place_caveat(test_context):
    """Wie niets deelt, heeft de plaats-kanttekening niet nodig."""
    result = await calculate_allocation_given_shortage(
        test_context, _input([DIKES, FARMLAND])
    )
    topics = {caveat.topic for caveat in result.caveats}
    assert any("vol bij het begin" in topic for topic in topics)
    assert not any("plaats" in topic for topic in topics)

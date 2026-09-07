"""Wat een antwoord over zijn eigen prijs zegt, en over zijn eigen maatvoering.

Drie dingen die niets aan de getallen veranderen en alles aan hoe ze gelezen worden: dat
een maatregel zonder bedrag niet als gratis leest, dat een onhaalbaar doel geen offerte
krijgt, en dat een maatvoering voorbij het optimum dat zelf zegt.
"""

import pytest

from talk_with_the_engineer.core.results import (
    LimitReason,
    SolveStatus,
)
from talk_with_the_engineer.interface.schemas.retain import (
    RetentionInputGivenArea,
)
from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.interface.schemas.supply import (
    SupplyInputGivenH,
)
from talk_with_the_engineer.interface.tools.retain import (
    calculate_retention_given_area,
)
from talk_with_the_engineer.interface.tools.store import (
    calculate_store_given_h,
)
from talk_with_the_engineer.interface.tools.supply import (
    calculate_supply_given_h,
)

POLDER = {
    "area_ha": 4000,
    "discharge_capacity_m3_per_sec": 5,
    "return_period": 100,
    "percentage_open_water": 3.5,
    "time_of_year": "winter",
}


# --- geen prijs is niet gratis -------------------------------------------------------


@pytest.mark.asyncio
async def test_a_level_margin_lowers_the_cost_and_says_what_it_costs(test_context):
    """Een maatregel die `cost` verlaagt en niets zichtbaars verhoogt, leest als winst.

    De peilmarge werkt inhoudelijk - de benodigde berging zakt van 68 naar 38 ha - en er
    stond niets in de uitvoer dat de lezer eraan herinnerde dat die 30 cm marge tot
    inundatie en bedrijfsvoering kost. `read_me` belooft daar `priceless` voor; dat veld
    bestond alleen in de pakketzoeker en niet in deze uitvoer.
    """
    plain = await calculate_store_given_h(
        test_context, StoreInputGivenH(**POLDER, delta_h_available=1.0)
    )
    with_margin = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, delta_h_available=1.0, level_margin_m=0.3),
    )

    assert with_margin.measure.delta < plain.measure.delta
    assert with_margin.cost < plain.cost
    assert plain.priceless == []

    posts = {post.topic: post for post in with_margin.priceless}
    assert "peilmarge" in posts
    assert "30 cm" == posts["peilmarge"].magnitude
    assert "drooglegging" in posts["peilmarge"].what_it_costs.lower()


@pytest.mark.asyncio
async def test_raising_the_target_level_is_reported_as_priceless_too(test_context):
    """Peilopzet kost drooglegging EN water, en dat zijn twee posten.

    De eerste is de prijs die je op het land betaalt: een hoger streefpeil is minder marge
    tot inundatie en landbouwschade. De tweede is de prijs die je in de zomer betaalt: een
    verhoogd peil verdampt en infiltreert weg en moet worden aangevuld. In de landelijke
    werkopgave is peilopzet daarom een VRAAGpost, waar hij hier een maatregel is - en zolang
    het antwoord er maar een van de twee noemt, leest de opzet als voorraad zonder rekening.
    """
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**POLDER, delta_h_available=1.0, target_level_rise_m=0.2),
    )
    posts = {post.topic: post for post in result.priceless}
    assert set(posts) == {"peilopzet", "water voor peilhandhaving"}
    assert "drooglegging" in posts["peilopzet"].what_it_costs.lower()
    assert "water" in posts["water voor peilhandhaving"].what_it_costs.lower()
    assert posts["water voor peilhandhaving"].magnitude == "20 cm"


@pytest.mark.asyncio
async def test_supply_has_no_cost_and_says_why(test_context):
    """Wat aanvoer kost is het water en niet het kunstwerk, en dat hoort in het antwoord."""
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            area_ha=4000,
            deficit_mm_per_day=4,
            drawdown_available_m=0.3,
        ),
    )
    topics = {post.topic for post in result.priceless}
    assert "aanvoeren" in topics
    # de bruikbare diepte onder streefpeil is op de droge kant dezelfde centimeter als de
    # peilmarge op de natte, en dus dezelfde niet-monetaire prijs
    assert "bruikbare diepte onder streefpeil" in topics
    # en peilopzet niet: die doen de aanvoertools niets mee, dus een prijs melden voor iets
    # wat dit antwoord niet gebruikt zou een nieuwe stilte zijn in plaats van minder
    assert "peilopzet" not in topics


# --- een onhaalbaar doel krijgt geen offerte -----------------------------------------


@pytest.mark.asyncio
async def test_an_infeasible_target_has_no_cost_but_keeps_the_number(test_context):
    """`after` is daar de grens waarop de maatregel vastloopt, en dus geen advies.

    De handleiding waarschuwt ervoor, en dat werkt zolang de beller de handleiding leest.
    Een bedrag van 521 miljoen euro naast "4000 ha open water" - 100 % van het gebied - leest
    zonder die waarschuwing als een offerte, dus het bedrag hoort hier niet in `cost` te
    staan.
    """
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**POLDER, delta_h_available=0.02)
    )

    assert result.status is SolveStatus.ACTION_INFEASIBLE
    assert result.cost is None
    assert result.cost_range is None
    assert result.cost_at_limit > 0
    assert result.cost_range_at_limit is not None


@pytest.mark.asyncio
async def test_a_feasible_target_keeps_its_cost_where_it_was(test_context):
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**POLDER, delta_h_available=1.0)
    )
    assert result.status is SolveStatus.EXACT
    assert result.cost > 0
    assert result.cost_at_limit is None


# --- voorbij het optimum ------------------------------------------------------------

RETENTION = {
    **POLDER,
    "days_to_discharge": 3,
    "days_to_retain_discharge": 2,
    "length_event_hrs": 96,
    "name_rainfall_pattern": "p1c",
    "rainfall_regime": "R",
}


@pytest.mark.asyncio
async def test_a_sizing_past_the_interior_optimum_says_so(test_context):
    """Duurder EN slechter, en niets in het antwoord wees daarop.

    Het was uitsluitend af te leiden uit `magnitude_optimum_kind: interior` naast
    `magnitude_at_optimum_ha` < `measure.after` - twee velden vergelijken die nergens als
    paar worden geintroduceerd. En juist het binnenoptimum bij vasthouden is het meest
    contra-intuitieve resultaat dat dit model produceert.
    """
    at_optimum = await calculate_retention_given_area(
        test_context, RetentionInputGivenArea(**RETENTION, delta_area_ha=2645)
    )
    beyond = await calculate_retention_given_area(
        test_context, RetentionInputGivenArea(**RETENTION, delta_area_ha=3800)
    )

    # duurder en slechter: dat is wat er te melden valt
    assert beyond.cost > at_optimum.cost
    assert beyond.dh_with_measure_m > at_optimum.dh_with_measure_m

    assert at_optimum.limit_reason is LimitReason.NONE
    assert beyond.limit_reason is LimitReason.PAST_OPTIMUM
    # het antwoord blijft exact: de vraag was "wat doet deze maatvoering", en dat klopt
    assert beyond.status is SolveStatus.EXACT
    # en de betere maatvoering staat in de zin die wordt voorgelezen
    assert "VOORBIJ het optimum" in beyond.description


@pytest.mark.asyncio
async def test_a_plateau_measure_is_not_flagged_as_past_its_optimum(test_context):
    """Bij afvoeren is meer capaciteit verspilling en niet schadelijk; dat is geen vlag."""
    from talk_with_the_engineer.interface.schemas.discharge import (
        DischargeInputGivenDischarge,
    )
    from talk_with_the_engineer.interface.tools.discharge import (
        calculate_discharge_given_discharge,
    )

    result = await calculate_discharge_given_discharge(
        test_context,
        DischargeInputGivenDischarge(
            **POLDER, delta_discharge_capacity_m3_per_sec=40.0
        ),
    )
    assert result.limit_reason is LimitReason.NONE


# --- de tekst spreekt `measure.delta` niet meer tegen --------------------------------


@pytest.mark.asyncio
async def test_a_rounded_magnitude_is_marked_as_approximate(test_context):
    """De zin is een benadering van `measure.delta` en geen tweede, afwijkende bewering.

    Afronden is goed - het model is zwak over maatvoering - maar een afgerond getal dat als
    PUNT wordt gepresenteerd spreekt het veld ernaast tegen. "Ongeveer" ervoor maakt er een
    benadering van hetzelfde getal van.

    Twee significante cijfers en niet een: "10" naast 12,71 zit 21 % te laag, en die
    afronding is niet symmetrisch - zodra het eerste cijfer laag is gaat hij structureel naar
    beneden. Zie `MINIMUM_DIGITS`.
    """
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            area_ha=4000,
            discharge_capacity_m3_per_sec=5,
            return_period=100,
            delta_h_available=1.0,
        ),
    )
    assert result.measure.delta == pytest.approx(12.71, abs=0.01)
    assert "ongeveer 13 ha" in result.description


@pytest.mark.asyncio
async def test_a_magnitude_that_is_not_rounded_away_stays_bare(test_context):
    """Zonder spreiding blijft de zin zoals hij was; "ongeveer" is geen vaste opsmuk.

    Heeft de beller alles ingevuld, dan is er geen parametrische onzekerheid die WIJ
    kennen, en dan wordt er ook niet afgerond - dezelfde discipline als bij de caveats.
    """
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**RETENTION, delta_h_available=1.0)
    )
    assert result.assumptions == []
    assert "ongeveer" not in result.description

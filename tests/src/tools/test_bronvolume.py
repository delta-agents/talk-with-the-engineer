"""Het bronvolume dat met de droogte meebeweegt.

De vraag kwam al uit de statistiek en het aanbod niet, en dat is geen voorzichtige aanname
maar een systematisch te gunstig antwoord: een zeldzamere droogte verhoogde de vraag en liet
het aanbod staan. Deze tests bewaken de twee eigenschappen die dat repareren - dat het
aanbod daalt waar de vraag stijgt, en dat je aan het antwoord kunt zien waardoor het
veranderde.

De genummerde toetsen hieronder verwijzen naar de toetsen
in Sec. 5 van dat plan.
"""

import pytest

from pydantic_ai import ModelRetry

from talk_with_the_engineer.interface.schemas.allocation import (
    AllocationInput,
    AllocationNode,
)
from talk_with_the_engineer.interface.schemas.supply import (
    SupplyInputGivenH,
    SupplyInputGivenSupply,
)
from talk_with_the_engineer.interface.schemas.drought import SOURCE_RIVERS
from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.interface.tools.allocation import (
    calculate_allocation_given_shortage,
)
from talk_with_the_engineer.interface.tools.supply import (
    calculate_supply_given_h,
    calculate_supply_given_supply,
)
from talk_with_the_engineer.core.stats.drought import (
    available_regions,
    available_return_periods,
    available_rivers,
    available_scenarios,
    cumulative_deficit_mm,
    normal_year_discharge_m3_per_sec,
    source_availability,
)

RETURN_PERIODS = (2, 5, 10, 25, 50, 100)

POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "drawdown_available_m": 0.30,
}

DROUGHT = {
    "drought_region": "Rijn_en_IJssel",
    "drought_scenario": "Referentie",
    "drought_return_period": 10,
}

# Ruim bemeten, zodat de bron niet klemt tenzij een test dat wil. Het groeiseizoen van 183
# dagen vraagt bij dit tekort ongeveer 10 mln m3 over de polder.
NORMAL_YEAR_M3 = 40_000_000


def _supply(**overrides):
    return SupplyInputGivenH(**{**POLDER, **DROUGHT, **overrides})


# --- de statistiek zelf (toetsen 1 tot en met 4) ------------------------------------


def test_the_river_list_cannot_drift_from_the_asset():
    """Toets 1. Dezelfde discipline als op de waterschappen en de scenario's.

    De keuzelijst staat in het invoermodel en de waarden staan in het databestand, want een
    import op moduleniveau zou een cykel opleveren. Deze test is wat die duplicatie eerlijk
    houdt.
    """
    assert set(SOURCE_RIVERS) == set(available_rivers())


def test_the_supply_falls_as_the_drought_gets_rarer():
    """Toets 2. Overal, in elk scenario, voor beide rivieren.

    Dit is de eigenschap waar het hele plan om draait. Hij is niet vanzelfsprekend: bij een
    correlatie van ongeveer -0,3 tussen tekort en rivierafvoer levert een ongeklemde fit bij
    een handvol combinaties een stijgende reeks op. Die worden bij het bouwen geklemd, en
    hier wordt vastgelegd dat die klem er is.
    """
    for region in available_regions():
        for scenario in available_scenarios(region):
            for river in available_rivers():
                values = [
                    found.fraction
                    for period in RETURN_PERIODS
                    if (found := source_availability(region, scenario, period, river))
                ]
                assert values, f"{region}/{scenario}/{river} heeft geen enkele waarde"
                assert all(
                    earlier >= later for earlier, later in zip(values, values[1:])
                ), f"{region}/{scenario}/{river} stijgt: {values}"


def test_the_fraction_is_a_fraction():
    """Toets 3. Boven de 1 zou zeggen dat een droogte meer water oplevert dan een normaal jaar."""
    for region in available_regions():
        for scenario in available_scenarios(region):
            for river in available_rivers():
                for period in RETURN_PERIODS:
                    found = source_availability(region, scenario, period, river)
                    if found is None:
                        continue
                    assert 0 < found.fraction <= 1, (region, scenario, river, period)


def test_the_climate_signal_lowers_the_supply_everywhere():
    """Toets 4. Hetzelfde signaal als aan de vraagkant, met het teken om.

    En de verhouding tussen de twee assen is de inhoudelijke uitkomst van dit werk: het
    scenario doet meer met het AANBOD dan de zeldzaamheid van de droogte, terwijl het aan de
    vraagkant andersom ligt. Vraag en aanbod lopen dus langs verschillende assen uit elkaar.
    """
    for region in available_regions():
        reference = source_availability(region, "Referentie", 10, "Rijn")
        warmer = source_availability(region, "Hd_2100", 10, "Rijn")
        assert warmer.fraction < reference.fraction, region

    scenario_effect = (
        source_availability("Rijn_en_IJssel", "Referentie", 10, "Rijn").fraction
        / source_availability("Rijn_en_IJssel", "Hd_2100", 10, "Rijn").fraction
    )
    return_period_effect = (
        source_availability("Rijn_en_IJssel", "Referentie", 2, "Rijn").fraction
        / source_availability("Rijn_en_IJssel", "Referentie", 100, "Rijn").fraction
    )
    assert scenario_effect > return_period_effect


def test_the_normal_year_is_national_and_not_regional():
    """De rivier is voor iedereen dezelfde rivier; alleen de koppeling is regionaal.

    De Maas is bovendien ruim een orde kleiner dan de Rijn, en dat is precies waarom de tool
    naar de rivier vraagt in plaats van er een te kiezen.
    """
    rhine = normal_year_discharge_m3_per_sec("Rijn")
    meuse = normal_year_discharge_m3_per_sec("Maas")
    assert rhine > 10 * meuse

    for river in available_rivers():
        assert normal_year_discharge_m3_per_sec(river) > 0


def test_an_unknown_river_is_an_error_and_not_a_silent_none():
    """Een tikfout is een fout in de aanroep, geen ontbrekende statistiek."""
    with pytest.raises(KeyError, match="onbekende rivier"):
        source_availability("Rijn_en_IJssel", "Referentie", 10, "Schelde")
    with pytest.raises(KeyError, match="onbekende rivier"):
        normal_year_discharge_m3_per_sec("Schelde")


def test_the_supply_is_missing_exactly_where_the_drought_is():
    """Toets 9, in het bestand. Waar geen droogte staat, hoort ook geen aanbod te staan.

    Anders zou de tool een aanbod adverteren bij een herhaaltijd die hij weigert door te
    rekenen, en dat is de soort dubbelzinnigheid waar de drie uitkomsten van
    `cumulative_deficit_mm` juist voor bedoeld zijn.
    """
    for region in available_regions():
        for scenario in available_scenarios(region):
            for period in available_return_periods():
                deficit = cumulative_deficit_mm(region, scenario, period)
                for river in available_rivers():
                    found = source_availability(region, scenario, period, river)
                    assert (deficit is None) == (found is None), (
                        region,
                        scenario,
                        river,
                        period,
                    )


# --- aan de toolgrens ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_and_supply_move_apart_with_the_return_period(test_context):
    """Toets 5. De reden dat dit werk bestaat, als uitvoerbare bewering.

    Dezelfde polder, dezelfde bron, alleen een zeldzamere droogte: de vraag loopt op en het
    beschikbare volume loopt terug. Eerder bewoog alleen het eerste.
    """
    answers = [
        await calculate_supply_given_h(
            test_context,
            _supply(
                drought_return_period=period,
                source_volume_normal_year_m3=NORMAL_YEAR_M3,
                source_river="Rijn",
            ),
        )
        for period in (2, 10, 100)
    ]
    demands = [answer.demand_mm for answer in answers]
    sources = [answer.available_source_volume_m3 for answer in answers]

    assert demands[0] < demands[1] < demands[2]
    assert sources[0] > sources[1] > sources[2]
    # en de benodigde inlaat loopt op, want beide bewegingen duwen dezelfde kant op
    capacities = [answer.supply_capacity_m3_per_sec for answer in answers]
    assert capacities[0] < capacities[1] < capacities[2]


@pytest.mark.asyncio
async def test_a_fixed_source_hides_half_the_movement(test_context):
    """Toets 5, van de andere kant: wat er misgaat zonder deze koppeling.

    Met een bronvolume dat op het normale jaar blijft staan, ziet een T100-droogte er
    gunstiger uit dan hij is. Het verschil tussen die twee antwoorden IS de bijdrage van dit
    werk, en het hoort groter dan nul te zijn.
    """
    fixed = await calculate_supply_given_h(
        test_context,
        _supply(drought_return_period=100, available_source_volume_m3=9_000_000),
    )
    moving = await calculate_supply_given_h(
        test_context,
        _supply(
            drought_return_period=100,
            source_volume_normal_year_m3=9_000_000,
            source_river="Rijn",
        ),
    )
    assert moving.available_source_volume_m3 < fixed.available_source_volume_m3
    assert moving.shortfall_mm > fixed.shortfall_mm


@pytest.mark.asyncio
async def test_the_two_branches_exclude_each_other(test_context):
    """Toets 6. Allebei tegelijk is niet te lezen, dus het wordt geweigerd."""
    with pytest.raises(ModelRetry, match="dubbelop"):
        _supply(
            available_source_volume_m3=1_000_000,
            source_volume_normal_year_m3=9_000_000,
            source_river="Rijn",
        )

    with pytest.raises(ModelRetry, match="source_river"):
        _supply(source_volume_normal_year_m3=9_000_000)

    with pytest.raises(ModelRetry, match="source_volume_normal_year_m3"):
        _supply(source_river="Rijn")


def test_a_derived_source_needs_a_drought_to_derive_it_from():
    """Toets 6, de derde vorm: zonder tripel is er geen droogte om af te lezen."""
    with pytest.raises(ModelRetry, match="droogte uit dezelfde statistiek"):
        SupplyInputGivenH(
            **POLDER,
            deficit_mm_per_day=4,
            source_volume_normal_year_m3=9_000_000,
            source_river="Rijn",
        )


@pytest.mark.asyncio
async def test_giving_the_volume_yourself_is_untouched(test_context):
    """Toets 7. De bestaande tak doet wat hij deed, tot op het getal.

    Een nieuwe weg naar hetzelfde veld mag de oude niet verschuiven; de beller die zijn eigen
    volume opgeeft merkt van dit werk niets behalve dat er meer in de uitvoer staat.
    """
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            **POLDER,
            deficit_mm_per_day=4,
            length_days=30,
            available_source_volume_m3=2_000_000,
        ),
    )
    assert result.available_source_volume_m3 == 2_000_000
    assert result.sensitivity == []
    assert "source_statistic" not in result.data
    topics = {caveat.topic for caveat in result.caveats}
    assert "herkomst van het bronvolume" in topics
    assert "het bronvolume komt uit een zwak verband" not in topics


@pytest.mark.asyncio
async def test_an_unlimited_source_stays_the_default(test_context):
    """Toets 8. Geen van beide takken is nog steeds een onbeperkte bron.

    Met de dragende caveat erbij, want dan is de aanname dat het water bij de inlaat staat
    nog steeds precies dat: een aanname.
    """
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(**POLDER, deficit_mm_per_day=4, length_days=30),
    )
    assert result.available_source_volume_m3 is None
    assert result.days_until_source_empty is None
    topics = {caveat.topic for caveat in result.caveats}
    assert "beschikbaarheid van aanvoerwater" in topics


def test_a_return_period_outside_the_series_refuses_instead_of_extrapolating():
    """Toets 9, aan de toolgrens.

    In het natste scenario van Noorderzijlvest wordt T100 in 240 jaar niet gehaald. Dan is er
    geen droogte, en dus ook geen aanbod; een fractie verzinnen zou een getal opleveren waar
    het rapport er geen heeft.
    """
    with pytest.raises(ModelRetry, match="buiten de reeks"):
        SupplyInputGivenH(
            **POLDER,
            drought_region="Noorderzijlvest",
            drought_scenario="Ln_2100",
            drought_return_period=100,
            source_volume_normal_year_m3=9_000_000,
            source_river="Rijn",
        )


@pytest.mark.asyncio
async def test_the_answer_says_when_the_source_runs_dry(test_context):
    """Toets 10. De bron koopt niets meer, en dat hoort te zien te zijn.

    `days_until_source_empty` stond al in de rekenkern en bleef daar hangen. Dat kon zolang
    het volume iets was dat de beller zelf had ingetypt; nu het uit de statistiek komt, is
    een antwoord dat verandert zonder te laten zien waardoor onbruikbaar.
    """
    thin = await calculate_supply_given_h(
        test_context,
        _supply(source_volume_normal_year_m3=4_000_000, source_river="Rijn"),
    )
    assert thin.days_until_source_empty is not None
    assert 0 < thin.days_until_source_empty < thin.data["length_days"]
    assert thin.status is SolveStatus.ACTION_INFEASIBLE
    # en de uitleg wijst de goede klem aan: meer kunstwerk helpt hier niet
    assert "beschikbaarheid en niet in de inlaat" in thin.description

    ample = await calculate_supply_given_h(
        test_context,
        _supply(source_volume_normal_year_m3=NORMAL_YEAR_M3, source_river="Rijn"),
    )
    assert ample.days_until_source_empty is None


@pytest.mark.asyncio
async def test_the_spread_of_the_weak_relation_is_reported(test_context):
    """Toets 11. Bij een correlatie van -0,3 is een puntwaarde te weinig.

    De band staat op twee plekken en dat is geen dubbeling: in `sensitivity` als antwoord aan
    de randen, en in de caveat als reden. Een agent die de een weglaat houdt de ander.
    """
    result = await calculate_supply_given_h(
        test_context,
        _supply(source_volume_normal_year_m3=11_000_000, source_river="Rijn"),
    )
    # de bronband staat naast de rijen voor de weggelaten velden; sinds B11 zijn dat er
    # meer dan een, en de bron is er daar een van
    spread = next(
        item
        for item in result.sensitivity
        if item.field == "available_source_volume_m3"
    )
    assert spread.low_answer != spread.high_answer

    statistic = result.data["source_statistic"]
    low, high = statistic["available_source_volume_range_m3"]
    assert low < result.available_source_volume_m3 < high
    assert statistic["fit_r"] < 0

    topics = {caveat.topic for caveat in result.caveats}
    assert "het bronvolume komt uit een zwak verband" in topics


@pytest.mark.asyncio
async def test_an_unbinding_source_reports_a_spread_of_nothing(test_context):
    """En de andere uitkomst van diezelfde regel, die net zo veel zegt.

    Is de bron ruim, dan is hij aan geen van beide randen de klem en staat er twee keer
    hetzelfde antwoord. Dat is geen lege regel maar de mededeling dat de zwakte van dit
    verband dit antwoord niet raakt - en dat is precies wat een lezer wil weten voordat hij
    zich zorgen maakt over een correlatie van -0,3.
    """
    result = await calculate_supply_given_h(
        test_context,
        _supply(source_volume_normal_year_m3=NORMAL_YEAR_M3, source_river="Rijn"),
    )
    spread = next(
        item
        for item in result.sensitivity
        if item.field == "available_source_volume_m3"
    )
    assert spread.low_answer == spread.high_answer
    assert result.days_until_source_empty is None


@pytest.mark.asyncio
async def test_mass_is_conserved_at_the_tool_boundary(test_context):
    """Toets 12. Er kan niet meer door de inlaat dan er in de bron zit."""
    result = await calculate_supply_given_supply(
        test_context,
        SupplyInputGivenSupply(
            **POLDER,
            **DROUGHT,
            source_volume_normal_year_m3=4_000_000,
            source_river="Maas",
            delta_supply_capacity_l_s_ha=0.5,
        ),
    )
    assert result.source_volume_used_m3 <= result.available_source_volume_m3 * (
        1 + 1e-9
    )
    assert result.source_volume_used_m3 > 0


@pytest.mark.asyncio
async def test_the_allocation_source_follows_the_same_drought(test_context):
    """Toets 5, op systeemschaal. Hier is de bron het onderwerp van de vraag.

    "Vanaf welk aanbod valt landbouw af" is pas een beleidsvraag zodra dat aanbod bij een
    herhaaltijd hoort in plaats van bij een aanname.
    """
    nodes = [
        AllocationNode(
            name="drinkwaterinname",
            percentage_open_water=3.5,
            drawdown_available_m=0.30,
            area_ha=500,
            deficit_mm_per_day=4,
            category=2,
            intake_capacity_m3_per_sec=1.0,
            draws_from="boezem",
        ),
        AllocationNode(
            name="landbouwpolder",
            percentage_open_water=3.5,
            drawdown_available_m=0.30,
            area_ha=4000,
            deficit_mm_per_day=4,
            category=4,
            intake_capacity_m3_per_sec=1.5,
            draws_from="boezem",
        ),
        AllocationNode(
            name="boezem",
            percentage_open_water=3.5,
            drawdown_available_m=0.30,
            area_ha=8000,
            deficit_mm_per_day=0,
            category=4,
            intake_capacity_m3_per_sec=10.0,
        ),
    ]

    answers = [
        await calculate_allocation_given_shortage(
            test_context,
            AllocationInput(
                nodes=nodes,
                length_days=30,
                drought_region="Rijn_en_IJssel",
                drought_scenario="Hd_2050",
                drought_return_period=period,
                source_volume_normal_year_m3=6_000_000,
                source_river="Rijn",
            ),
        )
        for period in (2, 100)
    ]
    mild, rare = answers

    assert rare.available_source_volume_m3 < mild.available_source_volume_m3
    assert rare.theta < mild.theta
    # de vraag is gelijk gebleven, dus de hele beweging komt van de bron
    assert rare.total_demand_m3 == mild.total_demand_m3

    topics = {caveat.topic for caveat in rare.caveats}
    assert "het bronvolume komt uit een zwak verband" in topics
    # en de caveat die zegt dat het volume "een INVOER" is, is hier onwaar geworden
    assert "herkomst van het bronvolume" not in topics

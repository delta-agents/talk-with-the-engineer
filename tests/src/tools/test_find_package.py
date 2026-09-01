"""De pakketzoeker door de toollaag heen: de deur mag het antwoord niet veranderen.

De rekenkern heeft zijn eigen toetsen. Wat hier wordt getoetst is de laag eromheen: dat het
invoermodel dezelfde vraag stelt, dat het uitvoermodel hetzelfde antwoord meldt, en dat de
dingen die een agent makkelijk verkeerd leest - een afgekapte zoektocht, een prijsloze
maatregel, een pakket zonder alternatief - in de uitvoer niet te verwarren zijn.

De ankerwaarden komen uit de rekenkern zelf: elke test die een pakket vastlegt, vergelijkt met
een directe `optimize`-aanroep in plaats van met een ingetypt getal. Zo blijft dit een toets op
de deur en niet een tweede kopie van de rekentoetsen.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import OptimizeInput
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    MeasureRole,
    SolveStatus,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools import find_package_given_protection
from talk_with_the_engineer.tools.toolset_rules_of_thumb.optimize import (
    Constraints,
    optimize,
    used_measures,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.supply import Deficit

REFERENCE = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
    "return_period": 1000,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
    "rainfall_regime": "R",
}
"""De referentiepolder met de bui waarvan de afvoerreeks uit het rekenblad de uitkomst is."""

DROUGHT = {"deficit_mm_per_day": 4.0, "length_days": 30}
"""Vier millimeter per dag over dertig dagen: 120 mm vraag over de polder.

Expliciet en niet uit de statistiek, zodat deze toetsen niet meebewegen met een databestand.
"""


def _input(**overrides) -> OptimizeInput:
    return OptimizeInput(**REFERENCE, **overrides)


def _measures(reading) -> set[str]:
    return {measure.name_nl for measure in reading.measures}


def _kern(input: OptimizeInput):
    """Dezelfde vraag rechtstreeks aan de rekenkern, als ankerwaarde."""
    state = PolderState.from_water_system_input(input)
    deficit = (
        None
        if input.deficit_mm_per_day is None
        else Deficit(input.deficit_mm_per_day, input.length_days)
    )
    return optimize(
        state,
        input,
        Constraints(
            max_dh_total_m=input.max_dh_total_m,
            min_storage_mm=input.min_storage_mm,
            max_shortfall_mm=input.max_shortfall_mm,
        ),
        deficit=deficit,
    )


# --- het anker: dezelfde vraag, hetzelfde antwoord ----------------------------------


@pytest.mark.asyncio
async def test_the_tool_returns_what_the_core_returns(test_context):
    """De toollaag rapporteert het pakket van de rekenkern, in de eenheden van de maatregel."""
    input = _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    output = await find_package_given_protection(test_context, input)
    expected = _kern(input)

    assert output.status is SolveStatus.EXACT
    assert _measures(output.best) == set(used_measures(expected.best))
    assert output.best.cost == pytest.approx(expected.best.cost)
    assert output.best.dh_total_m == pytest.approx(expected.best.dh_total_m)
    assert output.best.storage_mm == pytest.approx(expected.best.storage_mm)
    for measure in output.best.measures:
        assert measure.magnitude == pytest.approx(
            expected.best.quantities[measure.name_nl], rel=1e-3
        )


@pytest.mark.asyncio
async def test_the_second_requirement_changes_the_package(test_context):
    """De kerntest, door de toollaag: de voorraadeis brengt een maatregel erbij.

    Afvoeren koopt geen voorraad en peilopzet wel, dus de eis die over de peilband gaat kan
    niet met een groter gemaal worden gehaald. Op de rangorde en niet op de maatvoering: dat
    is de robuuste uitspraak.
    """
    only_flooding = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0)
    )
    both = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    assert _measures(only_flooding.best) == {"afvoeren"}
    assert _measures(both.best) == {"afvoeren", "peilopzet"}
    assert both.best.cost > only_flooding.best.cost
    assert "peilopzet" in both.best.priceless


@pytest.mark.asyncio
async def test_the_drought_requirement_on_the_water_level_axis_brings_in_supply(
    test_context,
):
    """Aanvoeren doet alleen mee bij een eis die over de tijd loopt.

    De statische voorraadeis leest geen inlaat, dus daar blijft aanvoeren buiten het pakket;
    het onvervulde tekort komt uit een doorrekening en kent hem wel.
    """
    static = await find_package_given_protection(
        test_context, _input(min_storage_mm=20.0, **DROUGHT)
    )
    dynamic = await find_package_given_protection(
        test_context, _input(max_shortfall_mm=50.0, **DROUGHT)
    )

    assert "aanvoeren" not in _measures(static.best)
    assert "aanvoeren" in _measures(dynamic.best)
    assert "aanvoeren" in dynamic.best.priceless


# --- wat een agent makkelijk verkeerd leest -----------------------------------------


@pytest.mark.asyncio
async def test_the_search_is_always_complete(test_context):
    """Alle combinaties van de vijf maatregelen, elke aanroep.

    Hierop rust de betekenis van `problem_infeasible`: "geen pakket" mag alleen "het kan
    niet" betekenen zolang er niets buiten de zoektocht is gebleven.
    """
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0)
    )

    assert output.data["mixes_examined"] == 31, "vijf maatregelen geven 31 combinaties"


@pytest.mark.asyncio
async def test_an_impossible_pair_of_requirements_is_reported_as_impossible(
    test_context,
):
    """Zonder begrenzing is "het kan niet" wel aangetoond, en dan staat erbij hoeveel het scheelt."""
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=0.05, min_storage_mm=500.0)
    )

    assert output.best is None
    assert output.status is SolveStatus.PROBLEM_INFEASIBLE
    assert {miss.requirement for miss in output.missed} == {"inundatie", "voorraad"}
    for miss in output.missed:
        assert miss.missed_by > 0
        assert miss.required == pytest.approx(
            0.05 if miss.requirement == "inundatie" else 500.0
        )


@pytest.mark.asyncio
async def test_a_requirement_that_is_already_met_needs_no_measure(test_context):
    """Een leeg pakket is een antwoord en geen pakket van nul euro."""
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=5.0)
    )

    assert output.status is SolveStatus.NO_MEASURE_NEEDED
    assert output.best.measures == []
    assert "geen maatregel nodig" in output.description
    # De kostenzin hoort hier niet te staan: er is niets gekocht om te prijzen.
    assert "miljoen euro" not in output.description


@pytest.mark.asyncio
async def test_a_priceless_measure_is_reported_and_leaves_no_price_band(test_context):
    """Geen prijs is niet gratis, en een pakket zonder prijs heeft ook geen prijsband."""
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    assert output.best.priceless == ["peilopzet"]
    assert output.best.cost_range is None
    # De epsilon leunt op het GEPRIJSDE deel en blijft dus staan: over het gemaal weten we
    # nog steeds wat we weten. Nul zou hij pas zijn als niets in het pakket een prijs heeft.
    assert output.cost_epsilon > 0.0
    posts = {post.topic: post for post in output.priceless}
    assert "peilopzet" in posts
    assert "drooglegging" in posts["peilopzet"].what_it_costs.lower()
    assert "m peilopzet" in posts["peilopzet"].magnitude


@pytest.mark.asyncio
async def test_the_alternatives_do_not_repeat_the_answer(test_context):
    """`near_optimal` gaat over ANDERE pakketten; een kopie van `best` verbergt dat er geen zijn."""
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    chosen = _measures(output.best)
    for reading in output.near_optimal + output.indistinguishable_as_replacement:
        assert _measures(reading) != chosen


@pytest.mark.asyncio
async def test_the_region_is_reported_next_to_the_point(test_context):
    """De rol per maatregel is de uitspraak die houdt, en `absent` is niet "te duur"."""
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    roles = {reading.name_nl: reading.role for reading in output.ranges}
    assert set(roles) == {
        "vasthouden",
        "bergen",
        "afvoeren",
        "peilopzet",
        "aanvoeren",
    }
    assert roles["afvoeren"] is MeasureRole.FORCED
    assert roles["peilopzet"] is MeasureRole.FORCED
    for reading in output.ranges:
        if reading.role is MeasureRole.ABSENT:
            assert reading.magnitude_max == 0.0
        else:
            assert reading.magnitude_min <= reading.magnitude_max
    assert "draagt" in output.description or "bijdragen" in output.description


@pytest.mark.asyncio
async def test_the_full_list_of_combinations_is_behind_a_flag(test_context):
    """Standaard staat er het antwoord; de sweep-informatie kost een expliciete vraag."""
    beknopt = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0)
    )
    volledig = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, detail=True)
    )

    assert beknopt.packages == []
    assert len(volledig.packages) == 31, (
        "vijf maatregelen geven eenendertig combinaties"
    )
    assert any(not reading.feasible for reading in volledig.packages)
    assert volledig.best.cost == pytest.approx(beknopt.best.cost)


@pytest.mark.asyncio
async def test_the_answer_carries_the_assumptions_it_leans_on(test_context):
    """Wat de beller weglaat, staat in `assumptions`; wat hij invult niet."""
    output = await find_package_given_protection(
        test_context,
        OptimizeInput(
            area_ha=4000,
            discharge_capacity_m3_per_sec=5,
            return_period=100,
            max_dh_total_m=1.0,
        ),
    )

    assumed = {assumption.field for assumption in output.assumptions}
    assert "time_of_year" in assumed
    assert "percentage_open_water" in assumed
    # Zonder droogte-eis doet het venster niets, en dan is het ook geen aanname.
    assert "length_days" not in assumed
    assert "return_period" not in assumed


# --- de vraag verkeerd stellen wordt uitgelegd en niet geraden ----------------------


def test_a_search_without_a_requirement_is_refused():
    """Zonder eis is het goedkoopste pakket altijd niets doen."""
    with pytest.raises(ModelRetry, match="minstens een eis"):
        _input()


def test_the_shortfall_requirement_needs_a_drought():
    """Er is geen tekort te meten zonder droogte om het op te meten."""
    with pytest.raises(ModelRetry, match="vraagt om een droogte"):
        _input(max_shortfall_mm=50.0)


def test_a_deficit_next_to_a_chosen_drought_is_refused():
    """Twee bronnen voor hetzelfde getal maakt onzichtbaar welke het antwoord stuurt."""
    with pytest.raises(ModelRetry, match="dubbelop"):
        _input(
            max_shortfall_mm=50.0,
            deficit_mm_per_day=4.0,
            drought_region="Rijn_en_IJssel",
            drought_scenario="Referentie",
            drought_return_period=10,
        )


def test_the_drought_statistic_fills_the_deficit_over_the_growing_season():
    """Het tripel levert het tekort, uitgesmeerd over het venster van die statistiek."""
    input = _input(
        max_shortfall_mm=50.0,
        drought_region="Rijn_en_IJssel",
        drought_scenario="Referentie",
        drought_return_period=10,
    )

    assert input.cumulative_deficit_mm is not None
    assert input.length_days == 183, "de statistiek telt op over het groeiseizoen"
    assert input.deficit_mm_per_day == pytest.approx(input.cumulative_deficit_mm / 183)


@pytest.mark.asyncio
async def test_a_wholly_priceless_package_is_not_described_as_free(test_context):
    """Nul euro is geen prijs, en de uitlegzin mag hem ook niet zo noemen.

    Bij een pakket waarin niets een bedrag heeft melden de twee kostenlezingen allebei
    "0,0 miljoen euro". Dat is de zin die een gebruiker voorgelezen krijgt, en hij zegt precies
    het omgekeerde van wat er aan de hand is: aanvoeren kost water, geen euro's.
    """
    output = await find_package_given_protection(
        test_context, _input(max_shortfall_mm=50.0, **DROUGHT)
    )

    assert output.best.cost == 0.0
    assert output.best.priceless == ["aanvoeren"]
    assert "miljoen euro" not in output.description
    assert "geen bedrag" in output.description
    assert "priceless" in output.description
    # En bij een pakket dat WEL iets geprijsd bevat blijven de twee lezingen staan.
    priced = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    assert "vervanging gerekend" in priced.description


@pytest.mark.asyncio
async def test_the_misses_are_per_requirement_and_not_one_package(test_context):
    """Twee overschrijdingen kunnen van twee verschillende combinaties komen.

    Per eis de dichtstbijzijnde die er is, dus ze zijn niet op te tellen tot de afstand van
    een pakket. Een miss hoort alleen in de lijst te staan als die eis werkelijk niet te halen
    is: een eis die wel haalbaar is maar niet samen met de andere, is niet de reden.
    """
    output = await find_package_given_protection(
        test_context, _input(max_dh_total_m=0.05, min_storage_mm=500.0)
    )

    misses = {miss.requirement: miss for miss in output.missed}
    assert set(misses) == {"inundatie", "voorraad"}
    for miss in output.missed:
        # de gemelde overschrijding is werkelijk de kleinste over alle combinaties
        readings = [
            package.dh_total_m
            if miss.requirement == "inundatie"
            else package.storage_mm
            for package in (
                await find_package_given_protection(
                    test_context,
                    _input(max_dh_total_m=0.05, min_storage_mm=500.0, detail=True),
                )
            ).packages
        ]
        best_reading = (
            min(readings) if miss.requirement == "inundatie" else max(readings)
        )
        assert miss.reached == pytest.approx(best_reading, rel=1e-6)


@pytest.mark.asyncio
async def test_a_wholly_priceless_package_has_no_epsilon(test_context):
    """Zit er niets geprijsd in, dan is er geen band en dus geen bijna-optimaal gebied."""
    output = await find_package_given_protection(
        test_context, _input(min_storage_mm=20.0)
    )

    assert output.best.priceless == ["peilopzet"]
    assert output.best.cost == 0.0
    assert output.cost_epsilon == 0.0


@pytest.mark.asyncio
async def test_an_already_raised_polder_only_gets_the_rise_it_still_needs(test_context):
    """Bestaand en extra zijn twee velden, ook bij peilopzet.

    De inundatienorm wordt boven het OORSPRONKELIJKE peil gemeten, dus een polder die al is
    opgezet heeft minder marge over. De maatregel is wat er BOVENOP komt: laat de zoeker de
    bestaande stand niet zien, dan adviseert hij de volle opzet en overschrijdt het pakket de
    norm zodra iemand hem bovenop de bestaande stand uitvoert.
    """
    kaal = await find_package_given_protection(
        test_context, _input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    opgezet = await find_package_given_protection(
        test_context,
        _input(max_dh_total_m=1.0, min_storage_mm=20.0, target_level_rise_m=0.2),
    )

    def opzet(output):
        return next(
            m.magnitude for m in output.best.measures if m.name_nl == "peilopzet"
        )

    # twintig centimeter die er al staat, is twintig centimeter die niet meer hoeft
    assert opzet(kaal) - opzet(opgezet) == pytest.approx(0.2, abs=5e-3)
    # en de eisen worden in beide gevallen op de grens gehaald, niet erlangs
    for output in (kaal, opgezet):
        assert output.best.dh_total_m == pytest.approx(1.0, abs=1e-3)
        assert output.best.storage_mm >= 20.0 - 1e-6


def test_the_searcher_sizes_the_rise_on_top_of_the_existing_one():
    """De bestaande stand is invoer, de opzet erbovenop is de maatregel."""
    assert "target_level_rise_m" in OptimizeInput.model_fields
    assert "level_margin_m" in OptimizeInput.model_fields

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

from talk_with_the_engineer.interface.schemas.optimize import OptimizeInput
from talk_with_the_engineer.core.results import (
    MeasureRole,
    SolveStatus,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.interface.tools.find_package import (
    find_package_given_protection,
)
from talk_with_the_engineer.core.package import (
    Constraints,
    optimize,
    used_measures,
)
from talk_with_the_engineer.interface.tools.supply import Deficit

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


def optimize_input(**overrides) -> OptimizeInput:
    return OptimizeInput(**REFERENCE, **overrides)


def measures(reading) -> set[str]:
    return {measure.name_nl for measure in reading.measures}


def kern_answer(input: OptimizeInput):
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
    input = optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    output = await find_package_given_protection(test_context, input)
    expected = kern_answer(input)

    assert output.status is SolveStatus.EXACT
    assert measures(output.best) == set(used_measures(expected.best))
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
        test_context, optimize_input(max_dh_total_m=1.0)
    )
    both = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    assert measures(only_flooding.best) == {"afvoeren"}
    assert measures(both.best) == {"afvoeren", "peilopzet"}
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
        test_context, optimize_input(min_storage_mm=20.0, **DROUGHT)
    )
    dynamic = await find_package_given_protection(
        test_context, optimize_input(max_shortfall_mm=50.0, **DROUGHT)
    )

    assert "aanvoeren" not in measures(static.best)
    assert "aanvoeren" in measures(dynamic.best)
    assert "aanvoeren" in dynamic.best.priceless


# --- wat een agent makkelijk verkeerd leest -----------------------------------------


@pytest.mark.asyncio
async def test_the_search_is_always_complete(test_context):
    """Alle combinaties van de vijf maatregelen, elke aanroep.

    Hierop rust de betekenis van `problem_infeasible`: "geen pakket" mag alleen "het kan
    niet" betekenen zolang er niets buiten de zoektocht is gebleven.
    """
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0)
    )

    assert output.data["mixes_examined"] == 31, "vijf maatregelen geven 31 combinaties"


@pytest.mark.asyncio
async def test_an_impossible_pair_of_requirements_is_reported_as_impossible(
    test_context,
):
    """Zonder begrenzing is "het kan niet" wel aangetoond, en dan staat erbij hoeveel het scheelt."""
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=0.05, min_storage_mm=500.0)
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
        test_context, optimize_input(max_dh_total_m=5.0)
    )

    assert output.status is SolveStatus.NO_MEASURE_NEEDED
    assert output.best.measures == []
    assert output.ranges == [], (
        "zonder gevraagde maatregel is er geen gebied voor rollen"
    )
    # De zin draagt de twee getallen waarmee de lezer het zelf kan nagaan.
    assert "181 cm" in output.description
    assert "eis 500 cm" in output.description
    assert "geen maatregel nodig" in output.description.lower()
    # De kostenzin hoort hier niet te staan: er is niets gekocht om te prijzen.
    assert "miljoen euro" not in output.description


@pytest.mark.asyncio
async def test_a_priceless_measure_is_reported_and_leaves_no_price_band(test_context):
    """Geen prijs is niet gratis, en een pakket zonder prijs heeft ook geen prijsband."""
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    assert output.best.priceless == ["peilopzet"]
    assert output.best.cost_range is None
    # De epsilon leunt op het GEPRIJSDE deel en blijft dus staan: over het gemaal weten we
    # nog steeds wat we weten. Nul zou hij pas zijn als niets in het pakket een prijs heeft.
    assert output.cost_epsilon > 0.0
    posts = {post.topic: post for post in output.priceless}
    assert "peilopzet" in posts
    assert "drooglegging" in posts["peilopzet"].what_it_costs.lower()
    assert "57 cm als maatregel" in posts["peilopzet"].magnitude


@pytest.mark.asyncio
async def test_the_alternatives_do_not_repeat_the_answer(test_context):
    """`near_optimal` gaat over ANDERE pakketten; een kopie van `best` verbergt dat er geen zijn."""
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    chosen = measures(output.best)
    for reading in output.near_optimal + output.indistinguishable_as_replacement:
        assert measures(reading) != chosen


@pytest.mark.asyncio
async def test_the_region_is_reported_next_to_the_point(test_context):
    """De rol per maatregel is de uitspraak die houdt, en `absent` is niet "te duur"."""
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
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
            assert reading.magnitude_max_source is None
        else:
            assert reading.magnitude_min <= reading.magnitude_max
            assert reading.magnitude_max_source in {"prijsband", "eis", "zoekgrens"}
    reasons = {r.name_nl: r.absent_reason for r in output.ranges if r.absent_reason}
    assert reasons["bergen"] == "buiten_prijsband", (
        "bergen koopt voorraad naast de opzet en valt dus op prijs af, niet op nut"
    )
    assert reasons["aanvoeren"] == "draagt_niet_bij"
    assert "passen niet binnen de prijsband" in output.description
    assert "verbetert geen enkele gestelde eis" in output.description


@pytest.mark.asyncio
async def test_the_full_list_of_combinations_is_behind_a_flag(test_context):
    """Standaard staat er het antwoord; de sweep-informatie kost een expliciete vraag."""
    beknopt = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0)
    )
    volledig = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, detail=True)
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


# --- als het niet kan, zegt het antwoord waarom en hoe ver ---------------------------


@pytest.mark.asyncio
async def test_conflicting_requirements_are_diagnosed_as_a_conflict(test_context):
    """Elk haalbaar, samen niet: dat is een ander gesprek dan "het kan niet".

    De grens per as komt uit een eigen doorrekening die de as zelf optimaliseert; de
    gezamenlijke zoektocht kan die uitspraak niet doen, want die optimaliseert kosten.
    """
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=0.05, min_storage_mm=500.0)
    )

    assert output.status is SolveStatus.PROBLEM_INFEASIBLE
    assert all(miss.alone_feasible for miss in output.missed)
    assert "de eisen conflicteren" in output.description
    inundatie = next(m for m in output.missed if m.requirement == "inundatie")
    assert inundatie.achievable_alone == pytest.approx(0.0, abs=1e-3), (
        "het gemaal kan de stijging naar nul brengen, dus de eis is alleen haalbaar"
    )


@pytest.mark.asyncio
async def test_a_hard_limit_is_reported_with_its_bound(test_context):
    """Een eis die ook alleen niet kan, krijgt de echte grens erbij: verder gaat het niet."""
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=0.05, min_storage_mm=1500.0)
    )

    voorraad = next(m for m in output.missed if m.requirement == "voorraad")
    assert not voorraad.alone_feasible
    assert voorraad.achievable_alone == pytest.approx(1000.0, rel=0.02), (
        "een meter opzet over volledig open water is het fysieke plafond"
    )
    assert "ook op zichzelf niet haalbaar" in output.description
    assert "de eisen conflicteren" not in output.description


# --- de context zonder bedrag krijgt zijn naam, en de epsilon is narekenbaar --------


@pytest.mark.asyncio
async def test_a_given_level_margin_is_named_next_to_its_discount(test_context):
    """Een opgegeven peilmarge maakt het pakket goedkoper en krijgt daarom een post.

    Zonder die post leest de korting als gratis winst, terwijl de marge bedrijfsvoering en
    drooglegging kost - dezelfde discipline die de losse maatregeltools al voeren.
    """
    zonder = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    met = await find_package_given_protection(
        test_context,
        optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0, level_margin_m=0.30),
    )

    assert met.best.cost < zonder.best.cost
    posts = {post.topic: post for post in met.priceless}
    assert "peilmarge" in posts
    assert "30 cm" in posts["peilmarge"].magnitude


@pytest.mark.asyncio
async def test_a_standing_rise_and_the_extra_rise_share_one_post(test_context):
    """Bestaand en extra zijn twee maatvoeringen van hetzelfde onderwerp: één post.

    Twee losse peilopzet-posten zouden als twee maatregelen lezen; de samengevoegde post
    draagt beide getallen en houdt ze uit elkaar.
    """
    output = await find_package_given_protection(
        test_context,
        optimize_input(
            max_dh_total_m=1.0, min_storage_mm=20.0, target_level_rise_m=0.20
        ),
    )

    posts = [post for post in output.priceless if post.topic == "peilopzet"]
    assert len(posts) == 1
    assert "37 cm als maatregel" in posts[0].magnitude
    assert "bovenop de 20 cm" in posts[0].magnitude


@pytest.mark.asyncio
async def test_the_epsilon_can_be_recomputed_from_the_answer(test_context):
    """`cost_epsilon` komt uit een band die het antwoord zelf meegeeft."""
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    low, high = output.priced_cost_range
    assert output.cost_epsilon == pytest.approx((high - low) / output.best.cost)
    # en zonder geprijsde maatregel is er geen band en dus null
    prijsloos = await find_package_given_protection(
        test_context, optimize_input(min_storage_mm=20.0)
    )
    assert prijsloos.priced_cost_range is None
    assert prijsloos.cost_epsilon == 0.0


# --- de description is huisstijl: feiten met getallen, geen lesstof -----------------


@pytest.mark.asyncio
async def test_two_different_answers_share_no_sentence(test_context):
    """Lesstof die elke uitvoer herhaalt, is structureel onmogelijk gemaakt.

    Elke zin hoort bij dit ene antwoord te horen. Delen twee verschillende vragen een
    zin, dan is die zin geen antwoord maar uitleg - en uitleg leeft in het schema en in de
    handleiding, waar hij een keer wordt betaald in plaats van bij elke aanroep. Kort
    gedeeld zinsdeel kan toeval zijn; vandaar de grens op 40 tekens.
    """
    import re

    one = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    other = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=0.6, min_storage_mm=40.0)
    )

    def sentences(text):
        # op zinseinden en niet op puntkomma's: een gemeten bijzin ("aanvoeren verbetert
        # geen enkele gestelde eis") mag tussen twee antwoorden samenvallen, een hele
        # leszin niet
        return {z.strip() for z in re.split(r"(?<=[.!?])\s+", text) if z.strip()}

    shared = {
        sentence
        for sentence in sentences(one.description) & sentences(other.description)
        if len(sentence) > 40
    }
    assert not shared, f"gedeelde lesstof: {shared}"


@pytest.mark.asyncio
async def test_every_sentence_of_an_exact_answer_carries_a_number(test_context):
    """De huisregel van de maatregeltools geldt ook hier: geen zin zonder getal."""
    import re

    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    assert output.status is SolveStatus.EXACT
    for sentence in re.split(r"(?<=[.!?])\s+", output.description):
        if sentence.strip():
            assert re.search(r"\d", sentence), f"zin zonder getal: {sentence!r}"


@pytest.mark.asyncio
async def test_the_english_answer_contains_no_dutch_fragments(test_context):
    """Een Engelse aanroep krijgt een Engelse zin, ook bij een onhaalbare vraag."""
    output = await find_package_given_protection(
        test_context,
        optimize_input(language="en", max_dh_total_m=0.05, min_storage_mm=500.0),
    )
    for fragment in ("tekort", "komt", "eis ", "gemist"):
        assert fragment not in output.description, output.description


# --- de vraag verkeerd stellen wordt uitgelegd en niet geraden ----------------------


@pytest.mark.parametrize(
    "veld, waarde, kern",
    [
        ("max_dh_total_m", -0.5, "negatieve inundatienorm bestaat niet"),
        ("min_storage_mm", -20.0, "altijd gehaald en dus geen eis"),
        ("max_shortfall_mm", -5.0, "negatief tekort bestaat niet"),
        ("deficit_mm_per_day", -4.0, "geen droogte maar een natte periode"),
        ("deficit_mm_per_day", 0.0, "geen droogte maar een natte periode"),
        ("length_days", 0, "droogte van nul dagen is geen droogte"),
        ("days_to_retain_discharge", -2, "kan niet negatief zijn"),
    ],
)
def test_the_advertised_bounds_are_enforced_with_a_reason(veld, waarde, kern):
    """Het schema adverteert grenzen; de runtime handhaaft ze met de reden erbij.

    Zonder handhaving glipt een betekenisloze vraag door met een antwoord dat
    betekenisvol oogt: een negatieve voorraadeis is "al gehaald", een negatief tekort is
    een natte droogte zonder tekort.
    """
    geldig = dict(max_dh_total_m=1.0, max_shortfall_mm=50.0, deficit_mm_per_day=4.0)
    invoer = {k: v for k, v in geldig.items() if k != veld}
    invoer[veld] = waarde
    with pytest.raises(ModelRetry, match=kern):
        optimize_input(**invoer)


def test_the_zero_edges_stay_valid():
    """Nul is bij de eisen een betekenisvolle waarde en blijft dus toegestaan."""
    optimize_input(max_dh_total_m=0.0)
    optimize_input(min_storage_mm=0.0)
    optimize_input(max_shortfall_mm=0.0, deficit_mm_per_day=4.0)


def test_a_search_without_a_requirement_is_refused():
    """Zonder eis is het goedkoopste pakket altijd niets doen."""
    with pytest.raises(ModelRetry, match="minstens een eis"):
        optimize_input()


def test_the_shortfall_requirement_needs_a_drought():
    """Er is geen tekort te meten zonder droogte om het op te meten."""
    with pytest.raises(ModelRetry, match="vraagt om een droogte"):
        optimize_input(max_shortfall_mm=50.0)


def test_a_deficit_next_to_a_chosen_drought_is_refused():
    """Twee bronnen voor hetzelfde getal maakt onzichtbaar welke het antwoord stuurt."""
    with pytest.raises(ModelRetry, match="dubbelop"):
        optimize_input(
            max_shortfall_mm=50.0,
            deficit_mm_per_day=4.0,
            drought_region="Rijn_en_IJssel",
            drought_scenario="Referentie",
            drought_return_period=10,
        )


def test_the_drought_statistic_fills_the_deficit_over_the_growing_season():
    """Het tripel levert het tekort, uitgesmeerd over het venster van die statistiek."""
    input = optimize_input(
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
        test_context, optimize_input(max_shortfall_mm=50.0, **DROUGHT)
    )

    assert output.best.cost == 0.0
    assert output.best.priceless == ["aanvoeren"]
    assert "miljoen euro" not in output.description
    assert "zonder investeringsbedrag" in output.description
    assert "water" in output.description
    assert "priceless" in output.description
    # En een pakket dat WEL iets geprijsd bevat, draagt zijn band over het geprijsde deel.
    priced = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    assert "over het geprijsde deel" in priced.description


@pytest.mark.asyncio
async def test_the_misses_are_per_requirement_and_not_one_package(test_context):
    """Twee overschrijdingen kunnen van twee verschillende combinaties komen.

    Per eis de dichtstbijzijnde die er is, dus ze zijn niet op te tellen tot de afstand van
    een pakket. Een miss hoort alleen in de lijst te staan als die eis werkelijk niet te halen
    is: een eis die wel haalbaar is maar niet samen met de andere, is niet de reden.
    """
    output = await find_package_given_protection(
        test_context, optimize_input(max_dh_total_m=0.05, min_storage_mm=500.0)
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
                    optimize_input(
                        max_dh_total_m=0.05, min_storage_mm=500.0, detail=True
                    ),
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
        test_context, optimize_input(min_storage_mm=20.0)
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
        test_context, optimize_input(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    opgezet = await find_package_given_protection(
        test_context,
        optimize_input(
            max_dh_total_m=1.0, min_storage_mm=20.0, target_level_rise_m=0.2
        ),
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

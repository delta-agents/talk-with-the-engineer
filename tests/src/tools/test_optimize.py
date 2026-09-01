"""De pakketzoeker: het goedkoopste pakket dat aan twee eisen tegelijk voldoet.

De kerntest is `test_the_second_constraint_changes_the_answer`. Met alleen de inundatie-eis
zegt het model "altijd pompen"; met de voorraadeis erbij komt peilopzet erbij, want dat is
de enige maatregel die voorraad direct koopt.

**Welk** pakket het dan wordt, hangt aan een prijs die er niet is, en die drie tests horen
bij elkaar: `test_a_priceless_measure_is_not_free`,
`test_the_switch_price_is_where_the_package_changes` en
`test_the_documented_package_returns_at_its_shadow_price`. Zonder prijs voor peilopzet wint
`{afvoeren, peilopzet}`; vanaf ongeveer 0,14 mln per centimeter komt bergen erbij, en bij
1,5 mln verdwijnt afvoeren. Let op dat die grenzen op een GECONVERGEERD antwoord slaan: een
niet-geconvergeerde optimalisatie schuift ze, en dan lijkt afvoeren eerder te verdwijnen dan
het doet.
"""

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    CAPITALISATION_FACTOR,
    COST_OPEN_WATER,
    DROOGLEGGING_VALUE_VEEN,
    AanvoerenAction,
    AfvoerenAction,
    BergenAction,
    PeilmargeAction,
    PeilopzetAction,
    UnitCost,
    VasthoudenAction,
    peilopzet_unit_cost,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import MeasureRole
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    describe_region,
    describe_step_cost_plateau,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.optimize import (
    DEFAULT_ACTIONS,
    Constraints,
    _finite_difference,
    _package_from,
    cost_epsilon,
    cost_range_of,
    distinct_answers,
    eps_of,
    indistinguishable_under_step_cost,
    optimise_mix,
    optimize,
    outcome_of,
    sweep_measure,
    switch_price_of,
    used_measures,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.supply import Deficit

DEFICIT = Deficit(deficit_mm_per_day=4.0, length_days=30)
"""De droge zomer waartegen de droogte-eis wordt gemeten.

Vier millimeter per dag over dertig dagen is 120 mm vraag over de polder - de orde van een
tekort dat het STOWA-materiaal in `drought_statistics.json` bij lage herhaaltijden geeft.
Expliciet en niet uit de statistiek, zodat de test niet meebeweegt met een databestand.
"""


def _priced_peilopzet(euro_per_metre: float) -> PeilopzetAction:
    """Peilopzet met een hypothetische prijs, zoals een beller hem zou aanleveren."""
    return PeilopzetAction(
        unit_cost=UnitCost(
            typical=euro_per_metre,
            low=euro_per_metre,
            high=euro_per_metre,
            unit="EUR per m peilopzet",
            price_level="hypothetisch",
            source="test",
        )
    )


def _actions_with(action) -> tuple:
    """`DEFAULT_ACTIONS` met een van de vier vervangen, op dezelfde plek.

    De volgorde is niet vrij - `apply` wordt sequentieel toegepast en bergen verandert het
    landoppervlak waar vasthouden zijn fractie tegen rekent. Zie `DEFAULT_ACTIONS`.
    """
    return tuple(
        action if type(existing) is type(action) else existing
        for existing in DEFAULT_ACTIONS
    )


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


@pytest.fixture
def storm():
    return StoreInputGivenH(**REFERENCE, delta_h_available=1.0)


@pytest.fixture
def state(storm):
    return PolderState.from_water_system_input(storm)


def _used(package):
    return {name: value for name, value in package.quantities.items() if value > 0}


# --- de vierde actie ---------------------------------------------------------------


def test_raising_the_target_level_buys_storage_and_spends_inundation_margin(
    state, storm
):
    """Peilopzet is de enige maatregel die voorraad koopt, en hij betaalt in drooglegging.

    Geen euro's: peilopzet kost landbouwschade en functiebeperking, en dat is een
    verdringingsvraagstuk. Maar gratis is hij niet - hij telt op in
    `dh_total_above_original_datum_m`, dus de inundatie-eis rekent hem af. Dat is de
    spanning tussen de natte en de droge eis, mechanisch.
    """
    action = PeilopzetAction(delta_target_level_rise_m=0.20)
    after = action.apply(state)

    assert action.cost(state) is None
    assert after.retained_volume_mm == pytest.approx(0.20 * 0.035 * 1000, abs=1e-9)
    assert state.retained_volume_mm == 0.0

    outcome = outcome_of(state, storm, (action,), [0.20])
    baseline = outcome_of(state, storm, (action,), [0.0]).dh_total_m
    assert outcome.dh_total_m == pytest.approx(baseline + 0.20, abs=1e-9)
    assert outcome.storage_mm > 0
    # en peilopzet meldt zich als prijsloos zodra hij wordt ingezet
    assert outcome.priceless == ("peilopzet",)
    assert outcome_of(state, storm, (action,), [0.0]).priceless == ()


def test_raising_the_target_level_is_not_the_level_margin(state, storm):
    """Twee randen van dezelfde band, twee gedragingen: lineair tegen verzadigend."""
    for rise in (0.1, 0.3, 0.5):
        dh_total = outcome_of(state, storm, (PeilopzetAction(),), [rise]).dh_total_m
        base = outcome_of(state, storm, (PeilopzetAction(),), [0.0]).dh_total_m
        # lineair en onbegrensd
        assert dh_total == pytest.approx(base + rise, abs=1e-9)

    # de marge verzadigt, en dat is precies het verschil
    margins = [
        outcome_of(state, storm, (PeilmargeAction(),), [margin]).dh_total_m
        for margin in (0.1, 0.3, 0.5)
    ]
    assert margins[1] == pytest.approx(margins[2], abs=1e-6)


# --- de gradiënt is expliciet en getest --------------------------------------------


def test_the_gradient_matches_the_closed_form_where_there_is_one(state, storm):
    """`retained_volume_mm` is analytisch in de peilopzet, dus de gradiënt is na te rekenen.

    De afgeleide is `aandeel open water * 1000` = 35 mm per meter opzet. Dat maakt deze test
    een echte controle op de gradiënt en niet een vergelijking van twee benaderingen met
    elkaar.
    """
    actions = (PeilopzetAction(),)

    def storage_at(x):
        return outcome_of(state, storm, actions, x)[2]

    gradient = _finite_difference(storage_at, np.array([0.2]))
    assert gradient[0] == pytest.approx(0.035 * 1000, rel=1e-6)


def test_the_cost_gradient_matches_the_unit_price(state, storm):
    """Bergen is lineair in het areaal, dus de kostengradiënt is de eenheidsprijs."""
    from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
        COST_OPEN_WATER,
    )

    actions = (BergenAction(),)

    def cost_at(x):
        return outcome_of(state, storm, actions, x)[3]

    gradient = _finite_difference(cost_at, np.array([50.0]))
    assert gradient[0] == pytest.approx(COST_OPEN_WATER.typical, rel=1e-6)


# --- de zoektocht zelf -------------------------------------------------------------


def test_one_constraint_picks_the_single_cheapest_measure(state, storm):
    """Met alleen de inundatie-eis is afvoeren bij deze prijzen overal het goedkoopst.

    SLSQP hoeft de eis niet tot op de millimeter te raken. Wat telt is de rangorde: de
    norm wordt gehaald, en het goedkoopste pakket is een groter gemaal.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert result.best is not None
    assert not result.problem_infeasible
    assert set(_used(result.best)) == {"afvoeren"}
    assert result.best.dh_total_m <= 1.0 + 1e-3


def test_the_second_constraint_changes_the_answer(state, storm):
    """De kerntest: de voorraadeis verandert het pakket.

    Afvoeren alleen koopt geen voorraad; peilopzet wel. Zonder prijs voor peilopzet is het
    goedkoopste pakket `{afvoeren, peilopzet}` - de opzet koopt de voorraad en het extra
    gemaal koopt de inundatiemarge terug die de opzet opsnoept.

    Deze test is expliciet over WELK pakket, en dat is geen pietluttigheid. Hij toetste
    eerder alleen `"peilopzet" in used` en `set(used) != {"afvoeren"}`, en beide houden ook
    voor `{afvoeren, peilopzet}` - waardoor de verschuiving van het gedocumenteerde
    `{bergen, peilopzet}` onopgemerkt bleef. De rangorde is de robuuste grootheid, dus die
    hoort vastgelegd; de maatvoering niet.

    Dat dit pakket het wint hangt aan de ONTBREKENDE prijs van peilopzet, niet aan de
    hydrologie: boven ongeveer 0,14 mln per centimeter komt bergen erbij en bij 1,5 mln
    verdwijnt afvoeren. Zie `test_the_switch_price_is_where_the_package_changes` en
    `test_the_documented_package_returns_at_its_shadow_price`.
    """
    only_flooding = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    both = optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))

    assert both.best is not None
    assert not both.problem_infeasible
    assert set(_used(only_flooding.best)) == {"afvoeren"}
    assert set(_used(both.best)) == {"afvoeren", "peilopzet"}

    trits = [
        package
        for package in both.packages
        if package.feasible and set(_used(package)) == {"bergen", "peilopzet"}
    ]
    assert trits, "bergen plus peilopzet hoort op het plateau te staan"

    assert both.best.cost > only_flooding.best.cost
    assert both.best.storage_mm >= 20.0 - 1e-6
    assert both.best.dh_total_m <= 1.0 + 1e-6


def test_storage_alone_is_bought_with_the_two_measures_that_can(state, storm):
    """Zonder inundatie-eis is voorraad het enige doel, en dan is peilopzet gratis."""
    result = optimize(state, storm, Constraints(min_storage_mm=20.0))
    assert result.best is not None
    assert result.best.storage_mm >= 20.0 - 1e-6
    assert "afvoeren" not in _used(result.best)
    # peilopzet kost geen euro's, dus dat is de goedkoopste weg naar voorraad
    assert result.best.cost == pytest.approx(0.0, abs=1.0)


# --- de droogte-eis op de waterstand-as --------------------------------------------


def test_supply_does_nothing_on_the_static_storage_requirement(state, storm):
    """De diagnose van issue #35, als meting.

    `min_storage_mm` is een peil-uitspraak: `retained_volume_mm` kent alleen de peilband.
    Een inlaat verandert die band niet, dus op deze eis is aanvoeren inert - nul effect, en
    daarmee een gradiënt van exact nul. Dat is de reden dat hij er niet zomaar bij kon.
    """
    actions = (AanvoerenAction(),)
    without = outcome_of(state, storm, actions, [0.0])
    with_supply = outcome_of(state, storm, actions, [2.0])

    assert with_supply.storage_mm == without.storage_mm
    assert with_supply.dh_total_m == pytest.approx(without.dh_total_m, abs=1e-12)
    assert with_supply.shortfall_mm is None  # geen droogte meegegeven, geen uitlezing


def test_supply_moves_the_dynamic_shortfall(state, storm):
    """En op de waterstand-as doet hij wél iets, monotoon.

    Dit is de hele omslag van dit plan: dezelfde maatregel, dezelfde toestand, een andere
    eis - en ineens is er een gradiënt om op te zoeken.
    """
    actions = (AanvoerenAction(),)
    shortfalls = [
        outcome_of(state, storm, actions, [capacity], DEFICIT).shortfall_mm
        for capacity in (0.0, 0.5, 1.0, 2.0)
    ]

    assert shortfalls[0] == pytest.approx(120.0, abs=1e-6)
    assert all(later < earlier for earlier, later in zip(shortfalls, shortfalls[1:]))
    assert shortfalls[-1] == pytest.approx(0.0, abs=1e-9)


def test_the_drought_requirement_brings_supply_into_the_package(state, storm):
    """Met de dynamische eis kiest de zoeker aanvoeren, en meldt hem als prijsloos.

    Aanvoeren heeft geen prijs - wat aanvoer kost is water en dat is een verdringingsvraag -
    dus hij verschijnt in `priceless` en niet in `cost`. Dat is dezelfde behandeling die
    peilopzet krijgt, en om dezelfde reden.
    """
    result = optimize(
        state,
        storm,
        Constraints(max_dh_total_m=1.0, max_shortfall_mm=60.0),
        deficit=DEFICIT,
    )

    assert result.best is not None
    assert "aanvoeren" in _used(result.best)
    assert "aanvoeren" in result.best.priceless
    assert result.best.shortfall_mm <= 60.0 + 1e-6
    # de prijs blijft die van de geprijsde maatregelen; aanvoeren telt niet mee als nul
    assert result.best.cost_range is None


def test_the_drought_requirement_needs_a_drought(state, storm):
    """Een eis op een tekort zonder droogte is een vraag zonder belasting."""
    with pytest.raises(ValueError, match="deficit"):
        optimize(state, storm, Constraints(max_shortfall_mm=60.0))


def test_a_priceless_measure_that_does_nothing_is_not_reported_as_used(state, storm):
    """De spookpakket-guard: geen maatvoering zonder werking.

    Een prijsloze maatregel krijgt geen tegendruk van de doelfunctie. Start de zoektocht op
    de bovengrens - wat `optimise_mix` doet als nul niet haalbaar is - dan blijft hij daar
    staan, ook als hij geen enkele eis beweegt. Het pakket meldt dan "aanvoeren 20 m3/s,
    prijs onbekend" terwijl aanvoeren niets doet, en juist `packages` hoort het antwoord
    navolgbaar te maken.

    Bij alleen de inundatie-eis is aanvoeren aantoonbaar inert, dus hij hoort in geen enkel
    pakket te staan - ook niet in de eenendertig mixen die hem aanbieden.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert all(
        package.quantities.get("aanvoeren", 0.0) == 0.0 for package in result.packages
    )
    assert all("aanvoeren" not in package.priceless for package in result.packages)


def test_a_priceless_measure_is_reported_at_its_smallest_working_size(state, storm):
    """De maatvoering van een prijsloze maatregel komt uit de EIS, niet uit de zoeker.

    Zonder prijs is er geen tegendruk van de doelfunctie, dus waar SLSQP zo'n maatregel laat
    staan hangt af van waar hij begon. `_minimise_priceless` legt daar een tweede,
    lexicografische doelfunctie onder: van alle even dure pakketten die de eisen halen, wint
    het pakket dat het minste vraagt van wat geen prijs heeft.

    Meetbaar gevolg: de gekozen inlaat zet het tekort precies OP de eis. Een grotere inlaat
    zou de eis ook halen en niets extra kosten - en dan zou het gerapporteerde getal een
    eigenschap van de zoeker zijn in plaats van van de vraag. Dat is dezelfde belofte als
    invariant I6, een laag hoger.
    """
    result = optimize(
        state,
        storm,
        Constraints(max_dh_total_m=1.0, max_shortfall_mm=60.0),
        deficit=DEFICIT,
    )

    assert "aanvoeren" in _used(result.best)
    # de eis is bindend en niet ruim gehaald
    assert result.best.shortfall_mm == pytest.approx(60.0, abs=1e-3)
    # en kleiner kan aantoonbaar niet: een halve procent minder mist de eis
    smaller = dict(result.best.quantities)
    smaller["aanvoeren"] *= 0.995
    missed = outcome_of(
        state,
        storm,
        DEFAULT_ACTIONS,
        [smaller.get(action.name_nl, 0.0) for action in DEFAULT_ACTIONS],
        DEFICIT,
    )
    assert missed.shortfall_mm > 60.0


def test_the_priceless_size_does_not_depend_on_where_the_search_started(state, storm):
    """Twee mixen die hetzelfde antwoord geven, geven ook dezelfde maatvoering.

    Hier zat de ruis: mixen die op de bovengrens moesten herstarten lieten aanvoeren op een
    andere waarde staan dan mixen die bij nul begonnen, en `distinct_answers` telde dat als
    twee verschillende antwoorden terwijl het verschil in een prijsloze maatregel zat.
    """
    result = optimize(
        state,
        storm,
        Constraints(max_dh_total_m=1.0, max_shortfall_mm=60.0),
        deficit=DEFICIT,
    )

    sizes = {
        round(package.quantities.get("aanvoeren", 0.0), 6)
        for package in result.packages
        if package.feasible and package.quantities.get("aanvoeren", 0.0) > 0
    }
    # een handvol verschillende waarden, elk de kleinste die bij ZIJN mix hoort - en geen
    # wolk van bijna-gelijke getallen uit de optimizer
    assert len(sizes) <= 3


def test_an_infeasible_package_also_drops_an_inert_measure(state, storm):
    """Ook een ONHAALBAAR pakket mag geen maatregel melden die niets doet.

    Dit is de tak die op CI omviel en lokaal niet. `_minimise_priceless` sloeg een onhaalbaar
    pakket over, dus daar bleef aanvoeren staan op de waarde waar SLSQP hem liet - en dat is
    de bovengrens zodra de zoektocht daar moest herstarten. Of dat gebeurt hangt af van waar
    de optimizer op dat platform uitkomt, dus het is een reproduceerbaarheidsprobleem en niet
    alleen een lelijk getal in de uitvoer.

    Hier wordt het pakket direct opgebouwd in plaats van gezocht, zodat de tak wordt geraakt
    ongeacht wat SLSQP op dit platform doet.
    """
    quantities = [0.0, 0.0, 0.0, 0.0, 20.0]  # alleen aanvoeren, op zijn zoekgrens
    package = _package_from(
        state,
        storm,
        DEFAULT_ACTIONS,
        quantities,
        Constraints(max_dh_total_m=0.10),  # onhaalbaar met alleen aanvoeren
        None,
    )

    assert not package.feasible
    assert package.quantities["aanvoeren"] == 0.0
    assert "aanvoeren" not in package.priceless


def test_an_inert_action_adds_no_distinct_answers(state, storm):
    """En daarom verandert een vijfde actie het ANTWOORD niet, alleen het aantal mixen.

    Zonder de guard zou elke mix met aanvoeren een eigen maatvoering krijgen en dus als een
    apart antwoord tellen, terwijl het verschil in een maatregel zit die niets doet.
    """
    four = optimize(
        state, storm, Constraints(max_dh_total_m=1.0), actions=DEFAULT_ACTIONS[:4]
    )
    five = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert len(four.packages) == 15
    assert len(five.packages) == 31
    assert set(_used(five.best)) == set(_used(four.best))
    assert five.best.cost == pytest.approx(four.best.cost, rel=1e-9)
    assert len(five.near_optimal) == len(four.near_optimal)


def test_the_shadow_price_survives_a_drought_requirement(state, storm):
    """`switch_price_of` rekent zelf `optimize` opnieuw uit, dus de droogte moet mee.

    Zonder doorgeven van `deficit` zou die interne aanroep struikelen over zijn eigen
    controle - "max_shortfall_mm vraagt om een deficit" - en dan is de schaduwprijs van
    aanvoeren onbereikbaar juist in de opzet waarin aanvoeren iets doet.

    Klein gehouden (`max_mix_size=1`) omdat dit de doorgifte toetst en niet de economie; de
    volledige zoektocht kost een minuut. Op de referentiecasus ligt het kantelpunt van
    aanvoeren rond 14 mln per m3/s inlaat, en daarboven komt peilopzet in het pakket.
    """
    price = switch_price_of(
        state,
        storm,
        Constraints(max_shortfall_mm=60.0),
        "aanvoeren",
        deficit=DEFICIT,
        max_mix_size=1,
        coarse_points=3,
        refinements=2,
    )

    assert price.measure_nl == "aanvoeren"
    assert "aanvoeren" in price.package_below


def test_raising_the_target_level_also_answers_the_drought_requirement(state, storm):
    """Peilopzet koopt voorraad op beide assen, en dat hoort consistent te zijn.

    Op de peil-as koopt hij `retained_volume_mm`; op de waterstand-as koopt hij bufferdiepte
    waaruit de droge periode kan putten. Zou de klem in `simulate_deficit` alleen de
    peilmarge kennen, dan zou peilopzet hier niets doen en zou de zoeker hem overslaan.
    """
    actions = (PeilopzetAction(),)
    without = outcome_of(state, storm, actions, [0.0], DEFICIT).shortfall_mm
    with_rise = outcome_of(state, storm, actions, [0.20], DEFICIT).shortfall_mm

    # 0,20 m over 3,5 % open water is 7,0 mm voorraad, en precies zoveel minder tekort
    assert without - with_rise == pytest.approx(0.20 * 0.035 * 1000, abs=1e-9)


def test_an_impossible_pair_of_constraints_is_problem_infeasible(state, storm):
    """`PROBLEM_INFEASIBLE` betekent iets anders dan `ACTION_INFEASIBLE`.

    Een voorraad van 500 mm vraagt een halve meter water over de hele polder, en dat kan met
    geen enkel pakket binnen een inundatienorm van 10 cm. Geen enkele mix haalt het, en dat
    is een uitspraak over het probleem en niet over een maatregel.
    """
    result = optimize(
        state, storm, Constraints(max_dh_total_m=0.10, min_storage_mm=500.0)
    )
    assert result.problem_infeasible
    assert result.best is None
    assert len(result.packages) == 31


def test_every_mix_is_reported_so_the_answer_is_traceable(state, storm):
    """Ook de onhaalbare mixen, want anders is het antwoord niet na te lopen."""
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    assert len(result.packages) == 31  # vijf acties, alle niet-lege deelverzamelingen
    assert any(not package.feasible for package in result.packages)
    assert result.best.cost == min(
        package.cost for package in result.packages if package.feasible
    )


def test_limiting_the_mix_size_limits_the_search(state, storm):
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0), max_mix_size=1)
    assert len(result.packages) == 5
    assert all(len(_used(package)) <= 1 for package in result.packages)


def test_no_constraint_is_refused_instead_of_answered(state, storm):
    """Zonder eis is het goedkoopste pakket niets doen, en dat is geen nuttig antwoord."""
    with pytest.raises(ValueError, match="minstens een eis"):
        optimize(state, storm, Constraints())


def test_a_negligible_quantity_is_reported_as_zero(state, storm):
    """0,001 ha is een restje van de zoektocht en geen maatregel.

    Zonder deze opruiming staat er "vasthouden: 0,001" in het pakket en dat leest als een
    keuze. En omdat er na het opschonen opnieuw wordt doorgerekend, hoort de uitkomst die
    erbij staat ook echt bij het gerapporteerde pakket.
    """
    package = optimise_mix(
        state,
        storm,
        (VasthoudenAction(), BergenAction(), AfvoerenAction(), PeilopzetAction()),
        Constraints(max_dh_total_m=1.0, min_storage_mm=20.0),
    )
    for name, quantity in package.quantities.items():
        assert quantity == 0.0 or quantity > 1e-3, f"{name}={quantity}"

    recomputed = outcome_of(
        state,
        storm,
        (VasthoudenAction(), BergenAction(), AfvoerenAction(), PeilopzetAction()),
        [
            package.quantities[name]
            for name in ("vasthouden", "bergen", "afvoeren", "peilopzet")
        ],
    )
    assert recomputed[1] == pytest.approx(package.dh_total_m, abs=1e-12)
    assert recomputed[2] == pytest.approx(package.storage_mm, abs=1e-12)


# --- geen prijs is niet gratis (issue #30) -----------------------------------------


def test_a_priceless_measure_is_not_free(state, storm):
    """Peilopzet heeft geen prijs, en dat is iets anders dan een prijs van nul.

    Eerder zette `outcome_of` de prijs met `or 0.0` op nul. Dat was niet alleen oneerlijk
    in de rapportage maar veranderde de UITKOMST: gratis peilopzet koopt inundatiemarge
    die een groter gemaal terugverdient, en het goedkoopste pakket verschoof daardoor van
    bergen naar afvoeren. Nu staat er wat er ontbreekt.
    """
    result = optimize(
        state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0)
    )

    assert "peilopzet" in used_measures(result.best)
    assert result.best.priceless == ("peilopzet",)
    # geen prijs betekent geen band; een band om een getal dat niet bestaat is erger
    assert result.best.cost_range is None
    # en de gemelde prijs is die van de maatregelen die er wel een hebben
    assert result.best.cost > 0


def test_a_fully_priced_package_carries_its_band(state, storm):
    """Zonder prijsloze maatregel is er wel een band, en die komt uit `UnitCost`."""
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert result.best.priceless == ()
    low, high = result.best.cost_range
    assert low < result.best.cost < high


def test_the_cost_band_is_the_unit_price_band(state, storm):
    """De band is geen verzonnen percentage maar de bron van de eenheidsprijs zelf.

    Bergen staat op -11/+70 % en het gemaal op -3/+6 %; een platte epsilon is dus voor de
    een te ruim en voor de ander te krap. Dat is precies waarom hij hier per maatregel uit
    `UnitCost` komt.
    """
    hectares = 100.0
    band = cost_range_of(state, (BergenAction(),), [hectares])
    assert band == pytest.approx(
        (COST_OPEN_WATER.low * hectares, COST_OPEN_WATER.high * hectares)
    )

    # `cost_range_of` geeft altijd de band over wat er WEL geprijsd is; dat de band als
    # PRIJS VAN HET PAKKET ontbreekt zodra er een prijsloze maatregel in zit, is een
    # uitspraak van `Package` en niet van deze som. Zie de docstring: twee taken, twee velden
    mixed = optimise_mix(
        state,
        storm,
        (BergenAction(), PeilopzetAction()),
        Constraints(max_dh_total_m=1.0, min_storage_mm=20.0),
    )
    assert mixed.priceless == ("peilopzet",)
    assert mixed.cost_range is None
    assert mixed.priced_cost_range[0] < mixed.cost < mixed.priced_cost_range[1]


def test_the_switch_price_is_where_the_package_changes(state, storm):
    """De schaduwprijs: niet de prijs verzinnen, maar hem aflezen.

    Onder ongeveer 0,14 miljoen euro per centimeter peilopzet blijft het antwoord
    `{afvoeren, peilopzet}`; daarboven komt bergen erbij. Dat getal produceert het model,
    en het maakt de politieke variabele bespreekbaar in plaats van dat hij als ontbrekende
    prijs de uitkomst bepaalt.

    Een interval en geen punt, want de grens wordt met bisectie benaderd en de vergelijking
    eronder rust op SLSQP. Wat robuust is, is de ordegrootte.
    """
    switch = switch_price_of(
        state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0), "peilopzet"
    )

    assert switch.changed
    assert switch.unit == "m peilopzet"
    per_cm_low, per_cm_high = switch.price_low / 100, switch.price_high / 100
    assert 0.10e6 < per_cm_low <= per_cm_high < 0.20e6, (per_cm_low, per_cm_high)
    assert switch.package_below == ("afvoeren", "peilopzet")
    assert "bergen" in switch.package_above


def test_a_measure_that_is_not_used_has_no_switch_price(state, storm):
    """Met alleen de inundatie-eis wordt peilopzet niet ingezet, dus verandert een prijs niets."""
    switch = switch_price_of(state, storm, Constraints(max_dh_total_m=1.0), "peilopzet")

    assert not switch.changed
    assert switch.package_below == switch.package_above == ("afvoeren",)


def test_a_priced_measure_has_no_shadow_price(state, storm):
    """Een schaduwprijs is alleen zinvol voor een maatregel die geen prijs heeft."""
    with pytest.raises(ValueError, match="heeft al een prijs"):
        switch_price_of(state, storm, Constraints(max_dh_total_m=1.0), "afvoeren")


def test_the_documented_package_returns_at_its_shadow_price(state, storm):
    """Het oude gedocumenteerde antwoord is het juiste antwoord op een andere vraag.

    Een eerder gepubliceerde kopregel noemde `bergen 190 ha + peilopzet 24 cm` voor
    25,67 mln. Dat was het niet-geconvergeerde antwoord van voor de COST_SCALE-fix - maar
    het komt exact terug zodra een centimeter drooglegging 1,5 miljoen euro waard is. Ter
    plausibiliteit: 24 cm maal 1,5 mln is 36 mln over 4000 ha, dus ruim 9.000 euro per
    hectare, ongeveer een tiende van de agrarische grondwaarde die COST_OPEN_WATER zelf als
    bron noemt.

    Daarmee is de demo-uitspraak niet "afvoeren verdwijnt uit het pakket" maar "afvoeren
    verdwijnt zodra drooglegging meer waard is dan dit" - en dat is een vraag voor het
    waterschap in plaats van een gevolg van een ontbrekende prijs.
    """
    result = optimize(
        state,
        storm,
        Constraints(max_dh_total_m=1.0, min_storage_mm=20.0),
        actions=_actions_with(_priced_peilopzet(1.5e8)),
    )

    used = _used(result.best)
    assert set(used) == {"bergen", "peilopzet"}
    assert used["bergen"] == pytest.approx(190, abs=6)
    assert used["peilopzet"] == pytest.approx(0.24, abs=0.02)
    # met een prijs is peilopzet niet meer prijsloos, dus is er weer een band
    assert result.best.priceless == ()
    assert result.best.cost_range is not None


# --- het gebied in plaats van het punt (issue #30) ----------------------------------


def test_two_tolerances_have_two_units(state, storm):
    """De twee eisen staan in twee eenheden, dus één drempel kan niet.

    `binding` deed `abs(margin) <= 1e-3` over een dict met de inundatiemarge in METER en de
    voorraadmarge in MILLIMETER - dus 1 mm op de stand en 1 micrometer op de voorraad. De
    tweede leidt zich nu af uit de eerste: 1 mm peilopzet koopt bij 3,5 % open water
    0,035 mm voorraad, dus dat is dezelfde fysieke uitspraak.
    """
    eps = eps_of(state)
    assert eps["inundatie"] == pytest.approx(1e-3)
    assert eps["voorraad"] == pytest.approx(0.035)

    # en hij schaalt mee met de polder in plaats van een afgesproken getal te zijn
    wider = PolderState.from_water_system_input(
        StoreInputGivenH(
            **{**REFERENCE, "percentage_open_water": 7.0}, delta_h_available=1.0
        )
    )
    assert eps_of(wider)["voorraad"] == pytest.approx(0.070)


def test_the_enumeration_collapses_onto_few_answers(state, storm):
    """`packages` is niet het gebied - het is één punt, tot eenendertig keer.

    Eenendertig mixen, vierentwintig haalbaar, en daarvan nog steeds drie ONDERSCHEIDEN:
    een grotere mix waarin de extra maatregelen naar nul gaan valt samen met een kleinere.
    Daarom is de sweep de hele opbrengst van deze stap en niet een uitlezing van wat er al
    lag.

    **Dat het er drie blijven terwijl er een vijfde actie bij kwam, is de meting.** Bij
    alleen de inundatie-eis doet aanvoeren niets - `simulate` leest `capacity_in` niet - dus
    elke mix mét aanvoeren valt samen met dezelfde mix zonder. Zonder
    `_minimise_priceless` zou aanvoeren op zijn zoekgrens blijven staan en zouden er
    antwoorden bij komen die alleen in een maatregel verschillen die niets doet.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert len(result.packages) == 31
    assert len([p for p in result.packages if p.feasible]) == 24
    assert len(distinct_answers([p for p in result.packages if p.feasible])) == 3


def test_the_interval_is_bounded_below_by_the_requirement(state, storm):
    """De onderkant van het interval is de eis, en dat maakt hem zoekeronafhankelijk.

    Onder 2,91 m3/s haalt de inundatienorm het niet - 2,00 geeft 1,225 m tegen een norm van
    1,00 - dus die grens komt uit de hydrologie en niet uit SLSQP. Dat is invariant I6 uit
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    discharge = next(r for r in result.ranges if r.name_nl == "afvoeren")

    assert discharge.role is MeasureRole.FORCED
    assert discharge.magnitude_min == pytest.approx(2.91, abs=0.05)
    # en op die ondergrens ligt de eis werkelijk op zijn grens
    outcome = outcome_of(state, storm, (AfvoerenAction(),), [discharge.magnitude_min])
    assert outcome.dh_total_m == pytest.approx(1.0, abs=2e-3)


def test_the_interval_is_bounded_above_by_the_price_band(state, storm):
    """De bovenkant komt uit de eigen prijsband, niet uit een afgesproken percentage.

    Het gemaal staat op -3/+6 %, dus de band is ruim 9 % breed en het interval loopt tot
    ongeveer 3,2 m3/s. Een platte 15 % zou hier te ruim zijn en bij bergen - band -11/+70 % -
    veel te krap. Daarom is epsilon afgeleid en niet afgesproken.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    discharge = next(r for r in result.ranges if r.name_nl == "afvoeren")

    assert cost_epsilon(result.best) == pytest.approx(0.094, abs=0.02)
    assert 2.93 < discharge.magnitude_max < 3.40
    assert discharge.magnitude_max > discharge.magnitude_min


def test_the_flat_objective_shows_a_plateau_instead_of_the_search_bound(state, storm):
    """Waar de doelfunctie plat is, hoort een interval te staan en niet de zoekgrens.

    Met alleen de voorraadeis kost peilopzet niets, dus is elke waarde boven 0,571 m even
    optimaal en meldde de zoeker 1,00 m - de waarde van `MAX_TARGET_LEVEL_RISE_M`. Dat is
    geen antwoord maar een artefact van de zoekruimte. Nu staat er 0,571 tot 1,000: de
    onderkant is wat de eis vraagt, de bovenkant waar we niet verder hebben gekeken.
    """
    result = optimize(state, storm, Constraints(min_storage_mm=20.0))
    rise = next(r for r in result.ranges if r.name_nl == "peilopzet")

    assert rise.role is MeasureRole.FORCED
    # 20 mm voorraad bij 3,5 % open water vraagt 20/35 meter opzet
    assert rise.magnitude_min == pytest.approx(20.0 / 35.0, abs=0.01)
    assert rise.magnitude_max > rise.magnitude_min + 0.3


def test_the_region_does_not_depend_on_the_starting_point(state, storm):
    """Het gebied is hetzelfde vanaf beide startpunten; het PUNT hoeft dat niet te zijn.

    Dit is de test die de Mac-versus-Linux-splitsing echt afdekt. `optimise_mix` start bij
    nul en probeert de bovengrens alleen als dat mist, en juist die keuze maakte het
    verschil tussen 2,91 en 4,75. Het interval hangt aan de eis en aan de prijsband, dus
    aan geen van beide startpunten.
    """
    constraints = Constraints(max_dh_total_m=1.0)
    actions = (AfvoerenAction(),)
    budget = 5.59e6 * 1.094

    from_zero = sweep_measure(state, storm, actions, [0.0], 0, constraints, budget)
    from_bound = sweep_measure(
        state,
        storm,
        actions,
        [AfvoerenAction().upper_bound(state)],
        0,
        constraints,
        budget,
    )
    assert from_zero == pytest.approx(from_bound, abs=1e-6)


def test_forced_and_optional_follow_the_second_constraint(state, storm):
    """De rollen zeggen wat vastzit en wat vrij is, en dat verandert met de eisen."""
    only_flooding = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    roles = {r.name_nl: r.role for r in only_flooding.ranges}
    assert roles["afvoeren"] is MeasureRole.FORCED
    assert roles["bergen"] is MeasureRole.ABSENT
    assert roles["peilopzet"] is MeasureRole.ABSENT

    both = optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))
    roles = {r.name_nl: r.role for r in both.ranges}
    # peilopzet is de enige die voorraad koopt, dus die zit er nu in elk pakket
    assert roles["peilopzet"] is MeasureRole.FORCED
    # en afvoeren is NIET verdwenen - dat hangt aan de ontbrekende prijs van peilopzet
    assert roles["afvoeren"] is MeasureRole.FORCED


def test_the_step_cost_reading_puts_storage_on_the_plateau(state, storm):
    """Het echte plateau zit in de kostenVORM, niet in de kostenslack.

    Epsilon op het kostenniveau bereikt bergen nooit: het tweede onderscheiden antwoord is
    111 ha voor 15,01 mln, dus +169 % boven 5,59 mln. Maar in de trapkost-lezing die
    `replacement_quantity` al levert kost hetzelfde gemaal 15,19 mln, en dán liggen de twee
    antwoorden 1,2 % uit elkaar met ruim overlappende banden. Dat is het plateau, en het is
    onzichtbaar zolang de prijs lineair is.
    """
    from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
        COST_PUMP_CAPACITY,
    )

    discharge = AfvoerenAction(delta_pump_capacity_m3_per_sec=2.9116)
    storage = BergenAction(delta_open_water_ha=111.218)

    linear = discharge.cost(state)
    replacement = discharge.replacement_quantity(state) * COST_PUMP_CAPACITY.typical
    assert storage.cost(state) / linear > 2.5  # +169 %, buiten elk redelijk epsilon
    assert storage.cost(state) == pytest.approx(replacement, rel=0.05)

    # en de banden overlappen, dus het model kan de twee niet onderscheiden
    replacement_band = (
        discharge.replacement_quantity(state) * COST_PUMP_CAPACITY.low,
        discharge.replacement_quantity(state) * COST_PUMP_CAPACITY.high,
    )
    storage_band = storage.cost_range(state)
    assert max(replacement_band[0], storage_band[0]) <= min(
        replacement_band[1], storage_band[1]
    )


# --- de zin, en de claim (issue #30 stap 2 en 3) ------------------------------------


def test_the_sentence_names_the_interval_and_not_the_point(state, storm):
    """De zin die in plaats van "2,91 m3/s" hoort te staan.

    Niet omdat 2,91 fout is, maar omdat het net zo goed 3,1 had kunnen zijn en de lezer dat
    niet kan zien. En de precisie van het interval volgt uit de BREEDTE van het interval:
    2,912 tot 3,185 is 9 % breed, dus twee cijfers.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    sentence = describe_region(result.ranges, "nl")

    assert "van 2.9 (de eis) tot 3.2 m3/s (de prijsband)" in sentence
    assert "2.91" not in sentence and "3.185" not in sentence


def test_a_wide_plateau_gets_fewer_digits_than_a_narrow_one(state, storm):
    """De precisie van de zin volgt de breedte, net als bij `append_spread`.

    Het voorraadplateau loopt van 0,571 tot 1,000 m. De randen komen uit de optimalisator
    en zijn dus EXACT - anders dan een spreidingsband, die zelf een schatting is - en de
    zin geeft ze op twee significante cijfers: "57 tot 100 cm".

    Op een cijfer zou er "60 tot 100 cm" staan, met als argument dat 0,571 een precisie
    suggereert die het plateau niet heeft. Dat argument geldt voor een middenwaarde en niet
    voor een rand: de rand IS de uitspraak, en hem naar 60 afronden verschuift het plateau
    met 5 % zonder daar iets voor terug te geven. Bij een lager eerste cijfer loopt diezelfde
    afronding op tot 21 %; zie `MINIMUM_DIGITS`.
    """
    plateau = optimize(state, storm, Constraints(min_storage_mm=20.0))
    sentence = describe_region(plateau.ranges, "nl")

    # prijsloos, dus de bovengrens is de zoekgrens en de zin zegt dat in plaats van hem
    # als koopgrens te presenteren
    assert "vanaf 57 cm" in sentence
    assert "gezocht tot 100" in sentence


def test_absent_names_the_measures_without_claiming_a_reason(state, storm):
    """Of een maatregel niet bijdraagt of alleen te duur is, valt uit het gebied niet af te
    lezen - dus claimt de zin geen van beide."""
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    sentence = describe_region(result.ranges, "nl")

    assert "doen hier niet mee" in sentence
    assert "vasthouden" in sentence.lower() and "bergen" in sentence.lower()
    assert "bijdra" not in sentence and "te duur" not in sentence


def test_the_english_sentence_names_every_measure_in_english(state, storm):
    """Geen Nederlandse maatregelnaam in een Engelse zin; `peilopzet` ontbrak in de tabel."""
    result = optimize(
        state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0)
    )
    sentence = describe_region(result.ranges, "en")

    assert "peilopzet" not in sentence
    assert "raise target level" in sentence


def test_the_claim_that_discharge_alone_is_enough_fails_on_the_second_requirement(
    state, storm
):
    """De claim testen in plaats van het getal - Lombardi-trede 2, uit het gebied gelezen.

    "Afvoeren alleen is genoeg" is waar met alleen de inundatie-eis en onwaar zodra er
    voorraad bij komt. Dat volgt hier uit `ranges` en niet uit een comment, en dat is het
    hele punt van de rol: hij is een uitspraak over het GEBIED en niet over een pakket.
    """

    def discharge_alone_suffices(result):
        roles = {r.name_nl: r.role for r in result.ranges}
        others = [n for n, role in roles.items() if n != "afvoeren"]
        return roles["afvoeren"] is MeasureRole.FORCED and all(
            roles[n] is MeasureRole.ABSENT for n in others
        )

    assert discharge_alone_suffices(
        optimize(state, storm, Constraints(max_dh_total_m=1.0))
    )
    assert not discharge_alone_suffices(
        optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))
    )


def test_the_robustness_axis_is_a_band_and_not_a_point(state, storm):
    """De y-as van de robuustheidscurve is het onbetrouwbaarste getal in het systeem.

    Hij staat in miljoenen euro's en is tegelijk de kop van de demo. Een punt melden waar de
    prijsband een factor twee breed is, is dezelfde fout als "2,91 m3/s" - dus draagt elk
    pakket dat volledig geprijsd is zijn band mee.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    for package in result.near_optimal:
        assert (
            package.priced_cost_range[0] <= package.cost <= package.priced_cost_range[1]
        )
    low, high = result.best.cost_range
    # bij een gemaal is de band smal, maar hij is er
    assert high > low > 0
    assert (high - low) / result.best.cost > 0.05


def test_the_optimiser_stays_within_a_few_seconds(state, storm):
    """Eenendertig mixen, soms een tweede start; de demo mag hier niet op zitten wachten.

    Het budget stond op 3 s toen er vier acties waren. Een vijfde actie verdubbelt het
    aantal niet-lege mixen - van vijftien naar eenendertig - en daarmee ongeveer de tijd:
    lokaal 0,5 s tegen 1,1 s. Op een CI-runner is dat 3,0 s, dus het oude budget lag er
    precies tegenaan.

    Zes seconden is dus geen opgerekte grens om een test groen te krijgen, maar hetzelfde
    budget per mix. Het vangt nog steeds waar het voor bedoeld is: een verandering die de
    zoektocht een orde trager maakt. Wat het NIET moet doen is stilzwijgend meegroeien -
    komt er ooit een zesde actie bij, dan is dat 63 mixen en hoort die afweging opnieuw
    gemaakt te worden, niet het getal opnieuw opgehoogd. Zie
    """
    import time

    start = time.perf_counter()
    optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 6000, f"{elapsed_ms:.0f} ms"


# --- de tweede kostenlezing: waar het plateau echt zit -------------------------------


def test_only_discharge_differs_between_the_two_cost_readings(state, storm):
    """Bergen en vasthouden zijn werkelijk lineair; een gemaal is dat niet.

    Je koopt hectares, en tien hectare kost tien keer een hectare. Je koopt een gemaal, en
    niet een m3/min. Dat is de enige plek waar de twee lezingen uiteenlopen, en dus de enige
    actie die `replacement_quantity` overschrijft.
    """
    assert BergenAction(delta_open_water_ha=50).replacement_cost(
        state
    ) == pytest.approx(BergenAction(delta_open_water_ha=50).cost(state))
    assert VasthoudenAction(delta_retention_ha=100).replacement_cost(
        state
    ) == pytest.approx(VasthoudenAction(delta_retention_ha=100).cost(state))

    discharge = AfvoerenAction(delta_pump_capacity_m3_per_sec=2.9116)
    assert discharge.replacement_cost(state) / discharge.cost(state) == pytest.approx(
        2.72, abs=0.05
    )


def test_the_step_cost_reading_changes_the_ranking_and_that_is_the_plateau(
    state, storm
):
    """De kern van #30, en hij zit niet in de kosten-slack.

    Lineair is `{bergen 111 ha}` +169 % boven `{afvoeren 2,91}` - geen enkele redelijke
    epsilon haalt dat. In de trapkost-lezing kost datzelfde gemaal 15,19 mln tegen 15,01 mln
    voor bergen: 1,2 % verschil met ruim overlappende banden. Dan zijn "een groter gemaal" en
    "111 hectare open water" twee structureel verschillende antwoorden die het model niet uit
    elkaar kan houden.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    # lineair is het gebied een antwoord
    assert len(result.near_optimal) == 1
    assert set(_used(result.near_optimal[0])) == {"afvoeren"}

    # in de trapkost-lezing zijn het er meer, en bergen zit erbij
    plateau = indistinguishable_under_step_cost(result)
    used = [set(_used(package)) for package in plateau]
    assert {"afvoeren"} in used
    assert any("bergen" in names for names in used), used
    assert len(plateau) > len(result.near_optimal)


def test_the_two_readings_are_reported_side_by_side_and_not_merged(state, storm):
    """Twee lezingen naast elkaar, geen bredere epsilon op een van de twee.

    Met een factor 2,7 als slack op de lineaire prijs slikt de band elk pakket en zegt het
    plateau niets meer. De informatie zit juist in het VERSCHIL tussen de twee.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    best = result.best

    assert best.cost < best.replacement_cost
    # en beide dragen hun eigen band, uit dezelfde onderbouwde eenheidsprijs
    assert best.priced_cost_range[0] < best.cost < best.priced_cost_range[1]
    assert (
        best.replacement_cost_range[0]
        < best.replacement_cost
        < best.replacement_cost_range[1]
    )
    # de banden overlappen niet: het zijn echt twee verschillende uitspraken
    assert best.priced_cost_range[1] < best.replacement_cost_range[0]


def test_the_sentence_says_the_ranking_changes(state, storm):
    """En de zin zegt het, want dat is wat er wordt voorgelezen."""
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    sentence = describe_step_cost_plateau(
        result.best, indistinguishable_under_step_cost(result), "nl"
    )

    assert "Als vervanging" in sentence
    assert "bergen" in sentence
    assert "niet van te onderscheiden" in sentence
    # geen verzonnen zekerheid over welke dan de goedkoopste is
    assert "kan dit model dan niet zeggen" in sentence


def test_no_ranking_change_means_silence_instead_of_a_stock_sentence(state, storm):
    """Verandert de vervangingslezing niets, dan is er niets te zeggen.

    Een vaste zin die elke uitvoer vult ("de rangorde verandert daar niet van") is ruis
    voor wie het antwoord al kent; stilte is hier het eerlijke signaal.
    """
    result = optimize(state, storm, Constraints(min_storage_mm=20.0))
    sentence = describe_step_cost_plateau(
        result.best, indistinguishable_under_step_cost(result), "nl"
    )
    assert result.best.cost == pytest.approx(result.best.replacement_cost)
    assert sentence == ""


# --- de prijs van drooglegging is een curve, geen getal ------------------------------


def test_the_value_curve_has_a_plateau_a_cliff_and_provenance():
    """Drie eigenschappen die een prijs per centimeter niet kan reproduceren.

    De bron is de Compensatie Systematiek Veenweiden: vastgesteld door DB Wetterskip Fryslan
    en GS Fryslan op 4 juni 2024, extern gevalideerd, en doorgerekend op BIN-cijfers van tien
    Friese veenweidebedrijven. Dat is geen schatting maar de methodiek waarmee
    nadeelcompensatie wordt bepaald - en dat is voor een vuistregel het betere anker, want
    individuele toegekende bedragen worden niet gepubliceerd.
    """
    curve = DROOGLEGGING_VALUE_VEEN

    # de ankers zelf
    assert curve.value_at(0.30) == pytest.approx(28_000)
    assert curve.value_at(0.90) == pytest.approx(53_000)

    # het plateau: droger maakt de grond niet waardevoller, dus vernatten kost er niets
    assert curve.value_at(1.50) == pytest.approx(curve.value_at(0.90))
    assert curve.marginal_at(1.20) == pytest.approx(0.0)

    # de klif: onder 30 cm vervalt normaal agrarisch gebruik, en de curve wordt steiler
    assert curve.marginal_at(0.25) > curve.marginal_at(0.60)
    assert curve.marginal_at(0.05) > curve.marginal_at(0.25)

    # en de herkomst reist mee, want deze curve geldt voor veen en niet overal
    assert "Wetterskip" in curve.source
    assert "veen" in curve.applies_to


def test_the_documented_curve_puts_every_band_above_the_first_switch_point(
    state, storm
):
    """De beslissende toets, en het antwoord is niet het getal dat ik eerst noemde.

    Het model kantelt bij ongeveer 0,145 mln per centimeter over 4000 ha, oftewel 36 euro per
    hectare per centimeter. Op de HELE gedocumenteerde curve - van 0 tot 90 cm drooglegging -
    ligt de marginale prijs tussen 417 en 900 euro per hectare per centimeter. Dus overal op
    die curve komt bergen erbij, en op elke band ligt hij zelfs boven het tweede kantelpunt
    van 375: dan verdwijnt afvoeren helemaal.

    Dat is precies het pakket dat oorspronkelijk in het plan stond. De gedocumenteerde demo
    was dus niet fout - hij hoorde bij een polder die op de curve zit, en het model rekende
    met een polder erboven.
    """
    curve = DROOGLEGGING_VALUE_VEEN
    first_switch_per_ha_per_cm = 36.0
    second_switch_per_ha_per_cm = 375.0

    bands = [
        (0.05, "0-10 cm"),
        (0.15, "10-20 cm"),
        (0.25, "20-30 cm"),
        (0.60, "30-90 cm"),
    ]
    for depth, label in bands:
        per_ha_per_cm = curve.marginal_at(depth) / 100.0
        assert per_ha_per_cm > first_switch_per_ha_per_cm, label
        assert per_ha_per_cm > second_switch_per_ha_per_cm, label

    # en boven het plateau is hij nul, dus daar wint afvoeren
    assert curve.marginal_at(1.20) / 100.0 < first_switch_per_ha_per_cm


def test_pricing_the_level_raise_from_the_curve_changes_the_package(state, storm):
    """Met de curve als prijs geeft de pakketzoeker het gedocumenteerde antwoord.

    Dit is de kern van issue #30 rond: peilopzet had geen prijs, en die afwezigheid bepaalde
    de uitkomst. Prijs hem uit de vastgestelde methodiek bij een drooglegging van 60 cm en het
    antwoord verschuift naar bergen plus een kleine opzet - zonder dat wij een getal hebben
    verzonnen.
    """
    priced = PeilopzetAction(unit_cost=peilopzet_unit_cost(state.area_ha, 0.60))
    result = optimize(
        state,
        storm,
        Constraints(max_dh_total_m=1.0, min_storage_mm=20.0),
        actions=_actions_with(priced),
    )

    used = _used(result.best)
    assert "bergen" in used, used
    assert result.best.priceless == (), "met een prijs is peilopzet niet meer prijsloos"
    # en de opzet is klein geworden, want hij is nu duur
    assert used.get("peilopzet", 0.0) < 0.35


def test_the_switch_price_is_a_linear_proxy_and_says_so(state, storm):
    """De beperking van wat ik eerder bouwde, als test in plaats van als voetnoot.

    `switch_price_of` varieert een LINEAIRE prijs. De werkelijke curve knikt, dus er is geen
    enkel getal waarbij het antwoord omslaat - het hangt af van de drooglegging van de polder,
    en die zit niet in `PolderState`. Deze test legt vast dat de twee niet hetzelfde zijn,
    zodat niemand de schaduwprijs voor de echte prijs aanziet.
    """
    switch = switch_price_of(
        state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0), "peilopzet"
    )
    linear_proxy_per_ha_per_cm = switch.price_low / state.area_ha / 100

    curve = DROOGLEGGING_VALUE_VEEN
    # de proxy is een ordegrootte, niet de prijs: de echte curve ligt er over de hele
    # gedocumenteerde band een factor tien tot vijfentwintig boven
    for depth in (0.05, 0.25, 0.60):
        ratio = (curve.marginal_at(depth) / 100) / linear_proxy_per_ha_per_cm
        assert ratio > 5, (depth, ratio)


def test_capitalised_income_damage_is_not_added_on_top(state, storm):
    """De valkuil die de bron zelf blootlegt, vastgelegd zodat niemand hem opnieuw inloopt.

    De eenmalige vermogenscompensatie kapitaliseert de verloren productiecapaciteit al. In het
    uitgewerkte CSV-voorbeeld is de resterende inkomensschade daardoor NEGATIEF - een
    inkomensvoordeel. Beide optellen is dubbeltellen, en dat is precies het soort fout dat een
    model plausibel maakt en onwaar.

    Deze test toetst dat `peilopzet_unit_cost` alleen de waardedaling gebruikt en niet ook een
    gekapitaliseerde jaarschade eroverheen legt.
    """
    curve = DROOGLEGGING_VALUE_VEEN
    unit = peilopzet_unit_cost(4000, 0.60)
    expected = curve.marginal_at(0.60) * 4000

    assert unit.typical == pytest.approx(expected)
    # en dus zeker niet nog eens de kapitalisatiefactor eroverheen
    assert unit.typical < expected * CAPITALISATION_FACTOR / 2

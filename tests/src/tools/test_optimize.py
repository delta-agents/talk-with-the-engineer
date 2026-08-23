"""De pakketzoeker: het goedkoopste pakket dat aan twee eisen tegelijk voldoet.

De kerntest is `test_the_second_constraint_changes_the_answer`. Met alleen de inundatie-eis
zegt het model "altijd pompen"; met de voorraadeis erbij komt peilopzet erbij, want dat is
de enige maatregel die voorraad direct koopt.

**Welk** pakket het dan wordt, hangt aan een prijs die er niet is, en die drie tests horen
bij elkaar: `test_a_priceless_measure_is_not_free`,
`test_the_switch_price_is_where_the_package_changes` en
`test_the_documented_package_returns_at_its_shadow_price`. Zonder prijs voor peilopzet wint
`{afvoeren, peilopzet}`; vanaf ongeveer 0,14 mln per centimeter komt bergen erbij, en bij
1,5 mln verdwijnt afvoeren. Eerder stond hier dat afvoeren "volledig verdwijnt" - dat was
het niet-geconvergeerde antwoord van voor de COST_SCALE-fix. Zie issue #30.
"""

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    COST_OPEN_WATER,
    AfvoerenAction,
    BergenAction,
    PeilmargeAction,
    PeilopzetAction,
    UnitCost,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import MeasureRole
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.optimize import (
    DEFAULT_ACTIONS,
    Constraints,
    _finite_difference,
    cost_epsilon,
    cost_range_of,
    distinct_answers,
    eps_of,
    optimise_mix,
    optimize,
    outcome_of,
    sweep_measure,
    switch_price_of,
    used_measures,
)


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
    spanning uit PLAN_TOOLS_REFACTOR.md Sec. 8.0, mechanisch.
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
    assert len(result.packages) == 15


def test_every_mix_is_reported_so_the_answer_is_traceable(state, storm):
    """Ook de onhaalbare mixen, want anders is het antwoord niet na te lopen."""
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    assert len(result.packages) == 15  # vier acties, alle niet-lege deelverzamelingen
    assert any(not package.feasible for package in result.packages)
    assert result.best.cost == min(
        package.cost for package in result.packages if package.feasible
    )


def test_limiting_the_mix_size_limits_the_search(state, storm):
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0), max_mix_size=1)
    assert len(result.packages) == 4
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

    `PLAN_UITWISSELING_EN_NETWERK.md` Sec. 9 meldde `bergen 190 ha + peilopzet 24 cm` voor
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
    """`packages` is niet het gebied - het is één punt, tot vijftien keer.

    Vijftien mixen, twaalf haalbaar, en daarvan drie ONDERSCHEIDEN: een grotere mix waarin
    de extra maatregelen naar nul gaan valt samen met een kleinere. Daarom is de sweep de
    hele opbrengst van deze stap en niet een uitlezing van wat er al lag.
    """
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert len(result.packages) == 15
    assert len([p for p in result.packages if p.feasible]) == 12
    assert len(distinct_answers([p for p in result.packages if p.feasible])) == 3


def test_the_interval_is_bounded_below_by_the_requirement(state, storm):
    """De onderkant van het interval is de eis, en dat maakt hem zoekeronafhankelijk.

    Onder 2,91 m3/s haalt de inundatienorm het niet - 2,00 geeft 1,225 m tegen een norm van
    1,00 - dus die grens komt uit de hydrologie en niet uit SLSQP. Dat is invariant I6 uit
    BOUW_WP13_WP15.md.
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


def test_the_optimiser_stays_within_a_few_seconds(state, storm):
    """Vijftien mixen, soms een tweede start; de demo mag hier geen seconden op wachten."""
    import time

    start = time.perf_counter()
    optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 3000, f"{elapsed_ms:.0f} ms"

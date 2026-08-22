"""De pakketzoeker: het goedkoopste pakket dat aan twee eisen tegelijk voldoet.

De kerntest is `test_the_second_constraint_changes_the_answer`. Met alleen de inundatie-eis
zegt het model "altijd pompen"; met de voorraadeis erbij verdwijnt afvoeren volledig en
komen bergen en peilopzet ervoor. Dat is de trits die uit het model komt in plaats van
eroverheen te worden gelegd, en het is het resultaat waar de demo op rust.
"""

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    PeilmargeAction,
    PeilopzetAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.optimize import (
    Constraints,
    _finite_difference,
    optimise_mix,
    optimize,
    outcome_of,
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


def test_raising_the_target_level_buys_storage_and_spends_inundation_margin(state, storm):
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

    _after, dh_total, storage, _cost = outcome_of(state, storm, (action,), [0.20])
    baseline = outcome_of(state, storm, (action,), [0.0])[1]
    assert dh_total == pytest.approx(baseline + 0.20, abs=1e-9)
    assert storage > 0


def test_raising_the_target_level_is_not_the_level_margin(state, storm):
    """Twee randen van dezelfde band, twee gedragingen: lineair tegen verzadigend."""
    for rise in (0.1, 0.3, 0.5):
        _a, dh_total, _s, _c = outcome_of(
            state, storm, (PeilopzetAction(),), [rise]
        )
        base = outcome_of(state, storm, (PeilopzetAction(),), [0.0])[1]
        # lineair en onbegrensd
        assert dh_total == pytest.approx(base + rise, abs=1e-9)

    # de marge verzadigt, en dat is precies het verschil
    margins = [
        outcome_of(state, storm, (PeilmargeAction(),), [margin])[1]
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
    """Met alleen de inundatie-eis is afvoeren bij deze prijzen overal het goedkoopst."""
    result = optimize(state, storm, Constraints(max_dh_total_m=1.0))

    assert result.best is not None
    assert not result.problem_infeasible
    assert set(_used(result.best)) == {"afvoeren"}
    assert result.best.dh_total_m == pytest.approx(1.0, abs=1e-3)
    assert "inundatie" in result.best.binding


def test_the_second_constraint_changes_the_answer(state, storm):
    """De kerntest: de voorraadeis laat de trits ontstaan.

    Afvoeren draagt niets bij aan de voorraad, bergen aan beide, en peilopzet koopt voorraad
    direct. Met de tweede eis erbij verdwijnt afvoeren dus volledig uit het optimale pakket -
    niet omdat een regel dat voorschrijft maar omdat het niet loont.
    """
    only_flooding = optimize(state, storm, Constraints(max_dh_total_m=1.0))
    both = optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))

    assert both.best is not None
    assert set(_used(only_flooding.best)) == {"afvoeren"}
    assert "afvoeren" not in _used(both.best)
    assert set(_used(both.best)) == {"bergen", "peilopzet"}

    # en de tweede eis is niet gratis
    assert both.best.cost > 4 * only_flooding.best.cost
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
        [package.quantities[name] for name in ("vasthouden", "bergen", "afvoeren", "peilopzet")],
    )
    assert recomputed[1] == pytest.approx(package.dh_total_m, abs=1e-12)
    assert recomputed[2] == pytest.approx(package.storage_mm, abs=1e-12)


def test_the_optimiser_stays_within_a_second(state, storm):
    """Vijftien SLSQP-runs op een doorrekening van 0,06 ms; de demo hangt hieraan."""
    import time

    start = time.perf_counter()
    optimize(state, storm, Constraints(max_dh_total_m=1.0, min_storage_mm=20.0))
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 1000, f"{elapsed_ms:.0f} ms"

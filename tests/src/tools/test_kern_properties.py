"""Eigenschappen van de rekenkern.

Deze tests dekken de defectklassen uit PLAN_TOOLS_REFACTOR.md, niet de losse defecten:
massabehoud, equivalentie met de recursie, de vorm van de responscurves, en of het rondje
sluit over het hele haalbare bereik.
"""

import time

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import SolveStatus
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    delay_daily,
    simulate,
    water_level_series,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import evaluate, solve

SECONDS_PER_HOUR = 3600
SQUARE_METRES_PER_HECTARE = 1e4

# Een spreiding aan buien, zodat vormeigenschappen niet op een enkel geval rusten.
STORMS = [
    {"time_of_year": "summer", "return_period": 10, "length_event_hrs": 96.0},
    {"time_of_year": "summer", "return_period": 100, "length_event_hrs": 96.0},
    {"time_of_year": "winter", "return_period": 100, "length_event_hrs": 96.0},
    {"time_of_year": "winter", "return_period": 1000, "length_event_hrs": 96.0},
    {"time_of_year": "winter", "return_period": 100, "length_event_hrs": 192.0},
    {"time_of_year": "summer", "return_period": 1000, "length_event_hrs": 48.0},
]
POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}


def _storm_and_state(storm_kwargs):
    storm = StoreInputGivenH(delta_h_available=1.0, **storm_kwargs, **POLDER)
    return storm, PolderState.from_water_system_input(storm)


def _reference_recursion(drainage_l_s_ha, area_open_water_ha, area_land_ha, pump):
    """Expliciete recursie, inclusief wat er werkelijk verplaatst is."""
    metres_per_m3_per_sec = SECONDS_PER_HOUR / (
        area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )
    level, levels, pumped = 0.0, [], []
    for drainage in drainage_l_s_ha:
        inflow_m = drainage * area_land_ha / 1000.0 * metres_per_m3_per_sec
        wanted_m = pump * metres_per_m3_per_sec
        available_m = level + inflow_m
        moved_m = min(wanted_m, available_m)
        level = available_m - moved_m
        levels.append(level)
        pumped.append(moved_m / metres_per_m3_per_sec)
    return np.array(levels), np.array(pumped)


def test_vectorised_water_balance_equals_the_recursion():
    generator = np.random.default_rng(20260821)
    worst_level = worst_pumped = 0.0
    for _ in range(500):
        length = int(generator.integers(5, 300))
        drainage = np.abs(generator.normal(1.5, 1.5, length))
        area_open_water_ha = float(generator.uniform(20, 500))
        area_land_ha = float(generator.uniform(500, 5000))
        pump = float(generator.uniform(0.5, 8))

        level, pumped = water_level_series(
            drainage, area_open_water_ha, area_land_ha, pump
        )
        level_ref, pumped_ref = _reference_recursion(
            drainage, area_open_water_ha, area_land_ha, pump
        )
        worst_level = max(worst_level, np.abs(level - level_ref).max())
        worst_pumped = max(worst_pumped, np.abs(pumped - pumped_ref).max())

    assert worst_level < 1e-9, f"waterstand wijkt {worst_level:.2e} m af"
    assert worst_pumped < 1e-9, f"debiet wijkt {worst_pumped:.2e} m3/s af"


@pytest.mark.parametrize("days_to_retain", range(0, 11))
def test_delay_conserves_mass(days_to_retain):
    """D5: het oude blokkenschema hield 304 % over bij dT=0 en 28 % bij dT=10."""
    daily = np.array([6.44, 17.95, 27.25, 32.30, 25.86, 14.35, 5.05])
    delayed = delay_daily(daily, days_to_retain)
    assert delayed.sum() == pytest.approx(daily.sum(), rel=1e-12)
    assert len(delayed) == len(daily) + days_to_retain
    assert (delayed >= 0).all()


@pytest.mark.parametrize(
    "storm_kwargs", STORMS, ids=lambda s: f"{s['time_of_year']}T{s['return_period']}"
)
def test_water_balance_closes(storm_kwargs):
    """Aanvoer = gepompt + berging. Nodig voor de cascade, en een sterke totaalcontrole."""
    storm, state = _storm_and_state(storm_kwargs)
    result = simulate(state, storm)

    inflow_m3 = (
        result.drainage_l_s_ha * state.area_land_ha / 1000.0 * SECONDS_PER_HOUR
    ).sum()
    pumped_m3 = result.pumped_m3_per_sec.sum() * SECONDS_PER_HOUR
    stored_m3 = (
        result.water_level_m[-1] * state.area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )

    assert pumped_m3 + stored_m3 == pytest.approx(inflow_m3, rel=1e-9)
    assert (result.pumped_m3_per_sec >= -1e-12).all()
    assert (result.pumped_m3_per_sec <= state.pump_capacity_m3_per_sec + 1e-12).all()


@pytest.mark.parametrize(
    "storm_kwargs", STORMS, ids=lambda s: f"{s['time_of_year']}T{s['return_period']}"
)
def test_store_and_discharge_are_monotonically_decreasing(storm_kwargs):
    storm, state = _storm_and_state(storm_kwargs)
    for action in (BergenAction(), AfvoerenAction()):
        upper_bound = action.upper_bound(state)
        magnitudes = np.linspace(0, upper_bound, 40)
        values = [
            simulate(action.at(m).apply(state), storm).dh_max_m for m in magnitudes
        ]
        assert np.all(np.diff(values) <= 1e-12), (
            f"{action.name_nl} is niet monotoon dalend bij {storm_kwargs}"
        )


@pytest.mark.parametrize(
    "storm_kwargs", STORMS, ids=lambda s: f"{s['time_of_year']}T{s['return_period']}"
)
def test_retention_is_unimodal(storm_kwargs):
    """Vasthouden daalt en stijgt dan weer; de gulden snede vereist unimodaliteit."""
    storm, state = _storm_and_state(storm_kwargs)
    action = VasthoudenAction()
    magnitudes = np.linspace(0, action.upper_bound(state), 60)
    values = np.array(
        [simulate(action.at(m).apply(state), storm).dh_max_m for m in magnitudes]
    )

    minimum_index = int(values.argmin())
    assert np.all(np.diff(values[: minimum_index + 1]) <= 1e-9), (
        "niet dalend voor het minimum"
    )
    assert np.all(np.diff(values[minimum_index:]) >= -1e-9), (
        "niet stijgend na het minimum"
    )


@pytest.mark.parametrize(
    "storm_kwargs", STORMS, ids=lambda s: f"{s['time_of_year']}T{s['return_period']}"
)
@pytest.mark.parametrize(
    "action",
    [BergenAction(), AfvoerenAction(), VasthoudenAction()],
    ids=lambda a: a.name_nl,
)
def test_roundtrip_closes_over_the_whole_feasible_range(storm_kwargs, action):
    """D7: eerder werd er met np.interp geinterpoleerd en dat klemde op de randen.

    Getest op tien doelen verdeeld over het haalbare bereik, niet op een enkel punt.
    """
    storm, state = _storm_and_state(storm_kwargs)
    probe = solve(state, storm, action, 0.0)
    dh_min, dh_max = probe.feasible_dh_min_m, probe.feasible_dh_max_m
    if dh_max - dh_min < 1e-6:
        pytest.skip("geen haalbaar bereik voor deze combinatie")

    # blijf net binnen de randen; daar is de maatvoering nul respectievelijk het optimum
    for fraction in np.linspace(0.05, 0.95, 10):
        target = dh_min + fraction * (dh_max - dh_min)
        inverse = solve(state, storm, action, target)
        assert inverse.status is SolveStatus.EXACT, (
            f"doel {target:.4f} gaf {inverse.status}"
        )

        forward = evaluate(state, storm, action.at(inverse.magnitude))
        assert forward.dh_with_measure_m == pytest.approx(target, abs=1e-3), (
            f"{action.name_nl} bij {storm_kwargs}: doel {target:.4f} -> "
            f"{inverse.magnitude:.4f} {action.unit} -> {forward.dh_with_measure_m:.4f}"
        )


def test_targets_outside_the_range_report_a_status_instead_of_a_number():
    storm, state = _storm_and_state(STORMS[3])
    for action in (BergenAction(), AfvoerenAction(), VasthoudenAction()):
        probe = solve(state, storm, action, 0.0)

        above = solve(state, storm, action, probe.feasible_dh_max_m + 0.5)
        assert above.status is SolveStatus.NO_MEASURE_NEEDED
        assert above.magnitude == 0.0

        if probe.feasible_dh_min_m > 1e-6:
            below = solve(state, storm, action, probe.feasible_dh_min_m - 1e-3)
            assert below.status is SolveStatus.INFEASIBLE
            assert below.magnitude == pytest.approx(below.magnitude_at_optimum)


def test_performance_budget():
    """simulate() < 1 ms en een inverse aanroep < 10 ms; de demo hangt erop."""
    storm, state = _storm_and_state(STORMS[3])
    simulate(state, storm)  # warm de cache van de bui

    start = time.perf_counter()
    for _ in range(500):
        simulate(state, storm)
    simulate_ms = (time.perf_counter() - start) / 500 * 1000
    assert simulate_ms < 1.0, f"simulate() duurt {simulate_ms:.3f} ms"

    for action in (BergenAction(), AfvoerenAction(), VasthoudenAction()):
        solve(state, storm, action, 1.0)
        start = time.perf_counter()
        for _ in range(10):
            solve(state, storm, action, 1.0)
        solve_ms = (time.perf_counter() - start) / 10 * 1000
        assert solve_ms < 10.0, f"solve({action.name_nl}) duurt {solve_ms:.2f} ms"


def test_land_area_can_follow_the_open_water():
    """V1: het rekenblad houdt het afvoerend oppervlak vast; beide takken moeten werken."""
    storm = StoreInputGivenH(
        return_period=1000,
        time_of_year="winter",
        length_event_hrs=96.0,
        name_rainfall_pattern="p1a",
        days_to_discharge=4,
        rainfall_regime="R",
        delta_h_available=1.0,
        **POLDER,
    )
    pinned = PolderState.from_water_system_input(
        storm, land_area_follows_open_water=False
    )
    following = PolderState.from_water_system_input(
        storm, land_area_follows_open_water=True
    )

    # zonder maatregel identiek
    assert pinned.area_land_ha == following.area_land_ha == 3860.0
    assert simulate(pinned, storm).dh_max_m == pytest.approx(
        simulate(following, storm).dh_max_m
    )

    # met bergen loopt het uiteen; meekrimpend land geeft een lagere stand
    action = BergenAction(delta_open_water_ha=1060)
    assert action.apply(pinned).area_land_ha == 3860.0
    assert action.apply(following).area_land_ha == pytest.approx(2800.0)
    assert (
        simulate(action.apply(following), storm).dh_max_m
        < simulate(action.apply(pinned), storm).dh_max_m
    )

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
    PeilmargeAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    OptimumKind,
    SolveStatus,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    HOURS_PER_DAY,
    clamped_scan,
    delay_daily,
    simulate,
    slack_of,
    to_hourly,
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

    runoff_m3 = (
        result.drainage_l_s_ha * state.area_land_ha / 1000.0 * SECONDS_PER_HOUR
    ).sum()
    # neerslag die direct op het open water valt hoort ook bij de aanvoer, en die gaat er
    # ongereduceerd in: het neerslagverlies is een bodemproces
    direct_m3 = (
        result.rainfall_on_water_per_day_mm.sum()
        / 1000.0
        * state.area_open_water_ha
        * SQUARE_METRES_PER_HECTARE
    )
    inflow_m3 = runoff_m3 + direct_m3
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
def test_discharge_is_monotonically_decreasing(storm_kwargs):
    """Meer gemaalcapaciteit helpt altijd, zonder omslagpunt."""
    storm, state = _storm_and_state(storm_kwargs)
    action = AfvoerenAction()
    magnitudes = np.linspace(0, action.upper_bound(state), 40)
    values = [simulate(action.at(m).apply(state), storm).dh_max_m for m in magnitudes]
    assert np.all(np.diff(values) <= 1e-12), (
        f"afvoeren is niet monotoon dalend bij {storm_kwargs}"
    )


@pytest.mark.parametrize(
    "storm_kwargs", STORMS, ids=lambda s: f"{s['time_of_year']}T{s['return_period']}"
)
@pytest.mark.parametrize(
    "action", [BergenAction(), VasthoudenAction()], ids=lambda a: a.name_nl
)
def test_store_and_retention_are_unimodal(storm_kwargs, action):
    """Beide maatregelen dalen en stijgen dan weer; de gulden snede vereist die vorm.

    Vasthouden: voorbij een zeker areaal valt de vertraagde afvoer van het ene deel samen
    met de piek van het andere.

    Bergen: pas dicht bij 100 % open water, want dan is er geen land meer dat de afvoer
    over meerdere dagen spreidt en ontvangt het open water de neerslag ongedempt. Bij
    realistische percentages weegt de bergingswinst zwaarder.
    """
    storm, state = _storm_and_state(storm_kwargs)
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
            assert below.status is SolveStatus.ACTION_INFEASIBLE
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


def test_polder_balance_includes_the_two_terms_the_spreadsheet_omits():
    """V1: de balans telt krimpend land en directe neerslag mee.

    De twee termen werken tegen elkaar in - krimpend land verlaagt de stand, neerslag op
    het open water verhoogt hem - maar ze heffen elkaar niet op: zonder maatregel blijft
    er 10 cm over. De rekenbladkant van deze vergelijking staat in test_reference_ton.py.
    """
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
    polder = PolderState.from_water_system_input(storm)

    # zonder maatregel is alleen de directe neerslag het verschil met het blad: 10,3 cm
    assert polder.area_land_ha == 3860.0
    assert simulate(polder, storm).dh_max_m == pytest.approx(1.80583, abs=1e-4)

    # en met bergen krimpt het afvoerende land mee
    action = BergenAction(delta_open_water_ha=1060)
    assert action.apply(polder).area_land_ha == pytest.approx(2800.0)


@pytest.mark.parametrize("season, expect_equal", [("winter", True), ("summer", False)])
def test_summer_loss_applies_to_land_only(season, expect_equal):
    """Het neerslagverlies is een bodemproces en geldt niet voor neerslag op open water."""
    storm = StoreInputGivenH(
        return_period=100,
        time_of_year=season,
        length_event_hrs=96.0,
        delta_h_available=1.0,
        **POLDER,
    )
    result = simulate(PolderState.from_water_system_input(storm), storm)
    on_land = result.rainfall_per_day_mm.sum()
    on_water = result.rainfall_on_water_per_day_mm.sum()

    if expect_equal:
        assert on_water == pytest.approx(on_land)
    else:
        assert on_water == pytest.approx(on_land + 20.0)


def test_direct_precipitation_raises_the_level_by_the_rainfall_depth():
    """Neerslag op open water geeft exact de neerslagdiepte, ongeacht het oppervlak.

    Zonder afvoer van het land en zonder gemaal moet de stand precies de netto neerslag
    zijn. Dat is de scherpste controle op de nieuwe term.
    """
    storm = StoreInputGivenH(
        return_period=1000,
        time_of_year="winter",
        length_event_hrs=96.0,
        name_rainfall_pattern="p1a",
        days_to_discharge=4,
        rainfall_regime="R",
        delta_h_available=1.0,
        area_ha=4000,
        percentage_open_water=100,  # alles is open water, dus geen afvoerend land
        discharge_capacity_m3_per_sec=0,  # en geen gemaal
    )
    state = PolderState.from_water_system_input(storm)
    result = simulate(state, storm)

    assert state.area_land_ha == 0.0
    assert result.dh_max_m == pytest.approx(
        result.rainfall_per_day_mm.sum() / 1000, rel=1e-9
    )


def test_unit_costs_carry_their_own_provenance():
    """De eenheidskosten zijn onderbouwd; de bron hoort in de code te staan."""
    from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
        COST_OPEN_WATER,
        COST_PUMP_CAPACITY,
        COST_RETENTION,
    )

    for unit_cost in (COST_OPEN_WATER, COST_PUMP_CAPACITY, COST_RETENTION):
        assert unit_cost.low <= unit_cost.typical <= unit_cost.high
        assert unit_cost.source and unit_cost.price_level and unit_cost.unit


def test_store_and_retention_costs_are_linear_in_the_area():
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5)

    bergen = BergenAction(delta_open_water_ha=100)
    assert bergen.cost(state) == pytest.approx(100 * 135_000)
    assert bergen.at(200).cost(state) == pytest.approx(2 * bergen.cost(state))

    vasthouden = VasthoudenAction(delta_retention_ha=1000)
    assert vasthouden.cost(state) == pytest.approx(1000 * 2_400)
    assert vasthouden.at(2000).cost(state) == pytest.approx(2 * vasthouden.cost(state))


def test_discharge_cost_is_linear_by_choice():
    """Afvoeren wordt lineair gerekend, en dat is een vuistregelvereenvoudiging.

    Deze test legt de keuze vast en maakt hem meetbaar: hij toont zowel dat `cost`
    lineair is als hoeveel dat afwijkt van de trapkost die de brondata laat zien. Gaat
    hij om, dan is de keuze veranderd en niet per ongeluk.
    """
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5)
    rate = AfvoerenAction().unit_cost.typical  # EUR per m3/s

    assert AfvoerenAction().cost(state) == 0.0

    small = AfvoerenAction(delta_pump_capacity_m3_per_sec=0.5)
    assert small.cost(state) == pytest.approx(0.5 * rate)
    # lineair: twee keer de toename is twee keer de kosten
    assert small.at(1.0).cost(state) == pytest.approx(2 * small.cost(state))

    # en dit is wat de vereenvoudiging kost: de trapkost-lezing van dezelfde uitbreiding
    replacement = rate * small.replacement_quantity(state)
    assert replacement == pytest.approx(5.5 * rate)
    assert replacement > 10 * small.cost(state)


def test_costs_can_be_switched_off():
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5)
    action = BergenAction(delta_open_water_ha=100, unit_cost=None)
    assert action.cost(state) is None
    assert action.cost_range(state) is None
    assert action.at(200).unit_cost is None


def test_cheapest_per_hectare_is_not_cheapest_per_centimetre():
    """Vasthouden is het goedkoopst per hectare en toch niet de goedkoopste maatregel.

    Dat is de omkering waarvoor je een model nodig hebt in plaats van een vuistregel over
    eenheidsprijzen: vasthouden kost per hectare een fractie van bergen, maar heeft er
    honderden keren zoveel nodig. Zie PLAN_TOOLS_REFACTOR.md §8.1.
    """
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
    state = PolderState.from_water_system_input(storm)

    assert VasthoudenAction().unit_cost.typical < BergenAction().unit_cost.typical / 50

    probe = solve(state, storm, VasthoudenAction(), 0.0)
    target = probe.feasible_dh_min_m + 1e-4

    costs, quantities = {}, {}
    for action in (BergenAction(), AfvoerenAction(), VasthoudenAction()):
        result = solve(state, storm, action, target)
        assert result.status is SolveStatus.EXACT
        costs[action.name_nl] = result.cost
        quantities[action.name_nl] = result.magnitude

    # vasthouden vraagt honderden keren meer hectares dan bergen voor dezelfde verlaging
    assert quantities["vasthouden"] > 100 * quantities["bergen"]
    assert costs["vasthouden"] > costs["bergen"]

    # met de lineaire kostenaanname is afvoeren hier de goedkoopste; met de trapkost uit
    # de brondata zou het de duurste zijn. Zie test_discharge_cost_is_linear_by_choice.
    assert costs["afvoeren"] < costs["bergen"]


def test_linear_pump_cost_removes_the_crossover():
    """Met lineaire gemaalkosten is afvoeren bij elke ambitie het goedkoopst.

    Dat is een gevolg van de kostenaanname en niet van de hydrologie. Met de
    trapkost-lezing ontstaat er wel een omslagpunt, rond 100 cm op deze polder.
    """
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
    state = PolderState.from_water_system_input(storm)
    rate = AfvoerenAction().unit_cost.typical

    crossover_found = False
    for target in (1.70, 1.50, 1.20, 1.00, 0.60):
        bergen = solve(state, storm, BergenAction(), target)
        afvoeren = solve(state, storm, AfvoerenAction(), target)
        assert bergen.status is SolveStatus.EXACT
        assert afvoeren.status is SolveStatus.EXACT

        # lineair: afvoeren altijd goedkoper
        assert afvoeren.cost < bergen.cost, f"bij {target * 100:.0f} cm"

        # trapkost: bij bescheiden ambitie draait het om
        replacement = rate * AfvoerenAction().at(
            afvoeren.magnitude
        ).replacement_quantity(state)
        if replacement > bergen.cost:
            crossover_found = True
    assert crossover_found, "de trapkost hoort ergens duurder te zijn dan bergen"


# ---------------------------------------------------------------------------
# Droogte: de tweede uitlezing van dezelfde doorrekening
# ---------------------------------------------------------------------------


def _reference_storm_and_state(**state_kwargs):
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
    state = PolderState.from_water_system_input(storm).replace(**state_kwargs)
    return storm, state


def test_pumped_volume_is_not_a_drought_readout():
    """Vastleggen waarom weggepompt volume hier niet werkt.

    Het gemaal pompt tot het streefpeil - de afkap op nul *is* dat peil - dus over een
    volledige gebeurtenis verdwijnt alles wat erboven komt, welke maatregel je ook neemt.
    Weggepompt volume onderscheidt de maatregelen alleen zolang het rekenvenster te kort
    is om leeg te lopen. Deze test bewijst dat, zodat de uitlezing niet opnieuw wordt
    voorgesteld. Zie PLAN_TOOLS_REFACTOR.md §8.2.
    """
    storm, base = _reference_storm_and_state()
    variants = [
        base,
        BergenAction(delta_open_water_ha=200).apply(base),
        AfvoerenAction(delta_pump_capacity_m3_per_sec=2).apply(base),
        VasthoudenAction(delta_retention_ha=2000).apply(base),
    ]

    def pumped_mm_with_tail(state, extra_days):
        result = simulate(state, storm)
        length = len(result.drainage_l_s_ha) + extra_days * HOURS_PER_DAY
        drainage = np.zeros(length)
        drainage[: len(result.drainage_l_s_ha)] = result.drainage_l_s_ha
        rain = np.zeros(length)
        per_hour = (
            np.repeat(
                result.rainfall_on_water_per_day_mm / HOURS_PER_DAY, HOURS_PER_DAY
            )
            / 1000.0
        )
        overlap = min(len(per_hour), len(result.drainage_l_s_ha))
        rain[:overlap] = per_hour[:overlap]
        _, pumped = water_level_series(
            drainage,
            state.area_open_water_ha,
            state.area_land_ha,
            state.pump_capacity_m3_per_sec,
            None,
            rain,
        )
        return (
            pumped.sum()
            * SECONDS_PER_HOUR
            / (state.area_ha * SQUARE_METRES_PER_HECTARE)
            * 1000
        )

    # binnen het rekenvenster lijken ze te verschillen
    short = [pumped_mm_with_tail(state, 0) for state in variants]
    assert max(short) - min(short) > 20  # tientallen mm verschil

    # maar met genoeg naloop convergeren ze naar hetzelfde: de hele bui gaat eruit
    long = [pumped_mm_with_tail(state, 14) for state in variants]
    assert max(long) - min(long) < 1e-6
    assert long[0] == pytest.approx(simulate(base, storm).volume_rain_mm, rel=1e-9)


def test_retained_volume_responds_only_to_the_target_level():
    """De droogte-uitlezing reageert op peilopzet en op open water, niet op de rest."""
    storm, base = _reference_storm_and_state()
    assert base.retained_volume_mm == 0.0  # zonder peilopzet is er geen voorraad

    raised = base.replace(target_level_rise_m=0.20)
    # 20 cm op 3,5 % open water is 7 mm over de hele polder
    assert raised.retained_volume_mm == pytest.approx(0.20 * 0.035 * 1000)

    # meer open water bij hetzelfde peil houdt meer vast
    wider = BergenAction(delta_open_water_ha=1000).apply(raised)
    assert wider.retained_volume_mm > raised.retained_volume_mm

    # afvoeren en vasthouden doen niets voor de voorraad
    assert AfvoerenAction(delta_pump_capacity_m3_per_sec=5).apply(
        raised
    ).retained_volume_mm == pytest.approx(raised.retained_volume_mm)
    assert VasthoudenAction(delta_retention_ha=2000).apply(
        raised
    ).retained_volume_mm == pytest.approx(raised.retained_volume_mm)


def test_target_level_trades_drought_against_flooding_one_for_one():
    """Peilopzet koopt voorraad en kost drooglegging, met exact dezelfde centimeters.

    Dat is de spanning tussen te nat en te droog, en het is de reden dat de twee
    uitlezingen niet los van elkaar te optimaliseren zijn.
    """
    storm, base = _reference_storm_and_state()
    without = simulate(base, storm)
    with_rise = simulate(base.replace(target_level_rise_m=0.20), storm)

    # de stijging boven het opgezette peil verandert niet: het open water is even groot
    assert with_rise.dh_max_m == pytest.approx(without.dh_max_m)

    # maar boven het oorspronkelijke peil komt de opzet er een-op-een bij
    assert with_rise.dh_total_above_original_datum_m == pytest.approx(
        without.dh_max_m + 0.20
    )
    assert with_rise.retained_volume_mm > without.retained_volume_mm


def test_both_readouts_come_from_one_simulation():
    """Het world-model-argument: een doorrekening, twee vragen."""
    storm, state = _reference_storm_and_state(target_level_rise_m=0.15)
    result = simulate(state, storm)

    assert result.dh_max_m > 0  # wateroverlast
    assert result.retained_volume_mm > 0  # droogte
    assert result.target_level_rise_m == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# Tekstuitvoer: de terugkeertijd zoals je hem uitspreekt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "return_period, expected_nl, expected_en",
    [
        (0.5, "gemiddeld twee keer per jaar", "twice a year on average"),
        (1.0, "gemiddeld eens per jaar", "once a year on average"),
        (10.0, "eens per 10 jaar", "1-in-10-year"),
        (1000.0, "eens per 1000 jaar", "1-in-1000-year"),
    ],
)
def test_return_period_is_phrased_the_way_it_is_spoken(
    return_period, expected_nl, expected_en
):
    """Een terugkeertijd onder een jaar is een frequentie, geen periode.

    T = 0,5 betekent gemiddeld twee keer per jaar, niet "eens per 0,5 jaar" - zo staat
    het ook in de STOWA-tabel waar deze statistiek uit komt. En "eens per 1 jaar" is
    "eens per jaar". Hele jaren komen zonder decimaal, want `return_period` is een float
    sinds 0.5 bereikbaar moest zijn.
    """
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
        _event_phrase,
    )

    assert expected_nl in _event_phrase(return_period, "nl")
    assert expected_en in _event_phrase(return_period, "en")
    # geen kale getallen met decimaal, en geen "eens per 0.5"
    assert ".0 jaar" not in _event_phrase(return_period, "nl")


@pytest.mark.asyncio
@pytest.mark.parametrize("return_period", [0.5, 1.0, 2.0, 10.0, 1000.0])
@pytest.mark.parametrize("language", ["nl", "en"])
async def test_descriptions_read_cleanly_for_every_return_period(
    test_context, return_period, language
):
    """Geen dubbele lidwoorden, dubbele spaties of ruwe floats in de uitvoer."""
    from talk_with_the_engineer.tools import calculate_store_given_h

    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            return_period=return_period,
            time_of_year="winter",
            length_event_hrs=96.0,
            delta_h_available=1.0,
            language=language,
            **POLDER,
        ),
    )
    text = result.description
    for wrong in (
        " a a ",
        " in a an ",
        "eens per 0.5",
        "eens per 1 jaar",
        ".0 jaar",
        "  ",
    ):
        assert wrong not in text, f"{language} T={return_period}: {wrong!r} in {text!r}"


# --- WP8: de tweezijdig geklemde waterbalans ----------------------------------------
#
# `clamped_scan` is een generalisatie en geen wijziging: het bestaande gedrag moet er als
# bijzonder geval `lo=0, hi=+inf` exact in zitten. Daarom staat de tolerantie hier op
# 1e-12 en niet op de 1e-9 die de rest van dit bestand gebruikt.

CLAMP_TOLERANCE_M = 1e-12

CLAMP_BOUNDS = [
    (0.0, np.inf),  # wateroverlast: het gemaal stopt op streefpeil
    (-0.30, np.inf),  # peilbeheer met marge: voorbemaling
    (-np.inf, 0.0),  # watertekort: de inlaat vult tot streefpeil
    (-0.30, 0.0),  # tweezijdige band
    (-0.20, 0.20),  # dynamisch peilbeheer
]


def _clamped_recursion(delta, lower, upper, initial=0.0):
    """De recursie als lus. De scan moet hier tot op machineprecisie op uitkomen."""
    out = np.empty(len(delta))
    level = initial
    for index, step in enumerate(delta):
        level = min(max(level + step, lower), upper)
        out[index] = level
    return out


def _reference_delta():
    """De uurlijkse peilverandering van de referentiebui, zoals `simulate` hem opbouwt."""
    storm, state = _storm_and_state(
        {
            "time_of_year": "winter",
            "return_period": 1000,
            "length_event_hrs": 96.0,
            "name_rainfall_pattern": "p1a",
            "days_to_discharge": 4,
        }
    )
    result = simulate(state, storm)
    metres_per_m3_per_sec = SECONDS_PER_HOUR / (
        state.area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )
    inflow = result.drainage_l_s_ha * state.area_land_ha / 1000.0
    delta = (inflow - state.pump_capacity_m3_per_sec) * metres_per_m3_per_sec
    per_hour_m = to_hourly(result.rainfall_on_water_per_day_mm / HOURS_PER_DAY) / 1000.0
    direct = np.zeros(len(delta))
    overlap = min(len(per_hour_m), len(direct))
    direct[:overlap] = per_hour_m[:overlap]
    return delta + direct, state, storm, result


@pytest.mark.parametrize("lower,upper", CLAMP_BOUNDS)
def test_clamped_scan_reproduces_the_recursion(lower, upper):
    """De scan is de recursie, niet een benadering ervan."""
    delta, _, _, _ = _reference_delta()
    worst = np.abs(
        clamped_scan(delta, lower, upper) - _clamped_recursion(delta, lower, upper)
    ).max()
    assert worst < CLAMP_TOLERANCE_M, f"lo={lower} hi={upper} wijkt {worst:.2e} m af"


def test_clamped_scan_handles_a_nonzero_initial_level():
    delta, _, _, _ = _reference_delta()
    worst = np.abs(
        clamped_scan(delta, -0.5, 0.5, initial_level_m=-0.2)
        - _clamped_recursion(delta, -0.5, 0.5, initial=-0.2)
    ).max()
    assert worst < CLAMP_TOLERANCE_M


def test_clamped_scan_rejects_an_inverted_band():
    with pytest.raises(ValueError, match="lower_bound_m"):
        clamped_scan(np.zeros(4), 1.0, 0.0)


@pytest.mark.parametrize("storm_kwargs", STORMS)
def test_clamped_scan_generalises_the_cumsum_trick(storm_kwargs):
    """`lo=0, hi=+inf` moet exact het gedrag zijn dat `cumsum`/`minimum.accumulate` gaf.

    Dit is de test die de generalisatie een generalisatie houdt: verschuift hij, dan is de
    waterbalans veranderd en niet alleen de manier waarop hij wordt uitgerekend.
    """
    storm, state = _storm_and_state(storm_kwargs)
    result = simulate(state, storm)
    metres_per_m3_per_sec = SECONDS_PER_HOUR / (
        state.area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )
    inflow = result.drainage_l_s_ha * state.area_land_ha / 1000.0
    delta = (inflow - state.pump_capacity_m3_per_sec) * metres_per_m3_per_sec
    per_hour_m = to_hourly(result.rainfall_on_water_per_day_mm / HOURS_PER_DAY) / 1000.0
    direct = np.zeros(len(delta))
    overlap = min(len(per_hour_m), len(direct))
    direct[:overlap] = per_hour_m[:overlap]

    levels = clamped_scan(delta + direct, 0.0, np.inf)
    assert np.abs(levels - result.water_level_m).max() < CLAMP_TOLERANCE_M


def test_slack_reproduces_the_pumped_series():
    """Alle debietuitlezingen zijn afgeleid van `slack`; dit is de toets daarop."""
    delta, state, storm, result = _reference_delta()
    metres_per_m3_per_sec = SECONDS_PER_HOUR / (
        state.area_open_water_ha * SQUARE_METRES_PER_HECTARE
    )
    levels = clamped_scan(delta, 0.0, np.inf)
    slack = slack_of(levels, delta)
    pumped = state.pump_capacity_m3_per_sec - slack / metres_per_m3_per_sec
    assert np.abs(pumped - result.pumped_m3_per_sec).max() < CLAMP_TOLERANCE_M
    assert np.abs(slack - result.slack_m).max() < CLAMP_TOLERANCE_M


@pytest.mark.parametrize("lower,upper", CLAMP_BOUNDS)
def test_slack_is_only_nonzero_at_a_clamp(lower, upper):
    """Slack is wat de klem deed, dus buiten een klem is hij nul."""
    delta, _, _, _ = _reference_delta()
    levels = clamped_scan(delta, lower, upper)
    slack = slack_of(levels, delta)
    at_a_clamp = (np.abs(levels - lower) < 1e-12) | (np.abs(levels - upper) < 1e-12)
    assert np.all((np.abs(slack) <= 1e-12) | at_a_clamp)


def test_the_mass_balance_closes_with_slack():
    """Aanvoer = weggepompt + eindberging, gerekend via `slack` in plaats van via de reeks."""
    delta, state, storm, result = _reference_delta()
    area_open_water_m2 = state.area_open_water_ha * SQUARE_METRES_PER_HECTARE
    metres_per_m3_per_sec = SECONDS_PER_HOUR / area_open_water_m2

    inflow_m3 = (
        delta / metres_per_m3_per_sec + state.pump_capacity_m3_per_sec
    ).sum() * SECONDS_PER_HOUR
    pumped_m3 = result.pumped_m3_per_sec.sum() * SECONDS_PER_HOUR
    stored_m3 = result.water_level_m[-1] * area_open_water_m2
    assert inflow_m3 - pumped_m3 - stored_m3 == pytest.approx(
        0.0, abs=inflow_m3 * 1e-12
    )


def test_the_level_margin_default_changes_nothing():
    """De generalisatie mag het bestaande antwoord niet aanraken."""
    _, state, storm, result = _reference_delta()
    assert state.level_margin_m == 0.0
    assert result.dh_max_m == pytest.approx(1.8057576857142845, abs=1e-12)
    assert result.dh_min_m == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize(
    "margin_m,expected_gain_cm",
    [
        (0.05, 5.0000),
        (0.10, 10.0000),
        (0.20, 10.5130),
        (0.30, 10.5130),
        (1.00, 10.5130),
    ],
)
def test_prereleasing_saturates_at_the_pump_rate(margin_m, expected_gain_cm):
    """Voorbemaling verzadigt: de eerste tien centimeter marge is volledig effectief.

    Daarna is het op, want het gemaal maalt 0,31 m per dag leeg en de droge uren voor de
    piek zijn beperkt. Dat is de reden dat dit `SATURATED` heet en geen `PLATEAU`: het is
    niet de waterstand die niet lager kan, het is het gemaal dat niet sneller kan.
    """
    _, state, storm, base = _reference_delta()
    with_margin = simulate(state.replace(level_margin_m=margin_m), storm)
    gain_cm = (base.dh_max_m - with_margin.dh_max_m) * 100
    assert gain_cm == pytest.approx(expected_gain_cm, abs=5e-4)


def test_the_drawdown_reached_is_exactly_the_peak_reduction_gained():
    """Met marge kan de stand onder streefpeil zakken; zonder marge nooit.

    En de uitzakking die het gemaal haalt is precies de verlaging van de piek. Dat is de
    verklaring van de verzadiging in de test hierboven, in een gelijkheid: 30 cm marge
    afspreken levert 10,5 cm uitzakking op, en dus 10,5 cm lagere piek. De marge is een
    plafond op de uitzakking, niet de uitzakking zelf.
    """
    _, state, storm, base = _reference_delta()
    assert base.dh_min_m == pytest.approx(0.0, abs=1e-12)

    with_margin = simulate(state.replace(level_margin_m=0.30), storm)
    assert with_margin.level_margin_m == 0.30
    assert with_margin.dh_min_m >= -0.30
    assert with_margin.dh_min_m == pytest.approx(-0.105130, abs=5e-6)
    assert -with_margin.dh_min_m == pytest.approx(
        base.dh_max_m - with_margin.dh_max_m, abs=1e-9
    )


def test_prereleasing_is_reported_as_saturated_and_not_as_plateau():
    """Het verschil tussen `plateau` en `saturated` is wie de klem is; zie OptimumKind."""
    _, state, storm, base = _reference_delta()
    target = base.dh_max_m - 0.05
    result = solve(state, storm, PeilmargeAction(), target)
    assert result.status is SolveStatus.EXACT
    assert result.magnitude == pytest.approx(0.05, abs=2e-3)

    impossible = solve(state, storm, PeilmargeAction(), base.dh_max_m - 0.50)
    assert impossible.status is SolveStatus.ACTION_INFEASIBLE
    assert impossible.magnitude_optimum_kind is OptimumKind.SATURATED
    assert impossible.feasible_dh_min_m == pytest.approx(
        base.dh_max_m - 0.105130, abs=5e-6
    )


def test_prereleasing_has_no_investment_cost():
    """Een verzonnen prijs is hier erger dan geen prijs; zie PeilmargeAction."""
    _, state, _, _ = _reference_delta()
    action = PeilmargeAction(delta_level_margin_m=0.2)
    assert action.cost(state) is None
    assert action.cost_range(state) is None


def test_the_core_uses_only_the_portable_numpy_subset():
    """De kern moet in de numpy-deelverzameling blijven die JAX een-op-een ondersteunt.

    Geen lus over de tijdas en geen `.item()`/`float()` binnen de twee primitieven, want
    dat is precies wat een tweede backend later duur maakt. Een AST-check en geen grep,
    zodat een lus in een docstring of een comment niet meetelt.
    """
    import ast
    import inspect

    from talk_with_the_engineer.tools.toolset_rules_of_thumb import simulate as module

    source = inspect.getsource(module)
    tree = ast.parse(source)
    guarded = {"clamped_scan", "slack_of"}
    offences = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in guarded):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, (ast.For, ast.comprehension)):
                offences.append(f"{node.name}: lus over de as")
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "item"
            ):
                offences.append(f"{node.name}: .item()")
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "float"
            ):
                offences.append(f"{node.name}: float()")
    assert not offences, offences

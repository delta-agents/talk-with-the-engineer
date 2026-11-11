"""Eigenschappen van de rekenkern.

Deze tests dekken defectKLASSEN en niet de losse defecten:
massabehoud, equivalentie met de recursie, de vorm van de responscurves, en of het rondje
sluit over het hele haalbare bereik.
"""

import time

import importlib.util
from functools import partial
from operator import attrgetter

import numpy as np
import pytest

from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH
from talk_with_the_engineer.core.actions import (
    DischargeAction,
    StorageAction,
    ControlAction,
    RetentionAction,
)
from talk_with_the_engineer.core.results import (
    OptimumKind,
    SolveStatus,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.transition import (
    HOURS_PER_DAY,
    _StormKey,
    _drainage_daily_for_storm,
    blend_retention,
    clamped_scan,
    delay_daily,
    simulate,
    slack_of,
    to_hourly,
    water_level_series,
)
from talk_with_the_engineer.core.stats.rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.core.inverse import evaluate, solve

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


def _storm_id(storm_kwargs):
    return f"{storm_kwargs['time_of_year']}T{storm_kwargs['return_period']}"


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
    """Massabehoud over de vertraging, voor elke vertraging.

    Een blokkenschema dat de reeks over `days_to_retain` uitsmeert zonder te normaliseren
    houdt water over of laat het verdwijnen, en dat is aan de piek niet te zien.
    """
    daily = np.array([6.44, 17.95, 27.25, 32.30, 25.86, 14.35, 5.05])
    delayed = delay_daily(daily, days_to_retain)
    assert delayed.sum() == pytest.approx(daily.sum(), rel=1e-12)
    assert len(delayed) == len(daily) + days_to_retain
    assert (delayed >= 0).all()


@pytest.mark.parametrize("storm_kwargs", STORMS, ids=_storm_id)
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


@pytest.mark.parametrize("storm_kwargs", STORMS, ids=_storm_id)
def test_discharge_is_monotonically_decreasing(storm_kwargs):
    """Meer gemaalcapaciteit helpt altijd, zonder omslagpunt."""
    storm, state = _storm_and_state(storm_kwargs)
    action = DischargeAction()
    magnitudes = np.linspace(0, action.upper_bound(state), 40)
    values = [simulate(action.at(m).apply(state), storm).dh_max_m for m in magnitudes]
    assert np.all(np.diff(values) <= 1e-12), (
        f"afvoeren is niet monotoon dalend bij {storm_kwargs}"
    )


@pytest.mark.parametrize("storm_kwargs", STORMS, ids=_storm_id)
@pytest.mark.parametrize(
    "action", [StorageAction(), RetentionAction()], ids=attrgetter("name_nl")
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


@pytest.mark.parametrize("storm_kwargs", STORMS, ids=_storm_id)
@pytest.mark.parametrize(
    "action",
    [StorageAction(), DischargeAction(), RetentionAction()],
    ids=attrgetter("name_nl"),
)
def test_roundtrip_closes_over_the_whole_feasible_range(storm_kwargs, action):
    """Het rondje sluit over het hele haalbare bereik en niet alleen in het midden.

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
    for action in (StorageAction(), DischargeAction(), RetentionAction()):
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

    for action in (StorageAction(), DischargeAction(), RetentionAction()):
        solve(state, storm, action, 1.0)
        start = time.perf_counter()
        for _ in range(10):
            solve(state, storm, action, 1.0)
        solve_ms = (time.perf_counter() - start) / 10 * 1000
        assert solve_ms < 10.0, f"solve({action.name_nl}) duurt {solve_ms:.2f} ms"


def test_polder_balance_includes_the_two_terms_the_spreadsheet_omits():
    """De balans telt krimpend land en directe neerslag mee; het rekenblad doet dat niet.

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
    action = StorageAction(delta_open_water_ha=1060)
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
    from talk_with_the_engineer.core.cost import (
        COST_OPEN_WATER,
        COST_PUMP_CAPACITY,
        COST_RETENTION,
    )

    for unit_cost in (COST_OPEN_WATER, COST_PUMP_CAPACITY, COST_RETENTION):
        assert unit_cost.low <= unit_cost.typical <= unit_cost.high
        assert unit_cost.source and unit_cost.price_level and unit_cost.unit


def test_store_and_retention_costs_are_linear_in_the_area():
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5)

    bergen = StorageAction(delta_open_water_ha=100)
    assert bergen.cost(state) == pytest.approx(100 * 135_000)
    assert bergen.at(200).cost(state) == pytest.approx(2 * bergen.cost(state))

    vasthouden = RetentionAction(delta_retention_ha=1000)
    assert vasthouden.cost(state) == pytest.approx(1000 * 2_400)
    assert vasthouden.at(2000).cost(state) == pytest.approx(2 * vasthouden.cost(state))


def test_discharge_cost_is_linear_by_choice():
    """Afvoeren wordt lineair gerekend, en dat is een vuistregelvereenvoudiging.

    Deze test legt de keuze vast en maakt hem meetbaar: hij toont zowel dat `cost`
    lineair is als hoeveel dat afwijkt van de trapkost die de brondata laat zien. Gaat
    hij om, dan is de keuze veranderd en niet per ongeluk.
    """
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5)
    rate = DischargeAction().unit_cost.typical  # EUR per m3/s

    assert DischargeAction().cost(state) == 0.0

    small = DischargeAction(delta_pump_capacity_m3_per_sec=0.5)
    assert small.cost(state) == pytest.approx(0.5 * rate)
    # lineair: twee keer de toename is twee keer de kosten
    assert small.at(1.0).cost(state) == pytest.approx(2 * small.cost(state))

    # en dit is wat de vereenvoudiging kost: de trapkost-lezing van dezelfde uitbreiding
    replacement = rate * small.replacement_quantity(state)
    assert replacement == pytest.approx(5.5 * rate)
    assert replacement > 10 * small.cost(state)


def test_costs_can_be_switched_off():
    state = PolderState(area_ha=4000, pct_open_water=3.5, pump_capacity_m3_per_sec=5)
    action = StorageAction(delta_open_water_ha=100, unit_cost=None)
    assert action.cost(state) is None
    assert action.cost_range(state) is None
    assert action.at(200).unit_cost is None


def test_cheapest_per_hectare_is_not_cheapest_per_centimetre():
    """Vasthouden is het goedkoopst per hectare en toch niet de goedkoopste maatregel.

    Dat is de omkering waarvoor je een model nodig hebt in plaats van een vuistregel over
    eenheidsprijzen: vasthouden kost per hectare een fractie van bergen, maar heeft er
    honderden keren zoveel nodig.
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

    assert RetentionAction().unit_cost.typical < StorageAction().unit_cost.typical / 50

    probe = solve(state, storm, RetentionAction(), 0.0)
    target = probe.feasible_dh_min_m + 1e-4

    costs, quantities = {}, {}
    for action in (StorageAction(), DischargeAction(), RetentionAction()):
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
    rate = DischargeAction().unit_cost.typical

    replacement_wint = {}
    for target in (1.70, 1.50, 1.20, 1.00, 0.60):
        bergen = solve(state, storm, StorageAction(), target)
        afvoeren = solve(state, storm, DischargeAction(), target)
        assert bergen.status is SolveStatus.EXACT
        assert afvoeren.status is SolveStatus.EXACT

        # lineair: afvoeren altijd goedkoper
        assert afvoeren.cost < bergen.cost, f"bij {target * 100:.0f} cm"

        replacement = rate * DischargeAction().at(
            afvoeren.magnitude
        ).replacement_quantity(state)
        replacement_wint[target] = replacement < bergen.cost

    # trapkost: de richting ligt vast - boven de omslagnorm wint bergen (weinig
    # hectares tegen de vervangingsvloer van een heel gemaal), eronder afvoeren
    # (veel hectares tegen een gemaal dat toch al groot moest worden)
    assert not replacement_wint[1.50], "milde norm: bergen hoort te winnen"
    assert replacement_wint[0.60], "strenge norm: afvoeren hoort te winnen"


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
    voorgesteld.
    """
    storm, base = _reference_storm_and_state()
    variants = [
        base,
        StorageAction(delta_open_water_ha=200).apply(base),
        DischargeAction(delta_pump_capacity_m3_per_sec=2).apply(base),
        RetentionAction(delta_retention_ha=2000).apply(base),
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
    wider = StorageAction(delta_open_water_ha=1000).apply(raised)
    assert wider.retained_volume_mm > raised.retained_volume_mm

    # afvoeren en vasthouden doen niets voor de voorraad
    assert DischargeAction(delta_pump_capacity_m3_per_sec=5).apply(
        raised
    ).retained_volume_mm == pytest.approx(raised.retained_volume_mm)
    assert RetentionAction(delta_retention_ha=2000).apply(
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
    from talk_with_the_engineer.interface.descriptions import (
        _event_phrase,
    )

    storm = _StormKey(return_period, "summer", 96.0, "R", "p1c", 3)

    assert expected_nl in _event_phrase(storm, "nl")
    assert expected_en in _event_phrase(storm, "en")
    # geen kale getallen met decimaal, en geen "eens per 0.5"
    assert ".0 jaar" not in _event_phrase(storm, "nl")


@pytest.mark.parametrize("volume", [12.0, 86.6, 150.0])
def test_an_own_rainfall_total_is_named_by_its_depth_and_not_by_a_rarity(volume):
    """Geef je de neerslagsom zelf, dan is er geen terugkeertijd om de bui mee aan te duiden.

    Er een verzinnen zou de bui een status geven die hij niet heeft: "eens per 100 jaar" is
    een uitspraak van de statistiek en niet van de beller. De som zelf is dan de enige
    eerlijke aanduiding.
    """
    from talk_with_the_engineer.interface.descriptions import (
        _event_phrase,
    )

    storm = _StormKey(None, "summer", 96.0, "R", "p1c", 3, volume)

    assert f"{volume:g} mm" in _event_phrase(storm, "nl")
    assert f"{volume:g} mm" in _event_phrase(storm, "en")
    for language in ("nl", "en"):
        assert "jaar" not in _event_phrase(storm, language)
        assert "year" not in _event_phrase(storm, language)


@pytest.mark.asyncio
@pytest.mark.parametrize("return_period", [0.5, 1.0, 2.0, 10.0, 1000.0])
@pytest.mark.parametrize("language", ["nl", "en"])
async def test_descriptions_read_cleanly_for_every_return_period(
    test_context, return_period, language
):
    """Geen dubbele lidwoorden, dubbele spaties of ruwe floats in de uitvoer."""
    from talk_with_the_engineer.interface.tools.store import calculate_store_given_h

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


# --- de tweezijdig geklemde waterbalans ----------------------------------------
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
    """De uurlijkse waterstandverandering van de referentiebui, zoals `simulate` hem opbouwt."""
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
    result = solve(state, storm, ControlAction(), target)
    assert result.status is SolveStatus.EXACT
    assert result.magnitude == pytest.approx(0.05, abs=2e-3)

    impossible = solve(state, storm, ControlAction(), base.dh_max_m - 0.50)
    assert impossible.status is SolveStatus.ACTION_INFEASIBLE
    assert impossible.magnitude_optimum_kind is OptimumKind.SATURATED
    assert impossible.feasible_dh_min_m == pytest.approx(
        base.dh_max_m - 0.105130, abs=5e-6
    )


def test_prereleasing_has_no_investment_cost():
    """Een verzonnen prijs is hier erger dan geen prijs; zie ControlAction."""
    _, state, _, _ = _reference_delta()
    action = ControlAction(delta_level_margin_m=0.2)
    assert action.cost(state) is None
    assert action.cost_range(state) is None


ALL_RULES = frozenset({"loops", "sync", "array_if", "inplace", "backend"})
BACKEND_NEUTRAL = frozenset({"inf", "nan", "pi", "ndarray", "newaxis"})
"""Namen uit numpy die geen array-OPERATIE zijn en dus niet door de schakelaar hoeven.

`np.inf` is een python-float; er is geen tweede backend met een andere oneindigheid. Idem
`np.nan` en `np.pi`. `np.ndarray` en `np.newaxis` zijn typen respectievelijk een indexerings-
constante. De regel gaat over rekenen, niet over constanten - en een uitzondering die je kunt
opsommen is beter dan een regel die je uitzet.
"""
SYNC_ONLY = frozenset({"sync"})


def _portability_offences(module, function_names, rules):
    """De portabiliteitsregels van de kern, als AST-controle op de genoemde functies.

    **Per functie een andere set regels, en die knip is de kern van deze test.** De regel is
    "in-place mutatie alleen op de BOUWKANT, niet in de recursie" - en die twee zien er in de
    AST identiek uit. Hetzelfde geldt voor lussen: een lus over de topologische DIEPTE mag
    (drie a vier lang) en een lus over de KNOPEN niet, en `ast.For` kent dat verschil niet.

    Dus:

    * `ALL_RULES` voor de primitieven. Daar is elke indextoewijzing een mutatie van de
      scan-toestand en elke `if` op een arraywaarde een leesactie die bij tracen niet bestaat.
      Die functies hebben ook geen enkele lus, dus "geen lus" is daar eenduidig.
    * `SYNC_ONLY` voor de passes eromheen. `_forward_pass` lust over de diepte en vult
      uitvoerbuffers; `node_forcing` lust over retentiegroepen - een handvol, expliciet niet
      over knopen. Dat is de bouwkant. Wat daar wel eenduidig is: `.item()` en `float()`
      forceren synchronisatie en breken tracing, waar ze ook staan.

    Dat de tweede laag zo dun is, is een eerlijke grens van een statische check en geen
    omissie. Wat hij niet kan zien, moet de backendtest zien.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(module))
    offences = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in function_names):
            continue
        # alleen de BODY, niet de signatuur. Annotaties en default-waarden worden bij
        # def-tijd geevalueerd en zijn geen backend-aanroep; `-> np.ndarray` en
        # `upper_bound_m: float = np.inf` mogen dus blijven staan.
        body = [inner for statement in node.body for inner in ast.walk(statement)]
        for inner in body:
            if "loops" in rules and isinstance(inner, (ast.For, ast.comprehension)):
                offences.append(f"{node.name}: lus over de as")
            if "sync" in rules:
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
            if "array_if" in rules and isinstance(inner, ast.If):
                test = ast.unparse(inner.test)
                if any(
                    marker in test
                    for marker in ("np.any", "np.all", ".any()", ".all()")
                ):
                    offences.append(f"{node.name}: if op een arraywaarde ({test})")
            if (
                "backend" in rules
                and isinstance(inner, ast.Attribute)
                and isinstance(inner.value, ast.Name)
                and inner.value.id == "np"
                and inner.attr not in BACKEND_NEUTRAL
            ):
                offences.append(
                    f"{node.name}: np.{inner.attr} in plaats van xp.{inner.attr}"
                )
            if "inplace" in rules and isinstance(inner, (ast.Assign, ast.AugAssign)):
                targets = (
                    inner.targets if isinstance(inner, ast.Assign) else [inner.target]
                )
                for target in targets:
                    if isinstance(target, ast.Subscript):
                        offences.append(
                            f"{node.name}: in-place mutatie ({ast.unparse(target)})"
                        )
    return offences


def test_the_primitives_stay_in_the_portable_numpy_subset():
    """Vier van de vijf portabiliteitsregels, op de primitieven.

    Wat erbij komt is precies wat een tracer breekt en wat een AST-check wel kan zien: een
    `if` op een arraywaarde, mutatie van de scan-toestand, en - sinds de backend een
    schakelaar is - een rechtstreekse `np.`-aanroep waar `xp.` hoort. Die laatste maakt de
    schakelaar een EIGENSCHAP in plaats van een belofte: `xp = numpy` zetten en er daarna
    langsheen blijven programmeren is precies hoe een tweede backend duur wordt.

    En `_reflected_scan` staat er nu in - de belangrijkste toevoeging, want dat is de functie
    die het NETWERK aanroept. `clamped_scan(delta, -margin, inf)` neemt het snelpad, dus de
    bewaakte set dekte de hete functie niet.
    """
    from talk_with_the_engineer.core import transition as module
    from talk_with_the_engineer.core import network

    offences = _portability_offences(
        module,
        {"clamped_scan", "_compose_at_distance", "_reflected_scan", "slack_of"},
        ALL_RULES,
    )
    offences += _portability_offences(
        network, {"levels_from", "derate_once"}, ALL_RULES
    )
    assert not offences, offences


def test_the_build_side_may_mutate_but_not_synchronise():
    """De passes eromheen: lussen en buffers mogen, `.item()` en `float()` niet.

    Dat deze laag zo dun is, is een grens van een statische check. Een lus over de diepte en
    een lus over de knopen zien er in de AST hetzelfde uit, en dus kan deze test het verschil
    niet maken dat de regel zelf wel maakt. Wat hij wel kan: forceren dat er nergens naar een
    scalaire python-waarde wordt teruggevallen, want dat breekt tracing waar het ook staat.
    """
    from talk_with_the_engineer.core import network as module

    offences = _portability_offences(
        module, {"_forward_pass", "node_forcing"}, SYNC_ONLY
    )
    assert not offences, offences


def test_the_topology_loop_is_the_one_python_loop_and_it_stays_outside():
    """`_compute_topological_levels` is een python-lus over de knoop-as, en dat moet zo blijven.

    Hij hoort niet in de bewaakte set. De topologie is STATISCH - `downstream` kan niet
    wijzigen zonder een nieuwe `SystemState` - dus hij hoort buiten het getraceerde deel, en
    hem vectoriseren zou hem juist naar binnen halen. Dat hij gecacht is, is wat hem daar
    houdt: een keer per systeem, niet een keer per doorrekening.

    Deze test legt de KEUZE vast en niet de implementatie: raakt die lus ooit weg, dan is de
    knip tussen bouwkant en rekenkant verschoven en hoort dat besluit opnieuw opgeschreven
    te worden.
    """
    from talk_with_the_engineer.core import system as module

    offences = _portability_offences(
        module, {"_compute_topological_levels"}, frozenset({"loops"})
    )
    assert offences, (
        "als deze functie geen python-lus meer heeft, is de knip tussen bouwkant en "
        "rekenkant verschoven "
        "en hoort dit besluit opnieuw te worden opgeschreven"
    )


def test_the_backend_is_a_switch_and_not_a_promise():
    """De kern rekent werkelijk DOOR `xp` heen, en dat is te meten.

    Een moduleconstante `xp = numpy` neerzetten en er daarna langsheen blijven programmeren is
    precies hoe een tweede backend duur wordt. De AST-test verbiedt `np.` in de primitieven;
    deze test toetst de andere kant: dat er dan ook echt iets door de schakelaar gaat.

    De spion geeft numpy door en telt mee, dus het antwoord hoort identiek te zijn. Zou dat
    niet zo zijn, dan hangt de kern aan iets anders dan de backend.
    """
    from talk_with_the_engineer.core import transition as core

    class CountingBackend:
        def __init__(self):
            self.calls = 0

        def __getattr__(self, name):
            self.calls += 1
            return getattr(np, name)

    delta = np.array([0.1, -0.3, 0.2, 0.05, -0.4, 0.3])
    reference = core.clamped_scan(delta, -0.2, 0.4)

    spy = CountingBackend()
    original = core.xp
    core.xp = spy
    try:
        through_switch = core.clamped_scan(delta, -0.2, 0.4)
    finally:
        core.xp = original

    assert spy.calls > 10, f"de kern raakte de backend maar {spy.calls} keer aan"
    assert np.allclose(reference, through_switch)


def test_the_running_minimum_is_the_one_seam_that_needs_a_second_implementation():
    """`xp.minimum.accumulate` vertaalt NIET een-op-een, en dat is de hele reden voor deze naad.

    In JAX bestaat `jnp.minimum.accumulate` wel, maar hij valt terug op een sequentiele
    `lax.scan` - O(n) diepte over de tijdas, precies wat de scan moest vermijden. De juiste
    JAX-vorm is `lax.cummin`. Deze test legt vast dat er maar EEN plek is waar dat uitmaakt,
    zodat het omzetten van de backend een functie is en geen zoektocht.
    """
    import ast
    import inspect

    from talk_with_the_engineer.core import transition as module

    source = inspect.getsource(module)
    tree = ast.parse(source)
    accumulate_sites = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        for inner in ast.walk(node)
        if isinstance(inner, ast.Attribute) and inner.attr == "accumulate"
    ]
    assert accumulate_sites == ["running_minimum"], accumulate_sites


# --- de tweede backend, als hij er is ------------------------------------------------

JAX_AVAILABLE = importlib.util.find_spec("jax") is not None


def _jax_running_minimum(values):
    """`running_minimum` voor JAX, met een niet-negatieve as: XLA staat `axis=-1` niet toe."""
    from jax import lax

    return lax.cummin(values, axis=values.ndim - 1)


def _jax_scatter_add(values, index, size):
    """`scatter_add` voor JAX: optellen per segment in plaats van in-place `np.add.at`."""
    import jax
    import jax.numpy as jnp

    return jax.ops.segment_sum(values, jnp.asarray(index), num_segments=size)


def test_the_backend_defaults_to_numpy_whether_or_not_jax_is_installed():
    """De schakelaar staat op numpy, en dat hangt niet af van wat er geinstalleerd is.

    Dat is het hele punt van "optionele feature": `pixi install -e jax` mag de uitkomsten van
    de zes+twee+twee tools niet verschuiven. De omzetting is een aparte, bewuste stap - zie
    een bewuste stap - en deze test zorgt dat hij niet per ongeluk gebeurt doordat
    iemand een omgeving installeert.

    Bewust GEEN assertie op of jax importeerbaar is: dat hangt af van in welke omgeving je de
    suite draait, en beide zijn geldig. Wat in beide moet gelden is dit.
    """
    from talk_with_the_engineer.core import transition as core

    assert core.xp is np


@pytest.mark.skipif(
    not JAX_AVAILABLE, reason="jax is een optionele feature; pixi install -e jax"
)
def test_the_primitive_gives_the_same_answer_under_jax():
    """De ankertest tussen de backends, klein: dezelfde monoide, twee backends, float64.

    Dit is wat de schakelaar waard is. En het is geen tautologie: onder numpy loopt het
    snelpad via `cumsum` plus `minimum.accumulate`, onder JAX via `lax.cummin` - en die
    schrijft zichzelf bij differentieren om naar een parallelle prefix-scan. Twee
    implementaties van dezelfde monoide, tegen elkaar gehouden.

    De naad is EEN functie, en dat is precies wat deze test aantoont: `xp` en
    `running_minimum` omzetten is alles wat er nodig is.
    """
    import jax
    import jax.numpy as jnp

    jax.config.update("jax_enable_x64", True)

    from talk_with_the_engineer.core import transition as core

    rng = np.random.default_rng(15)
    delta = rng.normal(size=240) * 1e-3

    reference_one_sided = core.clamped_scan(delta, -0.1, np.inf)
    reference_two_sided = core.clamped_scan(delta, -0.1, 0.05)

    original_xp, original_seam = core.xp, core.running_minimum
    core.xp = jnp
    core.running_minimum = _jax_running_minimum
    try:
        jax_one_sided = np.asarray(core.clamped_scan(jnp.asarray(delta), -0.1, np.inf))
        jax_two_sided = np.asarray(core.clamped_scan(jnp.asarray(delta), -0.1, 0.05))
    finally:
        core.xp, core.running_minimum = original_xp, original_seam

    assert np.allclose(jax_one_sided, reference_one_sided, atol=1e-12)
    assert np.allclose(jax_two_sided, reference_two_sided, atol=1e-12)


def _with_jax(fn):
    """Draai `fn` met de kern op de JAX-backend en zet hem daarna terug.

    De naad is twee namen - `xp` en `running_minimum` - en dat is precies wat deze helper
    aantoont. Zou het meer zijn, dan stond het hier.
    """
    import jax.numpy as jnp

    from talk_with_the_engineer.core import transition as core

    original_xp, original_seam = core.xp, core.running_minimum
    core.xp = jnp
    core.running_minimum = _jax_running_minimum
    try:
        return fn()
    finally:
        core.xp, core.running_minimum = original_xp, original_seam


@pytest.mark.skipif(
    not JAX_AVAILABLE, reason="jax is een optionele feature; pixi install -e jax"
)
@pytest.mark.parametrize("upper", [np.inf, 0.05], ids=["snelpad", "tweezijdig"])
def test_both_backends_agree_on_network_scale(upper):
    """Dezelfde monoide, twee backends, op de vorm die het netwerk gebruikt.

    En dit is geen tautologie. Onder numpy loopt het snelpad via `cumsum` plus
    `minimum.accumulate`; onder JAX via `lax.cummin`, die bij differentieren zichzelf omschrijft
    naar een parallelle prefix-scan. Het tweezijdige pad is onder beide de log-diepte scan.
    Twee implementaties, tegen elkaar gehouden op 8500 knopen x 240 uur.

    Gemeten: 6,9e-17 op het snelpad en exact nul op het tweezijdige. De eis was 1e-12.
    """
    import jax
    import jax.numpy as jnp

    from talk_with_the_engineer.core import transition as core

    jax.config.update("jax_enable_x64", True)
    delta = np.random.default_rng(152).normal(size=(2000, 240)) * 1e-3

    reference = core.clamped_scan(delta, -0.1, upper)
    through_jax = np.asarray(
        _with_jax(partial(core.clamped_scan, jnp.asarray(delta), -0.1, upper))
    )
    assert np.abs(through_jax - reference).max() < 1e-12


@pytest.mark.skipif(
    not JAX_AVAILABLE, reason="jax is een optionele feature; pixi install -e jax"
)
def test_the_adjoint_matches_a_central_difference():
    """De gradient door de primitief heen, tegen een onafhankelijke controle.

    Dit is waar #32 over gaat. Niet "SLSQP in JAX" maar EEN backward pass die zegt waar in het
    net een euro het meeste doet. Hier op de kleinste vorm daarvan: de afgeleide van de som van
    de standen naar elke tijdstap.

    Centrale differentie als controle en niet een tweede autodiff, want dan vergelijk je twee
    benaderingen met elkaar. Gemeten relatieve fout 5,7e-13, en alle tekens gelijk.

    **Wat dit NIET dekt:** de derating-iteratie in `simulate_network`. Die stopt op een
    data-afhankelijke conditie, en `lax.while_loop` is niet reverse-mode
    differentieerbaar. De klem in `clamped_scan` is dat wel, want die lus heeft een statisch
    aantal stappen en rolt uit.
    """
    import jax
    import jax.numpy as jnp

    from talk_with_the_engineer.core import transition as core

    jax.config.update("jax_enable_x64", True)
    delta = np.random.default_rng(153).normal(size=48) * 1e-3

    def check():
        def objective(values):
            return core.clamped_scan(values, -0.1, jnp.inf).sum()

        gradient = np.asarray(jax.grad(objective)(jnp.asarray(delta)))

        step = 1e-6
        finite = []
        for index in range(len(delta)):
            up, down = delta.copy(), delta.copy()
            up[index] += step
            down[index] -= step
            finite.append(
                (
                    float(objective(jnp.asarray(up)))
                    - float(objective(jnp.asarray(down)))
                )
                / (2 * step)
            )
        return gradient, np.asarray(finite)

    gradient, finite = _with_jax(check)

    scale = max(np.abs(finite).max(), 1e-12)
    assert np.abs(gradient - finite).max() / scale < 1e-9
    assert np.array_equal(np.sign(gradient), np.sign(finite))


@pytest.mark.skipif(
    not JAX_AVAILABLE, reason="jax is een optionele feature; pixi install -e jax"
)
def test_one_gradient_over_the_national_scale_is_affordable():
    """De maat waar #32 op rust, gemeten op deze code in plaats van op een prototype.

    Het ontwerpdocument voorspelde bij 8500 knopen 6,2 ms voorwaarts en 39 ms voor de
    gradient. Gemeten na jit: ongeveer 6 ms voorwaarts en 20 ms voor de gradient, dus een
    verhouding van ongeveer 1 op 3,5 - goedkoper dan voorspeld.

    Waar het om gaat is de vergelijking met de andere as: numpy doet diezelfde 8500 knopen
    voorwaarts in ruim 22 ms en heeft GEEN gradient. Dat is de sprong, en het is een andere as
    dan fidelity.

    De grenzen staan ruim: dit is een prestatietest op een laptop-CPU en hij hoort een
    ontspoorde implementatie te vangen, niet een trage machine af te keuren.
    """
    import time

    import jax
    import jax.numpy as jnp

    from talk_with_the_engineer.core import transition as core

    jax.config.update("jax_enable_x64", True)
    delta = np.random.default_rng(154).normal(size=(8500, 240)) * 1e-3

    def measure():
        values = jnp.asarray(delta)

        def total(x):
            return core.clamped_scan(x, -0.1, np.inf).sum()

        forward = jax.jit(total)
        backward = jax.jit(jax.grad(total))
        forward(values).block_until_ready()
        backward(values).block_until_ready()

        start = time.perf_counter()
        forward(values).block_until_ready()
        forward_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        gradient = backward(values)
        gradient.block_until_ready()
        backward_ms = (time.perf_counter() - start) * 1000
        return forward_ms, backward_ms, np.asarray(gradient)

    forward_ms, backward_ms, gradient = _with_jax(measure)

    assert gradient.shape == delta.shape
    assert backward_ms < 500, f"gradient {backward_ms:.0f} ms"
    assert backward_ms < 20 * max(forward_ms, 0.1), (
        f"voorwaarts {forward_ms:.1f} ms, gradient {backward_ms:.1f} ms - de verhouding "
        "hoort een kleine factor te zijn en niet een orde"
    )


@pytest.mark.skipif(
    not JAX_AVAILABLE, reason="jax is een optionele feature; pixi install -e jax"
)
def test_the_whole_network_pass_is_differentiable():
    """De gradient door een HELE netwerkdoorrekening heen, tegen een centrale differentie.

    Dit is waar issue #45 op uitkomt. Niet een primitief en niet een losse stap, maar
    `simulate_network` van begin tot eind: de forcering per knoop, de passes over de
    topologische lagen met hun scatter-add, en de derating met een vast budget.

    Drie naadnamen worden omgezet - `xp`, `running_minimum` en `scatter_add` - en verder
    niets. Dat is de meting achter de bewering dat de kern portabel is: zou er meer nodig
    zijn, dan stond het hier.

    Centrale differentie als controle en niet een tweede autodiff, want anders vergelijk je
    twee benaderingen met elkaar. De knoop zonder benedenstroomse buur heeft afgeleide nul -
    zijn gemaal loost op de buitenwereld en de klem is daar niet actief - en de twee andere
    komen op 2,6e-10 overeen.
    """
    import dataclasses

    import jax
    import jax.numpy as jnp

    from talk_with_the_engineer.core.connection import (
        Connection,
    )
    from talk_with_the_engineer.core.system import SystemState
    from talk_with_the_engineer.core import network
    from talk_with_the_engineer.core import transition as core

    jax.config.update("jax_enable_x64", True)

    polders = [
        PolderState(
            area_ha=4000,
            pct_open_water=3.5,
            connections=(Connection(to="b", capacity_out_m3_per_sec=5.0),),
        ),
        PolderState(
            area_ha=3000,
            pct_open_water=3.0,
            connections=(Connection(to="b", capacity_out_m3_per_sec=4.0),),
        ),
        PolderState(
            area_ha=8000,
            pct_open_water=3.5,
            connections=(Connection(capacity_out_m3_per_sec=10.0),),
        ),
    ]
    base = SystemState.from_polders(polders, names=["p0", "p1", "b"])
    storm = StoreInputGivenH(delta_h_available=1.0, return_period=100, **POLDER)

    original = (core.xp, core.running_minimum, core.scatter_add)
    try:
        core.xp = jnp
        core.running_minimum = _jax_running_minimum
        core.scatter_add = _jax_scatter_add

        def objective(capacities):
            system = dataclasses.replace(base, capacity_out_m3_per_sec=capacities)
            return network.simulate_network(system, storm, iterations=6).dh_max_m.sum()

        capacities = jnp.asarray([5.0, 4.0, 10.0])
        gradient = np.asarray(jax.grad(objective)(capacities))

        step = 1e-6
        finite = np.array(
            [
                (
                    float(objective(capacities.at[index].add(step)))
                    - float(objective(capacities.at[index].add(-step)))
                )
                / (2 * step)
                for index in range(3)
            ]
        )
    finally:
        core.xp, core.running_minimum, core.scatter_add = original

    assert np.abs(gradient - finite).max() < 1e-8
    # meer afvoercapaciteit verlaagt de stand, dus de afgeleide is niet positief
    assert (gradient <= 1e-12).all()


@pytest.mark.parametrize(
    "length_event_hrs,days_to_discharge,expected_days",
    [
        (48.0, 2, 3),
        (48.0, 4, 5),
        (96.0, 3, 6),
        (96.0, 4, 7),
        (192.0, 2, 9),
        (192.0, 3, 10),
        (192.0, 4, 11),
    ],
)
def test_the_discharge_runs_past_the_end_of_the_event(
    length_event_hrs, days_to_discharge, expected_days
):
    """Het afvoerverloop stopt niet bij de buiduur, en het stopt niet na vier dagen.

    De vraag uit de terugkoppeling van augustus 2026: de buiduur loopt tot 192 uur en de
    gekozen afvoer tot 4 dagen, dus wat gebeurt er dan met het afvoerverloop? Antwoord: de
    laatste regendag begint pas af te voeren op dag `length_event_days` en doet daar
    `days_to_discharge` dagen over, dus de reeks loopt tot `buiduur + afvoerduur - 1`. Bij
    een bui van 8 dagen met een regionale afvoer over 4 dagen is dat 11 dagen.

    `_get_model_matrix` rekent die lengte uit in plaats van hem vast te zetten, en dat is
    op twee plekken vastgelegd: hier, en als `discharge_series_days` in de `data` van de
    maatregeltools - zodat een lezer van het antwoord hem ook ziet.
    """
    daily, _, _, _ = _drainage_daily_for_storm(
        100.0, "summer", length_event_hrs, "R", "p1c", days_to_discharge, True
    )
    assert len(daily) == expected_days

    # en er gaat geen millimeter verloren in die verlenging
    rainfall, _ = get_rainfall(
        _StormKey(100.0, "summer", length_event_hrs, "R", "p1c", days_to_discharge)
    )
    assert daily.sum() == pytest.approx(rainfall.sum(), rel=1e-9)


def test_holding_water_stretches_the_discharge_even_further():
    """Vasthouden komt bovenop, en dat is de bovengrens van de tijdas.

    Acht dagen bui, vier dagen afvoer, vier dagen vasthouden: 11 + 4 = 15 dagen. Massa
    blijft behouden - vasthouden verschuift de afvoer, het laat hem niet verdwijnen.
    """
    daily, _, _, _ = _drainage_daily_for_storm(
        100.0, "summer", 192.0, "R", "p1c", 4, True
    )
    delayed = blend_retention(daily, 4, 1.0)
    assert len(delayed) == 15
    assert delayed.sum() == pytest.approx(daily.sum(), rel=1e-9)

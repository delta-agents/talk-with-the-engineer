"""Gouden regressietest: de rekenkern moet Ton's rekenblad reproduceren.

Dit is de enige externe waarheid die we hebben. De tolerantie is 1e-12 m; loopt die op,
dan is de waterbalans veranderd en niet alleen de parameterisatie eromheen.

Zie tests/data/README.md voor de herkomst van de referentiecasus.
"""

import numpy as np
import pytest

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    _get_discharge_curve,
    _get_model_matrix,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from tests.conftest import (
    REFERENCE_AREA_LAND_HA,
    REFERENCE_AREA_OPEN_WATER_HA,
    REFERENCE_DH_M,
    REFERENCE_POLDER,
    REFERENCE_STORM,
    load_ton_sweep,
)

TOLERANCE_M = 1e-12
PUMP_M3_PER_SEC = 5.0
DAYS_TO_RETAIN = 2

# In het rekenblad zijn de sweepkolommen met de hand ingevulde waarden, geen formules: Ton
# stelde de schatting bij en typte de uitkomst over. Bij 10 m3/s staat er exact 0,5 terwijl
# alle buren 16 significante cijfers hebben (9,0 -> 0,6883473714285732). Dat is een
# overtypfout in de referentie, geen modelverschil; onze waarde is 0,5032045142857140.
# test_afvoeren_sweep_has_one_transcription_defect bewaakt deze uitzondering.
AFVOEREN_TRANSCRIPTION_DEFECT_M3_PER_SEC = 10.0


def _reference_storm():
    return StoreInputGivenH(
        **REFERENCE_STORM, **REFERENCE_POLDER, delta_h_available=1.0
    )


def _reference_state():
    """De polder uit het rekenblad. Het afvoerend oppervlak staat vast op 3860 ha (V1)."""
    return PolderState.from_water_system_input(
        _reference_storm(), land_area_follows_open_water=False
    )


def _reference_drainage_hourly():
    """De afvoerreeks van de referentiebui, in l/s/ha, uit de eigen routines."""
    model = _reference_storm()
    rain_per_day, _ = get_rainfall(model)
    days = int(model.length_event_hrs / 24)
    flow_per_day, _ = _get_model_matrix(
        model,
        rain_per_day,
        _get_discharge_curve(model.days_to_discharge),
        days + model.days_to_discharge - 1,
    )
    return np.repeat(flow_per_day / 24 * 10 / 3.6, 24)


def test_rainfall_module_reproduces_ton_drainage_series(ton_drainage):
    """De neerslag- en afvoerroutines reconstrueren Ton's reeks exact."""
    ours = _reference_drainage_hourly()
    theirs = np.asarray(ton_drainage)

    # Ton's reeks loopt 288 uur door met nullen in de staart; onze reeks stopt eerder.
    length = max(len(ours), len(theirs))
    padded_ours = np.zeros(length)
    padded_theirs = np.zeros(length)
    padded_ours[: len(ours)] = ours
    padded_theirs[: len(theirs)] = theirs

    # in mm over de hele reeks: l/s/ha maal 0,36 geeft mm per uur
    l1_error_mm = np.abs(padded_ours - padded_theirs).sum() * 0.36
    assert l1_error_mm < 1e-9, f"L1-fout {l1_error_mm:.6f} mm"


def test_reference_water_level_without_measure():
    """Zonder maatregel komt de waterstandstijging op de rekenbladwaarde uit."""
    dh = simulate(_reference_state(), _reference_storm()).dh_max_m
    assert abs(dh - REFERENCE_DH_M) < TOLERANCE_M


def test_sweep_bergen():
    """Absolute fractie open water -> waterstandstijging, tegen het rekenblad."""
    state, storm = _reference_state(), _reference_storm()
    for fraction, expected in load_ton_sweep("bergen"):
        target_open_water_ha = fraction * REFERENCE_POLDER["area_ha"]
        action = BergenAction(
            delta_open_water_ha=target_open_water_ha - REFERENCE_AREA_OPEN_WATER_HA
        )
        dh = simulate(action.apply(state), storm).dh_max_m
        assert abs(dh - expected) < TOLERANCE_M, (
            f"{fraction * 100:.2f} % open water: {dh} != {expected}"
        )


def test_sweep_afvoeren():
    """Absolute gemaalcapaciteit -> waterstandstijging, tegen het rekenblad."""
    state, storm = _reference_state(), _reference_storm()
    for capacity_m3_per_sec, expected in load_ton_sweep("afvoeren"):
        if capacity_m3_per_sec == AFVOEREN_TRANSCRIPTION_DEFECT_M3_PER_SEC:
            continue
        action = AfvoerenAction(
            delta_pump_capacity_m3_per_sec=capacity_m3_per_sec - PUMP_M3_PER_SEC
        )
        dh = simulate(action.apply(state), storm).dh_max_m
        assert abs(dh - expected) < TOLERANCE_M, (
            f"{capacity_m3_per_sec} m3/s: {dh} != {expected}"
        )


def test_sweep_vasthouden():
    """Percentage vastgehouden landoppervlak -> waterstandstijging, tegen het rekenblad."""
    state, storm = _reference_state(), _reference_storm()
    for retention_pct, expected in load_ton_sweep("vasthouden"):
        action = VasthoudenAction(
            delta_retention_ha=retention_pct / 100 * REFERENCE_AREA_LAND_HA
        )
        dh = simulate(action.apply(state), storm).dh_max_m
        assert abs(dh - expected) < TOLERANCE_M, (
            f"{retention_pct} % vasthouden: {dh} != {expected}"
        )


def test_bergen_anchor_from_the_plan():
    """Doel 1,0 m vraagt 98 ha extra open water, niet 2809 ha (D3)."""
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import solve

    result = solve(_reference_state(), _reference_storm(), BergenAction(), 1.0)
    assert result.magnitude == pytest.approx(98.3, abs=0.5)
    assert result.state_after.pct_open_water == pytest.approx(5.96, abs=0.01)


def test_vasthouden_anchor_from_the_plan():
    """30 % vasthouden is 1158 ha, gerekend over 3860 ha land en niet over 4000 ha (D4)."""
    state = _reference_state()
    action = VasthoudenAction(delta_retention_ha=0.30 * REFERENCE_AREA_LAND_HA)
    assert action.delta_retention_ha == pytest.approx(1158.0)
    assert action.apply(state).retention_fraction == pytest.approx(0.30)


def test_afvoeren_sweep_has_one_transcription_defect():
    """Bewaakt de uitzondering in test_sweep_afvoeren.

    Wordt het rekenblad ooit gecorrigeerd, dan valt deze test om en moet de uitzondering
    uit test_sweep_afvoeren verdwijnen.
    """
    values = dict(load_ton_sweep("afvoeren"))
    assert values[AFVOEREN_TRANSCRIPTION_DEFECT_M3_PER_SEC] == 0.5

    # de buren hebben wel volle precisie; dat is het bewijs dat 0,5 is overgetypt
    assert values[9.0] != round(values[9.0], 4)
    assert values[10.5] != round(values[10.5], 4)


def test_vasthouden_sweep_is_not_monotonic():
    """Vastleggen dat de niet-monotonie in de referentiedata zit, niet in onze code."""
    values = [dh for _, dh in load_ton_sweep("vasthouden")]
    assert np.argmin(values) not in (0, len(values) - 1)
    assert values[-1] > min(values)

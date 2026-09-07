"""Gedeelde fixtures voor de rules-of-thumb tests.

De referentiecasus komt uit `scripts/scripts_Ton/TttE_v03.xlsx`; zie `tests/data/`
voor de herkomst van de parameters.
"""

import csv
from pathlib import Path

import pytest

from talk_with_the_engineer.interface.mcp.connections import get_runtime_ctx
from tests.utils_tests import setup_dot_env

DATA = Path(__file__).parent / "data"

# De bui waarvan Ton's afvoerreeks de uitkomst is. Let op: dit zijn NIET de defaults van
# RainfallInput (die staan op p1c en days_to_discharge=3).
REFERENCE_STORM = {
    "return_period": 1000,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
    "rainfall_regime": "R",
}

REFERENCE_POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}

# Waterstandstijging zonder maatregel, uit het rekenblad.
REFERENCE_DH_M = 1.7023330857142858

# Afgeleide grootheden van de referentiepolder, in het rekenblad L1/L2/L3.
REFERENCE_AREA_OPEN_WATER_HA = 140.0
REFERENCE_AREA_LAND_HA = 3860.0


@pytest.fixture
def test_context():
    setup_dot_env()
    return get_runtime_ctx()


@pytest.fixture
def reference_case():
    """De referentiecasus als losse kwargs, klaar om in een invoermodel te gaan."""
    return {**REFERENCE_STORM, **REFERENCE_POLDER}


def load_ton_sweep(measure):
    """Lees een sweeptabel uit tests/data als lijst van (maatvoering, dh_max_m)."""
    path = DATA / f"ton_sweep_{measure}.csv"
    with path.open() as handle:
        rows = list(csv.reader(handle))
    return [(float(x), float(dh)) for x, dh in rows[1:]]


def load_ton_drainage():
    """Lees Ton's basis-afvoerreeks in l/s/ha."""
    path = DATA / "ton_drainage_hourly.csv"
    with path.open() as handle:
        rows = list(csv.reader(handle))
    return [float(value) for _, value in rows[1:]]


@pytest.fixture
def ton_sweep():
    return load_ton_sweep


@pytest.fixture
def ton_drainage():
    return load_ton_drainage()

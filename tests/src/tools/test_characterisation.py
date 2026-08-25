"""Vangnet (WP0): legt het gedrag van de zes tools vast als snapshot.

Doel is niet dat deze waarden juist zijn — een deel is aantoonbaar fout, zie
PLAN_TOOLS_REFACTOR.md §4 — maar dat elke gedragsverandering zichtbaar en bedoeld is.

Baseline opnieuw vastleggen na een bedoelde wijziging:

    UPDATE_CHARACTERISATION=1 pixi run pytest tests/src/tools/test_characterisation.py

en dan de diff in git nalopen voordat je hem meeneemt.
"""

import json
import os
from pathlib import Path

import pytest

from talk_with_the_engineer.models import (
    DischargeInputGivenDischarge,
    DischargeInputGivenH,
    RetentionInputGivenArea,
    RetentionInputGivenH,
    StoreInputGivenArea,
    StoreInputGivenH,
)
from talk_with_the_engineer.tools import (
    calculate_discharge_given_discharge,
    calculate_discharge_given_h,
    calculate_retention_given_area,
    calculate_retention_given_h,
    calculate_store_given_area,
    calculate_store_given_h,
)

BASELINE = (
    Path(__file__).parent.parent.parent / "data" / "characterisation_baseline.json"
)

POLDER = {
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}

# Attributen op de uitvoer, niet sleutels in `.data`. De centimeter-varianten stonden
# eerder in `data` en waren exact deze getallen maal honderd; die dubbeling is weg, en
# `dh_reduction` en `feasible_dh_max` zijn afleidbaar uit de andere twee.
DH_ATTRIBUTES = [
    "dh_reference_m",
    "dh_with_measure_m",
    "feasible_dh_min_m",
]

# (naam, tool, invoermodel, extra kwargs, uit te lezen sleutels uit .data)
CASES = [
    (
        "store_given_h/T10",
        calculate_store_given_h,
        StoreInputGivenH,
        {"return_period": 10, "delta_h_available": 0.06},
        [
            "delta_open_water_ha",
            "new_area_percentage",
            "rain_volume_gross_mm",
        ],
    ),
    (
        "store_given_h/T100",
        calculate_store_given_h,
        StoreInputGivenH,
        {"return_period": 100, "delta_h_available": 0.4},
        [
            "delta_open_water_ha",
            "new_area_percentage",
            "rain_volume_gross_mm",
        ],
    ),
    (
        "store_given_area/1000ha",
        calculate_store_given_area,
        StoreInputGivenArea,
        {"return_period": 100, "area_available_ha": 1000},
        [
            "delta_open_water_ha",
            "new_area_percentage",
            "rain_volume_gross_mm",
        ],
    ),
    (
        "retention_given_h/T100",
        calculate_retention_given_h,
        RetentionInputGivenH,
        {"return_period": 100, "delta_h_available": 0.5},
        [
            "area_polder_delayed_ha",
            "area_percentage_delayed",
            "rain_volume_gross_mm",
        ],
    ),
    (
        "retention_given_area/1158ha",
        calculate_retention_given_area,
        RetentionInputGivenArea,
        {"return_period": 10, "delta_area_ha": 1158},
        [
            "area_polder_delayed_ha",
            "area_percentage_delayed",
            "rain_volume_gross_mm",
        ],
    ),
    (
        "discharge_given_h/T10",
        calculate_discharge_given_h,
        DischargeInputGivenH,
        {"return_period": 10, "delta_h_available": 0.05},
        [
            "extra_discharge_capacity_m3_per_min_required",
            "total_discharge_capacity_m3_per_min",
            "rain_volume_gross_mm",
        ],
    ),
    (
        "discharge_given_discharge/174",
        calculate_discharge_given_discharge,
        DischargeInputGivenDischarge,
        {"return_period": 10, "delta_discharge_capacity_m3_per_min": 174},
        [
            "extra_discharge_capacity_m3_per_min_required",
            "rain_volume_gross_mm",
        ],
    ),
]


async def _run_all(ctx):
    snapshot = {}
    for name, tool, model, kwargs, keys in CASES:
        result = await tool(ctx, model(**POLDER, **kwargs))
        snapshot[name] = {key: round(float(result.data[key]), 6) for key in keys}
        snapshot[name].update(
            {a: round(float(getattr(result, a)), 6) for a in DH_ATTRIBUTES}
        )
        snapshot[name]["status"] = result.status.value
        # de maatvoering NA de maatregel, in de eenheid van die maatregel; kwam eerder uit
        # `state_after.pct_open_water`, wat alleen bij bergen iets zei
        snapshot[name]["measure_after"] = round(float(result.measure.after), 6)
    return snapshot


@pytest.mark.asyncio
async def test_characterisation(test_context):
    snapshot = await _run_all(test_context)

    if os.environ.get("UPDATE_CHARACTERISATION") or not BASELINE.exists():
        BASELINE.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"baseline weggeschreven naar {BASELINE.name}; diff nalopen in git")

    expected = json.loads(BASELINE.read_text())
    assert snapshot == expected, (
        "gedrag van de tools is veranderd. Als dat bedoeld is: "
        "UPDATE_CHARACTERISATION=1 pytest ... en de diff nalopen."
    )

"""Validators moeten ongeldige invoer ook echt afwijzen (WP1)."""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    _get_discharge_curve,
)

POLDER = {"area_ha": 4000, "discharge_capacity_m3_per_sec": 5}


@pytest.mark.parametrize("percentage", [-50, -0.1, 0, 100.1, 250])
def test_invalid_percentage_open_water_is_rejected(percentage):
    """D9: -50 % werd geaccepteerd en gaf -2000 ha open water."""
    with pytest.raises(ModelRetry):
        StoreInputGivenH(
            return_period=10,
            percentage_open_water=percentage,
            delta_h_available=1.0,
            **POLDER,
        )


@pytest.mark.parametrize("percentage", [0.1, 3.5, 100])
def test_valid_percentage_open_water_is_accepted(percentage):
    model = StoreInputGivenH(
        return_period=10,
        percentage_open_water=percentage,
        delta_h_available=1.0,
        **POLDER,
    )
    assert model.percentage_open_water == percentage


@pytest.mark.parametrize("days", [2, 3, 4])
def test_documented_discharge_curves_sum_to_one(days):
    curve = _get_discharge_curve(days)
    assert len(curve) == days
    assert abs(sum(curve) - 1.0) < 1e-12


@pytest.mark.parametrize("days", [0, 1, 5, 10, 11])
def test_undocumented_discharge_curves_are_rejected(days):
    """D12: de validator stond 2-4 toe, de implementatie 2-10."""
    with pytest.raises(ValueError):
        _get_discharge_curve(days)


@pytest.mark.parametrize("days", [1, 5, 10])
def test_days_to_discharge_outside_table_39_is_rejected_by_the_model(days):
    with pytest.raises(ModelRetry):
        StoreInputGivenH(
            return_period=10, days_to_discharge=days, delta_h_available=1.0, **POLDER
        )

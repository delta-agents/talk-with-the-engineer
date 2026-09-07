"""Maatregel afvoeren."""

import re

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.interface.schemas.discharge import (
    DischargeInputGivenDischarge,
    DischargeInputGivenH,
    DischargeOutput,
)
from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.interface.tools.discharge import (
    calculate_discharge_given_discharge,
    calculate_discharge_given_h,
)

POLDER_SUMMER = {
    "area_ha": 4000,
    "time_of_year": "summer",
    "return_period": 10,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}


@pytest.mark.asyncio
async def test_discharge_given_h_returns_a_usable_answer(test_context):
    result: DischargeOutput = await calculate_discharge_given_h(
        test_context,
        DischargeInputGivenH(
            return_period=200,
            time_of_year="summer",
            length_event_hrs=96,
            rainfall_regime="L",
            area_ha=4000,
            percentage_open_water=3.5,
            discharge_capacity_m3_per_sec=5,
            delta_h_available=0.2,
        ),
    )
    assert result.status is SolveStatus.EXACT
    assert result.data["extra_discharge_capacity_m3_per_min_required"] > 0
    assert result.measure.after > result.measure.before


@pytest.mark.asyncio
async def test_discharge_given_discharge_returns_a_usable_answer(test_context):
    result: DischargeOutput = await calculate_discharge_given_discharge(
        test_context,
        DischargeInputGivenDischarge(
            delta_discharge_capacity_m3_per_min=174, **POLDER_SUMMER
        ),
    )
    assert result.description
    assert result.dh_reference_m - result.dh_with_measure_m > 0
    assert result.measure.after == pytest.approx(5 + 174 / 60)


@pytest.mark.asyncio
async def test_discharge_roundtrip_closes_inside_the_feasible_range(test_context):
    target_m = 0.05  # bereik is hier [0, 0.11] m

    inverse: DischargeOutput = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(delta_h_available=target_m, **POLDER_SUMMER)
    )
    assert inverse.status is SolveStatus.EXACT

    forward: DischargeOutput = await calculate_discharge_given_discharge(
        test_context,
        DischargeInputGivenDischarge(
            delta_discharge_capacity_m3_per_sec=inverse.data[
                "extra_discharge_capacity_m3_per_sec_required"
            ],
            **POLDER_SUMMER,
        ),
    )
    assert forward.dh_with_measure_m == pytest.approx(target_m, abs=1e-3)


@pytest.mark.asyncio
async def test_discharge_target_above_reference_needs_no_measure(test_context):
    result: DischargeOutput = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(delta_h_available=0.9, **POLDER_SUMMER)
    )
    assert result.status is SolveStatus.NO_MEASURE_NEEDED
    assert "niet nodig" in result.description


@pytest.mark.asyncio
async def test_discharge_description_reports_the_increase_not_the_total(test_context):
    """D10: de Nederlandse tekst zette de nieuwe totaalcapaciteit op de plek van de toename.

    Toetst de GROOTHEID en niet de opmaak. Een assertie op `f"{increase:.2f} m3/s"` zou
    naast D10 ook twee decimalen vastleggen, terwijl de tekst zijn precisie uit de gemeten
    spreiding haalt en hier dus "0.8" zegt en niet "0.78". Die afronding is het doel; de
    test hoort er niet aan vast te zitten.
    """
    result: DischargeOutput = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(delta_h_available=0.05, **POLDER_SUMMER)
    )
    increase = result.data["extra_discharge_capacity_m3_per_sec_required"]
    total = result.data["total_discharge_capacity_m3_per_min"] / 60
    assert total > increase  # anders test dit niets

    reported = re.search(r"([\d.]+) m3/s extra gemaalcapaciteit", result.description)
    assert reported, result.description
    value = float(reported.group(1))
    assert abs(value - increase) < abs(value - total)


@pytest.mark.asyncio
async def test_discharge_rejects_negative_capacity(test_context):
    with pytest.raises(ModelRetry):
        await calculate_discharge_given_discharge(
            test_context,
            DischargeInputGivenDischarge(
                delta_discharge_capacity_m3_per_sec=-1, **POLDER_SUMMER
            ),
        )

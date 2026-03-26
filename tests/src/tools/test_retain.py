import numpy as np
import pytest

from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenH,
    RetentionInputGivenArea,
    RetentionOutput,
)
from talk_with_the_engineer.routers import get_runtime_ctx

from talk_with_the_engineer.tools.toolset_rules_of_thumb.retain import (
    calculate_retention_given_h,
    calculate_retention_given_area,
)
from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()



@pytest.mark.asyncio
async def test_hold_ton(test_context):
    input = RetentionInputGivenH(
        return_period=200,
        time_of_year="summer",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=4000,
        discharge_capacity_m3_per_sec=5,
        delta_h_available=1.5,
        percentage_open_water=3.5,
    )
    res: RetentionOutput = await calculate_retention_given_h(test_context, input)
    res.data

@pytest.mark.asyncio
async def test_hold(test_context):
    input = RetentionInputGivenH(
        return_period=200,
        time_of_year="summer",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=100,
        discharge_capacity_m3_per_min=5,
        delta_h_available=0.45,
    )
    res: RetentionOutput = await calculate_retention_given_h(test_context, input)
    res.data


@pytest.mark.asyncio
async def test_hold_edge_case(test_context):
    retention_input = RetentionInputGivenH(
        area_ha=500,
        time_of_year="summer",
        return_period=10,
        delta_h_available=0.3,
        percentage_open_water=5,
        discharge_capacity_mm_d=2.7,  # of 2.6
    )

    res: RetentionOutput = await calculate_retention_given_h(
        test_context, retention_input
    )
    res.data


@pytest.mark.asyncio
async def test_calculate_retain_input_h_should_be_output_area(test_context):
    delta_h_available = 0.15  # meters
    retain_input_given_h = RetentionInputGivenH(
        # based on water system and rain event
        area_ha=500,
        time_of_year="summer",
        return_period=10,
        percentage_open_water=5,
        discharge_capacity_mm_d=5,
        # based on measure 'store'
        delta_h_available=delta_h_available,
    )

    retain_output_given_h: RetentionOutput = await calculate_retention_given_h(
        ctx=test_context, input=retain_input_given_h
    )
    retain_input_given_area = RetentionInputGivenArea(
        # based on water system and rain event
        area_ha=500,
        time_of_year="summer",
        return_period=10,
        percentage_open_water=5,
        discharge_capacity_mm_d=5,
        # based on measure 'store'
        delta_area_ha=retain_output_given_h.data["area_polder_delayed_ha"],
    )

    retain_output_given_area: RetentionOutput = await calculate_retention_given_area(
        ctx=test_context, input=retain_input_given_area
    )
    delta = (
        retain_output_given_area.data["change_in_delta_h_cm"] - delta_h_available * 100
    )
    assert np.isclose(delta, 0)  # should give a valid results

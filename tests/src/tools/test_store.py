import pytest

from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.routers import get_runtime_ctx

from talk_with_the_engineer.tools.toolset_rules_of_thumb.store import (
    calculate_store_given_area,
    calculate_store_given_h,
)
from tests.utils_tests import setup_dot_env
import numpy as np


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()


@pytest.mark.asyncio
async def test_calculate_store_given_h_ton(test_context):
    input = StoreInputGivenH(
        return_period=200,
        time_of_year="summer",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=4000,
        discharge_capacity_m3_per_sec=5,
        delta_h_available=0.1,
        percentage_open_water=3.5,
    )
    res: StoreOutput = await calculate_store_given_h(test_context, input)
    assert res.data["area_ha_required_open_water"] >= 0  # should give a valid results


@pytest.mark.asyncio
async def test_calculate_store_given_h(test_context):
    input = StoreInputGivenH(
        return_period=200,
        time_of_year="winter",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=100,
        discharge_capacity_m3_per_min=5,
        delta_h_available=0.1,
    )
    res: StoreOutput = await calculate_store_given_h(test_context, input)
    assert res.data["area_ha_required_open_water"] >= 0  # should give a valid results


@pytest.mark.asyncio
async def test_calculate_store_given_area(test_context):
    input = StoreInputGivenArea(
        return_period=200,
        time_of_year="winter",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=100,
        discharge_capacity_m3_per_min=5,
        area_available_m2=100,
    )
    res: StoreOutput = await calculate_store_given_area(test_context, input)
    assert res.description  # add tests later


@pytest.mark.asyncio
async def test_calculate_store_input_should_be_output(test_context):
    delta_h_available = 0.15  # meters
    store_input_given_h = StoreInputGivenH(
        # based on water system and rain event
        area_ha=500,
        time_of_year="summer",
        return_period=10,
        percentage_open_water=5,
        discharge_capacity_mm_d=5,
        # based on measure 'store'
        delta_h_available=delta_h_available,
    )

    store_output_given_h: StoreOutput = await calculate_store_given_h(
        ctx=test_context, input=store_input_given_h
    )
    store_input_given_area = StoreInputGivenArea(
        # based on water system and rain event
        area_ha=500,
        time_of_year="summer",
        return_period=10,
        percentage_open_water=5,
        discharge_capacity_mm_d=5,
        # based on measure 'store'
        area_available_ha=store_output_given_h.data["area_ha_required_open_water"],
    )

    store_output_given_area: StoreOutput = await calculate_store_given_area(
        ctx=test_context, input=store_input_given_area
    )
    delta = (
        store_output_given_area.data["reduction_in_delta_h_cm"]
        - delta_h_available * 100
    )
    assert np.isclose(delta, 0)  # should give a valid results

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


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()


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

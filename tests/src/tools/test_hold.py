import pytest

from talk_with_the_engineer.models.modelset_rules_of_thumb.hold import (
    HoldInput,
    HoldOutput,
)
from talk_with_the_engineer.routers import get_runtime_ctx

from talk_with_the_engineer.tools.toolset_rules_of_thumb.hold import hold_tool
from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()


@pytest.mark.asyncio
async def test_hold(test_context):
    input = HoldInput(
        return_period=200,
        time_of_year="summer",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=100,
        discharge_capacity_m3_per_min=5,
        delta_h_available=0.45,
    )
    res: HoldOutput = await hold_tool(test_context, input)
    res.data

@pytest.mark.asyncio
async def test_hold_edge_case(test_context):
    hold_input = HoldInput(
        area_ha=500, 
        time_of_year='summer', 
        return_period=10, 
        delta_h_available=0.3,
        percentage_open_water=5,
        discharge_capacity_mm_d=2.7 # of 2.6
    )

    res: HoldOutput = await hold_tool(test_context, hold_input)
    res.data
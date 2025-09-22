import pytest

from talk_with_the_engineer.models.modelset_rules_of_thumb.discharge import (
    DischargeInput,
    DischargeOutput,
)

from talk_with_the_engineer.routers import get_runtime_ctx

from talk_with_the_engineer.tools.toolset_rules_of_thumb.discharge import discharge_tool
from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()


@pytest.mark.asyncio
async def test_store(test_context):
    input = DischargeInput(
        return_period=200,
        time_of_year="summer",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=100,
        discharge_capacity_m3_per_min=5,
        delta_h_available=0.1,
    )

    res: DischargeOutput = await discharge_tool(test_context, input)
    assert (
        res.data["extra_discharge_capacity_m3_per_min_required"] >= 0
    )  # should give a valid results


@pytest.mark.asyncio
async def test_discharge_edge_case(test_context):
    discharge_input = DischargeInput(
        area_ha=500,
        time_of_year="summer",
        return_period=10,
        delta_h_available=0.3,
        percentage_open_water=5,
        discharge_capacity_mm_d=2.7,  # of 2.6
    )

    res: DischargeOutput = await discharge_tool(test_context, discharge_input)
    res.data

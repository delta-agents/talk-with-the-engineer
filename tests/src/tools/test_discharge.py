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

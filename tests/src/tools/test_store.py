import pytest

from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInput,
    StoreOutput,
)
from talk_with_the_engineer.routers import get_runtime_ctx

from talk_with_the_engineer.tools.toolset_rules_of_thumb.store import store_tool
from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()


@pytest.mark.asyncio
async def test_store(test_context):
    input = StoreInput(
        return_period=200,
        time_of_year="winter",
        length_event_hrs=96,
        rainfall_regime="L",
        area_ha=100,
        disposal_capacity_m3_per_min=5,
    )
    res: StoreOutput = await store_tool(test_context, input)
    assert (
        max(res.data["area_ha_required_open_water"]) >= 0
    )  # should give a valid results

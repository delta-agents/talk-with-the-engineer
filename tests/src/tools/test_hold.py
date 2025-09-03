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
        time_of_year="winter",
        length_event_hrs=96,
        rainfall_regime="L",
    )
    res: HoldOutput = await hold_tool(test_context, input)
    res.data

import pytest

from AI_agents_template.models.modelset_1.example1 import Example1Input, Example1Output
from AI_agents_template.routers.setup_connections import get_runtime_ctx
from AI_agents_template.tools.toolset_1.example1 import example1_tool
from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context with FEWS webservice URL"""
    setup_dot_env()
    return get_runtime_ctx()


@pytest.mark.asyncio
async def test_example1(test_context):
    """Test handling of invalid time ranges"""
    # Test end time before start time
    input = Example1Input(index=1)

    res: Example1Output = await example1_tool(test_context, input)

    res.data

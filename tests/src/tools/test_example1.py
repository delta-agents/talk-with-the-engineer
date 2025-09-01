import pytest

# from talk_with_the_engineer.models.modelset_1.example1 import Example1Input, Example1Output
from talk_with_the_engineer.routers import get_runtime_ctx

# from talk_with_the_engineer.tools.toolset_1.example1 import example1_tool
from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context with FEWS webservice URL"""
    setup_dot_env()
    return get_runtime_ctx()


# @pytest.mark.asyncio
# async def test_example1(test_context):
#     """Test handling of invalid time ranges"""
#     # Test end time before start time
#     input = Example1Input(index=1)

#     res: Example1Output = await example1_tool(test_context, input)

#     res.data

import pytest

from talk_with_the_engineer.routers import get_runtime_ctx

from tests.utils_tests import setup_dot_env


@pytest.fixture
def test_context():
    """Create a test context"""
    setup_dot_env()
    return get_runtime_ctx()


# @pytest.mark.asyncio
# async def test_hold(test_context):  
# ....

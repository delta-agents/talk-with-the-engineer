from fastapi import APIRouter
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from talk_with_the_engineer.utils.docstring_generator import auto_docstring
from talk_with_the_engineer.models import (
    Example2Input,
    Example2Output,
)
from talk_with_the_engineer.tools import example2_tool

# Import tool functions and their models
from talk_with_the_engineer.routers.setup_connections import get_runtime_ctx, setup_env

# see talk-with-fews for user specific configuration of tools
tokens = setup_env()
verifier = StaticTokenVerifier(tokens=tokens, required_scopes=["read:data"])

router = APIRouter()
mcp = FastMCP(name="Prerequisites", auth=verifier)


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.Prerequisites/example2")
@auto_docstring("Example2")
async def example2_mcp(
    input: Example2Input,
) -> Example2Output:
    ctx = get_runtime_ctx()
    return await example2_tool(ctx, input)

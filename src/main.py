from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.talk_with_the_engineer.routers.tools_router_RulesOfThumb import (
    router as router_vuistregels,
)
from src.talk_with_the_engineer.routers.tools_router_RulesOfThumb import (
    mcp as mcp_vuistregels,
)

# unused for now
from src.talk_with_the_engineer.routers.tools_router_Prerequisites import (
    router as router_randvoorwaarden,
)
from src.talk_with_the_engineer.routers.tools_router_Prerequisites import (
    mcp as mcp_randvoorwaarden,
)

from typing import AsyncIterator
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv(dotenv_path="env/.env")

## Talk With Config

# Mount MCP at /mcp
mcp_app_vuistregels = mcp_vuistregels.http_app(
    path="/", transport="streamable-http", stateless_http=True
)

mcp_app_randvoorwaarden = mcp_randvoorwaarden.http_app(
    path="/", transport="streamable-http", stateless_http=True
)


@asynccontextmanager
async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run both lifespans in startup
    async with (
        mcp_app_vuistregels.lifespan(mcp_app_vuistregels),
        mcp_app_randvoorwaarden.lifespan(mcp_app_randvoorwaarden),
    ):
        yield


app = FastAPI(
    title="Talk with the engineer Tools API",
    version="0.1.0",
    description="API and MCP server exposing selected tools",
    lifespan=combined_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the tools router
app.include_router(router_vuistregels)

# Mount MCP at /mcp
app.mount("/mcp/vuistregels", mcp_app_vuistregels)

# Include the tools router
app.include_router(router_randvoorwaarden)

# Mount MCP at /mcp
app.mount("/mcp/randvoorwaarden", mcp_app_randvoorwaarden)

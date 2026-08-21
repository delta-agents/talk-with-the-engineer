from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.talk_with_the_engineer.routers.tools_router_RulesOfThumb import (
    mcp as mcp_vuistregels,
)
from src.talk_with_the_engineer.routers.tools_router_RulesOfThumb import (
    router as router_vuistregels,
)

load_dotenv(dotenv_path="env/.env")

# Mount MCP at /mcp
mcp_app_vuistregels = mcp_vuistregels.http_app(
    path="/", transport="streamable-http", stateless_http=True
)


@asynccontextmanager
async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with mcp_app_vuistregels.lifespan(mcp_app_vuistregels):
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

app.include_router(router_vuistregels)
app.mount("/mcp/vuistregels", mcp_app_vuistregels)

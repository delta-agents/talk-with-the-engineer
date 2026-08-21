from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp.exceptions import ToolError
from pydantic_ai import ModelRetry

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


@app.exception_handler(ModelRetry)
@app.exception_handler(ToolError)
async def model_retry_handler(request: Request, exc: Exception) -> JSONResponse:
    """Geef een ModelRetry terug als 422 in plaats van hem te laten crashen.

    De invoervalidators raisen `ModelRetry` uit pydantic-ai. Dat is geen pydantic
    `ValidationError`, dus FastAPI zet het niet om in een 422 maar laat het als
    onbehandelde exceptie naar buiten komen: over HTTP crashte ongeldige invoer met een
    500 in plaats van een nette foutmelding.

    Juist bij `ModelRetry` is dat kwalijk, want de hele bedoeling van die klasse is dat de
    aanroeper het bericht ziet en het opnieuw probeert - een LLM die de tool aanroept moet
    kunnen lezen welke waarden wel geldig zijn. Daarom hier op 422 gemapt met het bericht
    in de body, in dezelfde vorm als FastAPI's eigen validatiefouten.
    """
    return JSONResponse(
        status_code=422,
        content={"detail": [{"type": "model_retry", "msg": str(exc)}]},
    )


app.include_router(router_vuistregels)
app.mount("/mcp/vuistregels", mcp_app_vuistregels)

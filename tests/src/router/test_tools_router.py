"""De FastAPI-app end-to-end: de enige test die over HTTP gaat.

Testte eerder het Prerequisites-voorbeeld; dat is verwijderd, dus nu een echte
vuistregeltool. Daarmee dekt deze test ook de serialisatie van de nieuwe uitvoervelden -
`measure` en de status - die door de MCP- en HTTP-laag heen moeten.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client

from src.main import app
from src.talk_with_the_engineer.interface.mcp.router import mcp
from tests.utils_tests import setup_dot_env

POLDER_AND_STORM = {
    "return_period": 100,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "area_ha": 4000,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}


def test_store_given_area_over_http():
    setup_dot_env()
    client = TestClient(app)
    response = client.post(
        "/tools.RulesOfThumb/store_given_area",
        json={**POLDER_AND_STORM, "area_available_ha": 200},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert "data" in body
    assert body["description"]
    assert body["status"] == "exact"

    # de verandering komt er als voor/na/verschil uit, niet als twee volle toestanden
    assert body["measure"]["after"] > body["measure"]["before"]
    assert body["measure"]["delta"] > 0
    assert body["dh_reference_m"] > body["dh_with_measure_m"]
    assert body["cost"] > 0


def test_all_routes_are_mounted():
    """Via het OpenAPI-schema in plaats van via `app.routes`.

    FastAPI 0.141 laat opgenomen routers als `_IncludedRouter` in `app.routes` staan in
    plaats van ze uit te vlakken, dus dat is een intern detail om niet op te leunen. Het
    schema is publieke API en test bovendien wat er daadwerkelijk wordt aangeboden.

    De aantalcheck onderaan is wat een handmatige lijst niet kan: elke tool wordt zowel bij
    MCP als bij FastAPI geregistreerd, en een tool die maar een van de twee krijgt zou hier
    anders stil doorglippen.
    """
    paths = set(app.openapi()["paths"])
    for name in (
        "read_me",
        "retention_given_h",
        "retention_given_area",
        "store_given_h",
        "store_given_area",
        "discharge_given_h",
        "discharge_given_discharge",
        "supply_given_h",
        "supply_given_supply",
        "cascade_given_excess",
        "allocation_given_shortage",
        "find_package_given_protection",
    ):
        assert f"/tools.RulesOfThumb/{name}" in paths
    assert not any("Prerequisites" in path for path in paths)

    tool_paths = {path for path in paths if path.startswith("/tools.RulesOfThumb/")}
    registered = asyncio.run(_mcp_tool_names())
    assert len(tool_paths) == len(registered), (
        f"{len(registered)} tools bij MCP en {len(tool_paths)} REST-routes; elke tool hoort "
        "beide te hebben"
    )


async def _mcp_tool_names() -> set[str]:
    async with Client(mcp) as client:
        return {tool.name for tool in await client.list_tools()}


@pytest.mark.parametrize(
    "override, expected_in_message",
    [
        ({"return_period": 7}, "Input should be 0.5"),
        ({"length_event_hrs": 100.0}, "Input should be 48.0, 96.0 or 192.0"),
        ({"percentage_open_water": -50}, "Input should be greater than 0"),
        ({"rainfall_regime": "X"}, "Input should be 'LL', 'L', 'R' or 'H'"),
    ],
)
def test_invalid_input_gives_422_with_the_reason(override, expected_in_message):
    """Ongeldige invoer geeft een 422 met veldpad en toegestane waarden.

    Sinds de beperkingen als `Literal` in het type staan is dit FastAPI's eigen 422: het
    veldpad zit erin en het bericht noemt wat wél mag. Voorheen raisten de validators
    `ModelRetry` uit pydantic-ai - geen pydantic `ValidationError` - waardoor FastAPI het
    niet omzette en ongeldige invoer over HTTP met een 500 crashte.
    """
    setup_dot_env()
    client = TestClient(app)
    response = client.post(
        "/tools.RulesOfThumb/store_given_area",
        json={**POLDER_AND_STORM, "area_available_ha": 200, **override},
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    # FastAPI's eigen 422: het veldpad zit erin, dus de aanroeper weet welk veld fout is
    assert detail[0]["loc"][-1] == next(iter(override))
    assert expected_in_message in detail[0]["msg"]


def test_impossible_measure_gives_422_not_a_crash():
    """Ook een ModelRetry uit de tool zelf hoort als 422 terug te komen.

    8000 ha open water op een polder van 4000 ha wordt door `evaluate` afgewezen. Dat
    liep langs dezelfde route mis als de validators.
    """
    setup_dot_env()
    client = TestClient(app)
    response = client.post(
        "/tools.RulesOfThumb/store_given_area",
        json={**POLDER_AND_STORM, "area_available_ha": 8000},
    )
    assert response.status_code == 422, response.text
    assert "niet mogelijk" in response.json()["detail"][0]["msg"]

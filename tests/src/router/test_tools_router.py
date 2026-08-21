"""De FastAPI-app end-to-end: de enige test die over HTTP gaat.

Testte eerder het Prerequisites-voorbeeld; dat is verwijderd, dus nu een echte
vuistregeltool. Daarmee dekt deze test ook de serialisatie van de nieuwe uitvoervelden -
`state_before`, `state_after` en de status - die door de MCP- en HTTP-laag heen moeten.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
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

    # de toestand komt er als toestand uit, niet alleen als getal
    assert (
        body["state_after"]["pct_open_water"] > body["state_before"]["pct_open_water"]
    )
    assert body["dh_reduction_m"] > 0
    assert body["cost"] > 0


def test_all_six_routes_are_mounted():
    """Via het OpenAPI-schema in plaats van via `app.routes`.

    FastAPI 0.141 laat opgenomen routers als `_IncludedRouter` in `app.routes` staan in
    plaats van ze uit te vlakken, dus dat is een intern detail om niet op te leunen. Het
    schema is publieke API en test bovendien wat er daadwerkelijk wordt aangeboden.
    """
    paths = set(app.openapi()["paths"])
    for name in (
        "retention_given_h",
        "retention_given_area",
        "store_given_h",
        "store_given_area",
        "discharge_given_h",
        "discharge_given_discharge",
    ):
        assert f"/tools.RulesOfThumb/{name}" in paths
    assert not any("Prerequisites" in path for path in paths)


@pytest.mark.parametrize(
    "override, expected_in_message",
    [
        ({"return_period": 7}, "return_period must be one of"),
        ({"length_event_hrs": 100.0}, "length_event_hrs must be one of"),
        (
            {"percentage_open_water": -50},
            "percentage_open_water must be greater than 0",
        ),
        ({"rainfall_regime": "X"}, "rainfall_regime must be one of"),
    ],
)
def test_invalid_input_gives_422_with_the_reason(override, expected_in_message):
    """Ongeldige invoer moet een 422 met uitleg geven, geen crash.

    De validators raisen `ModelRetry` uit pydantic-ai, en dat is geen pydantic
    `ValidationError`. FastAPI zet het dus niet zelf om in een 422; zonder de
    exception handler in `main.py` kwam het als onbehandelde exceptie naar buiten en
    crashte ongeldige invoer over HTTP met een 500.

    Juist bij `ModelRetry` is dat kwalijk: de hele bedoeling is dat de aanroeper het
    bericht ziet en het opnieuw probeert, dus een LLM moet kunnen lezen welke waarden
    wél geldig zijn. Deze test controleert dat het bericht de body bereikt.
    """
    setup_dot_env()
    client = TestClient(app)
    response = client.post(
        "/tools.RulesOfThumb/store_given_area",
        json={**POLDER_AND_STORM, "area_available_ha": 200, **override},
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail[0]["type"] == "model_retry"
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

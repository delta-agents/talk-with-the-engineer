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
    paths = {route.path for route in app.routes}
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Bestaand defect, buiten de scope van deze wijziging: de validators raisen "
        "ModelRetry uit pydantic-ai, en dat is geen pydantic ValidationError. FastAPI "
        "zet het dus niet om in een 422 maar laat het als onbehandelde exceptie naar "
        "buiten komen. Over HTTP crasht ongeldige invoer daarmee in plaats van een "
        "nette foutmelding te geven - en juist bij ModelRetry is dat kwalijk, want de "
        "hele bedoeling is dat de aanroeper het bericht ziet en het opnieuw probeert. "
        "Een exception handler die ModelRetry op 422 mapt lost het op."
    ),
)
def test_invalid_input_is_rejected():
    setup_dot_env()
    client = TestClient(app)
    response = client.post(
        "/tools.RulesOfThumb/store_given_area",
        json={**POLDER_AND_STORM, "area_available_ha": 200, "return_period": 7},
    )
    assert response.status_code >= 400

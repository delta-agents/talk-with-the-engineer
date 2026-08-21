"""Ongeldige invoer moet worden afgewezen, en de reden hoort in het schema te staan.

De toegestane waarden zitten als `Literal` in het type en dus als `enum` in het
JSON-schema. Pydantic valideert ze daarmee zelf; er zijn geen eigen validators meer voor
nodig. Dat maakt de beperking zichtbaar voor een MCP-client in plaats van alleen leesbaar
in een beschrijving.
"""

import pytest
from pydantic import ValidationError

from talk_with_the_engineer.models import StoreInputGivenH
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    DAYS_TO_DISCHARGE,
    LENGTH_EVENT_HRS,
    NAME_RAINFALL_PATTERN,
    RAINFALL_REGIMES,
    RETURN_PERIODS,
    TIME_OF_YEAR,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    _get_discharge_curve,
)

POLDER = {"area_ha": 4000, "discharge_capacity_m3_per_sec": 5}
BASE = {"return_period": 100, "delta_h_available": 1.0, **POLDER}


@pytest.mark.parametrize(
    "field, allowed",
    [
        ("return_period", RETURN_PERIODS),
        ("time_of_year", TIME_OF_YEAR),
        ("length_event_hrs", LENGTH_EVENT_HRS),
        ("rainfall_regime", RAINFALL_REGIMES),
        ("name_rainfall_pattern", NAME_RAINFALL_PATTERN),
        ("days_to_discharge", DAYS_TO_DISCHARGE),
    ],
)
def test_allowed_values_are_in_the_json_schema(field, allowed):
    """De constantenlijst is de enige bron en komt als `enum` in het schema terecht."""
    spec = StoreInputGivenH.model_json_schema()["properties"][field]
    assert spec["enum"] == list(allowed), field


@pytest.mark.parametrize(
    "field, value",
    [
        ("return_period", 7),
        ("time_of_year", "lente"),
        ("length_event_hrs", 100.0),
        ("rainfall_regime", "X"),
        ("name_rainfall_pattern", "p9z"),
        ("days_to_discharge", 10),
        ("language", "de"),
    ],
)
def test_values_outside_the_enum_are_rejected(field, value):
    with pytest.raises(ValidationError) as excinfo:
        StoreInputGivenH(**{**BASE, field: value})
    error = excinfo.value.errors()[0]
    assert error["type"] == "literal_error"
    assert error["loc"] == (field,)
    # het bericht noemt de toegestane waarden
    assert "Input should be" in error["msg"]


def test_every_allowed_return_period_is_usable():
    """Ook 0.5 - dat was onbereikbaar toen het veld nog `int` was."""
    for period in RETURN_PERIODS:
        model = StoreInputGivenH(**{**BASE, "return_period": period})
        assert model.return_period == period


@pytest.mark.parametrize("percentage", [-50, -0.1, 0, 100.1, 250])
def test_invalid_percentage_open_water_is_rejected(percentage):
    """De grenzen staan nu op het veld en dus in het schema, niet in een validator."""
    with pytest.raises(ValidationError):
        StoreInputGivenH(**{**BASE, "percentage_open_water": percentage})


def test_percentage_open_water_bounds_are_in_the_schema():
    spec = StoreInputGivenH.model_json_schema()["properties"]["percentage_open_water"]
    assert spec["exclusiveMinimum"] == 0
    assert spec["maximum"] == 100


@pytest.mark.parametrize("percentage", [0.1, 3.5, 100])
def test_valid_percentage_open_water_is_accepted(percentage):
    model = StoreInputGivenH(**{**BASE, "percentage_open_water": percentage})
    assert model.percentage_open_water == percentage


@pytest.mark.parametrize("days", DAYS_TO_DISCHARGE)
def test_documented_discharge_curves_sum_to_one(days):
    curve = _get_discharge_curve(days)
    assert len(curve) == days
    assert abs(sum(curve) - 1.0) < 1e-12


@pytest.mark.parametrize("days", [0, 1, 5, 10, 11])
def test_undocumented_discharge_curves_are_rejected(days):
    """Tabel 39 geeft alleen 2, 3 en 4 dagen; de rest was met de hand verzonnen."""
    with pytest.raises(ValueError):
        _get_discharge_curve(days)

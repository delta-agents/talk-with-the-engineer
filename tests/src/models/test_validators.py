"""Ongeldige invoer moet worden afgewezen, en de reden hoort in het schema te staan.

De toegestane waarden zitten als `Literal` in het type en dus als `enum` in het
JSON-schema. Pydantic valideert ze daarmee zelf; er zijn geen eigen validators meer voor
nodig. Dat maakt de beperking zichtbaar voor een MCP-client in plaats van alleen leesbaar
in een beschrijving.
"""

import pytest
from pydantic import ValidationError
from pydantic_ai import ModelRetry

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


# --- gemaalcapaciteit: vijf eenheden, een grootheid ---------------------------------

STORM = {"return_period": 100, "delta_h_available": 1.0, "area_ha": 4000}


def test_l_s_ha_is_converted_to_the_other_units():
    """1,5 l/s/ha op 4000 ha is 6 m3/s; de klassieke Nederlandse maalcapaciteit.

    l/s/ha ontbrak, terwijl de bandbreedtes in alle vier de andere beschrijvingen er wel
    in zijn uitgedrukt. Het is de eenheid waarin een waterbeheerder denkt.
    """
    model = StoreInputGivenH(discharge_capacity_l_s_ha=1.5, **STORM)
    assert model.discharge_capacity_m3_per_sec == pytest.approx(6.0)
    assert model.discharge_capacity_m3_per_min == pytest.approx(360.0)
    assert model.discharge_capacity_m3_per_day == pytest.approx(518_400.0)
    assert model.discharge_capacity_mm_d == pytest.approx(12.96)


@pytest.mark.parametrize(
    "field, value",
    [
        ("discharge_capacity_m3_per_sec", 6.0),
        ("discharge_capacity_m3_per_min", 360.0),
        ("discharge_capacity_m3_per_day", 518_400.0),
        ("discharge_capacity_mm_d", 12.96),
        ("discharge_capacity_l_s_ha", 1.5),
    ],
)
def test_all_five_units_describe_the_same_pump(field, value):
    """Welke eenheid je ook invult, de andere vier komen op dezelfde capaciteit uit."""
    model = StoreInputGivenH(**{field: value}, **STORM)
    assert model.discharge_capacity_m3_per_sec == pytest.approx(6.0)
    assert model.discharge_capacity_l_s_ha == pytest.approx(1.5)
    assert model.discharge_capacity_mm_d == pytest.approx(12.96)


def test_one_l_s_ha_is_8_64_mm_per_day():
    """De omrekenfactor die de beschrijvingen noemen, vastgelegd.

    De mm/dag-beschrijving noemde jarenlang "1 tot 5 mm/dag" terwijl dat de l/s/ha-getallen
    waren; een factor 8,64 mis. Deze test legt de factor vast zodat de tekst en de code
    niet opnieuw uit elkaar kunnen lopen.
    """
    model = StoreInputGivenH(discharge_capacity_l_s_ha=1.0, **STORM)
    assert model.discharge_capacity_mm_d == pytest.approx(8.64)


def test_missing_discharge_capacity_explains_itself():
    """Zonder capaciteit hoort er uitleg te komen, geen TypeError.

    De foutmelding stond er wel, maar in een onbereikbare `else`: het `if/elif` op mm/dag
    dekte None en niet-None allebei af. Wie het gemaal vergat, kreeg
    "unsupported operand type(s) for /: 'NoneType' and 'float'".
    """
    with pytest.raises(Exception) as excinfo:
        StoreInputGivenH(**STORM)
    assert not isinstance(excinfo.value, TypeError)
    assert "discharge_capacity_l_s_ha" in str(excinfo.value)


# --- twee eenheden voor dezelfde grootheid: weigeren en niet stil kiezen -------------


@pytest.mark.parametrize(
    "conflict, expected",
    [
        ({"area_m2": 99_000_000}, "oppervlak"),
        (
            {"discharge_capacity_m3_per_sec": 5, "discharge_capacity_l_s_ha": 99},
            "gemaalcapaciteit",
        ),
    ],
)
def test_the_same_quantity_in_two_units_is_refused(conflict, expected):
    """Het gevaarlijkste faaltype: een plausibel en volledig fout antwoord zonder signaal.

    Er was een prioriteitsvolgorde - `_ha` won van `_m2` - en die was voor de beller
    onzichtbaar. 4000 ha en 99 000 000 m2 samen leverden exact de uitvoer van 4000 ha op,
    zonder melding en zonder regel in `assumptions`, terwijl die twee een factor 25
    schelen. Een taalmodel dat tussen twee eenheden twijfelt en er "voor de zekerheid"
    twee invult, kreeg dus geen correctie.
    """
    payload = {**STORM, **conflict}
    payload.setdefault("discharge_capacity_m3_per_sec", 5)

    with pytest.raises(ModelRetry) as refusal:
        StoreInputGivenH(**payload)

    message = str(refusal.value)
    assert expected in message
    # de melding noemt beide velden met hun waarde, zodat de beller ziet welke hij weglaat
    for field in conflict:
        assert field in message


def test_one_unit_is_still_fine():
    """De weigering gaat alleen af bij een conflict, niet bij een gewone aanroep."""
    model = StoreInputGivenH(discharge_capacity_l_s_ha=1.5, **STORM)
    assert model.discharge_capacity_m3_per_sec == pytest.approx(6.0)


def test_a_missing_area_explains_itself_in_the_house_style():
    """Nederlands en uitleggend, zoals de rest van de meldingen; niet Engels en kaal."""
    with pytest.raises(ModelRetry) as refusal:
        StoreInputGivenH(
            return_period=100, delta_h_available=1.0, discharge_capacity_m3_per_sec=5
        )
    assert "area_ha" in str(refusal.value)
    assert "must be provided" not in str(refusal.value)

"""Maatregel vasthouden.

Anders dan bergen en afvoeren heeft deze maatregel een optimum: voorbij een zeker areaal
valt de vertraagde afvoer van het ene deel samen met de piek van het andere. Dat staat ook
zo in Ton's rekenblad.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.interface.schemas.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
    RetentionOutput,
)
from talk_with_the_engineer.interface.tools.retain import (
    calculate_retention_given_area,
    calculate_retention_given_h,
)

POLDER_SUMMER = {
    "area_ha": 4000,
    "time_of_year": "summer",
    "return_period": 10,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_sec": 5,
}


@pytest.mark.asyncio
async def test_retention_given_h_returns_a_usable_answer(test_context):
    result: RetentionOutput = await calculate_retention_given_h(
        test_context,
        RetentionInputGivenH(
            return_period=200,
            time_of_year="summer",
            length_event_hrs=96,
            rainfall_regime="L",
            area_ha=4000,
            percentage_open_water=3.5,
            discharge_capacity_m3_per_sec=5,
            delta_h_available=0.3,
        ),
    )
    assert result.data["area_polder_delayed_ha"] >= 0
    assert result.measure.after >= 0


@pytest.mark.asyncio
async def test_retention_given_area_uses_the_land_area_as_reference(test_context):
    """Het retentie-areaal is een fractie van het LAND en niet van de hele polder."""
    result: RetentionOutput = await calculate_retention_given_area(
        test_context, RetentionInputGivenArea(delta_area_ha=1158, **POLDER_SUMMER)
    )
    # 1158 ha op 3860 ha land is 30,0 %; op 4000 ha zou het 29,0 % zijn
    assert result.data["area_percentage_delayed"] == pytest.approx(30.0, abs=1e-6)
    assert result.measure.after == pytest.approx(1158)


@pytest.mark.asyncio
async def test_retention_roundtrip_closes_inside_the_feasible_range(test_context):
    inverse: RetentionOutput = await calculate_retention_given_h(
        test_context, RetentionInputGivenH(delta_h_available=0.08, **POLDER_SUMMER)
    )
    assert inverse.status is SolveStatus.EXACT

    forward: RetentionOutput = await calculate_retention_given_area(
        test_context,
        RetentionInputGivenArea(
            delta_area_ha=inverse.data["area_polder_delayed_ha"], **POLDER_SUMMER
        ),
    )
    assert forward.dh_with_measure_m == pytest.approx(0.08, abs=1e-3)


@pytest.mark.asyncio
async def test_retention_target_above_reference_needs_no_measure(test_context):
    result: RetentionOutput = await calculate_retention_given_h(
        test_context, RetentionInputGivenH(delta_h_available=1.5, **POLDER_SUMMER)
    )
    assert result.status is SolveStatus.NO_MEASURE_NEEDED
    assert result.data["area_polder_delayed_ha"] == 0


@pytest.mark.asyncio
async def test_retention_reports_its_optimum_when_the_target_is_out_of_reach(
    test_context,
):
    """De referentiebui: vasthouden komt niet lager dan ongeveer 1,46 m."""
    result: RetentionOutput = await calculate_retention_given_h(
        test_context,
        RetentionInputGivenH(
            return_period=1000,
            time_of_year="winter",
            length_event_hrs=96.0,
            name_rainfall_pattern="p1a",
            days_to_discharge=4,
            rainfall_regime="R",
            area_ha=4000,
            percentage_open_water=3.5,
            discharge_capacity_m3_per_sec=5,
            delta_h_available=1.0,
        ),
    )
    assert result.status is SolveStatus.ACTION_INFEASIBLE
    # in de volledige waterbalans ligt het optimum hoger dan de 1,46 m van het rekenblad,
    # doordat de neerslag op het open water erbij komt
    assert result.feasible_dh_min_m == pytest.approx(1.56, abs=0.03)
    assert "optimum" in result.description
    assert "bergen of afvoeren" in result.description


@pytest.mark.asyncio
async def test_retention_rejects_negative_area(test_context):
    with pytest.raises(ModelRetry):
        await calculate_retention_given_area(
            test_context, RetentionInputGivenArea(delta_area_ha=-100, **POLDER_SUMMER)
        )


# --- het schema en de validatie zeggen nu hetzelfde ---------------------------------


def test_a_negative_retention_area_is_refused_with_an_explanation():
    """Het schema nodigde uit tot een aanroep die per definitie faalde.

    De veldbeschrijving zei "positive for increase, negative for decrease" en de tool
    weigerde elke negatieve waarde. Nu staat de ondergrens in het schema en legt de
    weigering uit waar de beller wél heen kan.
    """
    with pytest.raises(ModelRetry) as refusal:
        RetentionInputGivenArea(
            area_ha=4000,
            delta_area_ha=-5000,
            discharge_capacity_m3_per_sec=5,
            return_period=100,
        )
    assert "negatief" in str(refusal.value)
    assert "pydantic" not in str(refusal.value)


def test_the_lower_bound_is_visible_in_the_schema():
    """`minimum: 0`, zodat een client hem ziet voordat hij de aanroep verstuurt.

    Bewust geen `ge=0`: een pydantic-constraint levert aan de MCP-grens een rauwe
    validatiedump op, met een link naar errors.pydantic.dev erin.
    """
    schema = RetentionInputGivenArea.model_json_schema()["properties"]
    assert schema["delta_area_ha"]["minimum"] == 0
    assert schema["delta_area_m2"]["minimum"] == 0


def test_the_state_reads_the_delay_from_the_input_field():
    """`days_to_retain_discharge` op de invoer wordt `days_to_retain` op de toestand.

    Het enige veld in de toolset met een naamverschil tussen invoer en toestand, en daarmee
    het enige veld waar een vertaling kan worden overgeslagen. Slaat een pad hem over, dan
    rekent dat pad stilzwijgend met de standaardwaarde van twee dagen door.

    Deze test staat bewust op modelniveau en niet op tooluitkomsten. Een tool zonder die
    vertaling geeft dezelfde antwoorden als een gevoeligheidsrij zonder die vertaling, dus
    tool en rij naast elkaar leggen bewijst niets: het anker moet eronder liggen.
    """
    base = {"area_ha": 4000, "discharge_capacity_m3_per_sec": 5, "return_period": 100}

    for days in (0, 2, 4):
        state = PolderState.from_water_system_input(
            RetentionInputGivenH(
                **base, delta_h_available=1.0, days_to_retain_discharge=days
            )
        )
        assert state.days_to_retain == days

    # weggelaten: dan vult het invoermodel zijn eigen fallback in, en die telt ook
    omitted = PolderState.from_water_system_input(
        RetentionInputGivenH(**base, delta_h_available=1.0)
    )
    assert omitted.days_to_retain == 2

    # een invoermodel zonder dit veld - bergen, afvoeren - blijft op de standaardwaarde
    from talk_with_the_engineer.interface.schemas.store import StoreInputGivenH

    other = PolderState.from_water_system_input(
        StoreInputGivenH(**base, delta_h_available=1.0)
    )
    assert other.days_to_retain == 2

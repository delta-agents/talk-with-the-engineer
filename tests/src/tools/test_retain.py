"""Maatregel vasthouden.

Anders dan bergen en afvoeren heeft deze maatregel een optimum: voorbij een zeker areaal
valt de vertraagde afvoer van het ene deel samen met de piek van het andere. Dat staat ook
zo in Ton's rekenblad.
"""

import pytest
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.results import SolveStatus
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
    RetentionOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.retain import (
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
    assert result.state_after.retention_fraction >= 0


@pytest.mark.asyncio
async def test_retention_given_area_uses_the_land_area_as_reference(test_context):
    """D4: het retentie-areaal is een fractie van het LAND, niet van de hele polder."""
    result: RetentionOutput = await calculate_retention_given_area(
        test_context, RetentionInputGivenArea(delta_area_ha=1158, **POLDER_SUMMER)
    )
    # 1158 ha op 3860 ha land is 30,0 %; op 4000 ha zou het 29,0 % zijn
    assert result.data["area_percentage_delayed"] == pytest.approx(30.0, abs=1e-6)
    assert result.state_after.retention_area_ha == pytest.approx(1158)


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
    assert result.status is SolveStatus.INFEASIBLE
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

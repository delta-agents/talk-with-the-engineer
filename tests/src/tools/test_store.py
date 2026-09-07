"""Maatregel bergen."""

import pytest
from pydantic import ValidationError
from pydantic_ai import ModelRetry

from talk_with_the_engineer.core.results import SolveStatus
from talk_with_the_engineer.interface.schemas.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.interface.tools.store import (
    calculate_store_given_area,
    calculate_store_given_h,
)

# Bij deze bui en polder ligt het haalbare bereik op [0,52 , 1,04] m.
SMALL_POLDER_SUMMER = {
    "area_ha": 4000,
    "time_of_year": "summer",
    "return_period": 10,
    "percentage_open_water": 3.5,
    "discharge_capacity_m3_per_min": 5,
}


@pytest.mark.asyncio
async def test_store_given_h_returns_a_usable_answer(test_context):
    result: StoreOutput = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            return_period=200,
            time_of_year="summer",
            length_event_hrs=96,
            rainfall_regime="L",
            area_ha=4000,
            discharge_capacity_m3_per_sec=5,
            percentage_open_water=3.5,
            delta_h_available=0.3,
        ),
    )
    assert result.status is SolveStatus.EXACT
    assert result.data["delta_open_water_ha"] > 0
    assert result.measure.after > result.measure.before
    assert result.dh_reference_m - result.dh_with_measure_m > 0


@pytest.mark.asyncio
async def test_store_given_area_returns_a_usable_answer(test_context):
    result: StoreOutput = await calculate_store_given_area(
        test_context,
        StoreInputGivenArea(
            return_period=200,
            time_of_year="winter",
            length_event_hrs=96,
            rainfall_regime="L",
            area_ha=100,
            discharge_capacity_m3_per_min=5,
            area_available_ha=10,
        ),
    )
    assert result.description
    assert result.dh_reference_m - result.dh_with_measure_m > 0
    assert result.measure.after == pytest.approx(result.measure.before + 10)


@pytest.mark.asyncio
async def test_store_roundtrip_closes_inside_the_feasible_range(test_context):
    """Het rondje sluit voor een doel binnen het haalbare bereik.

    Deze test mikte eerder op 210 cm terwijl de stijging bij deze bui 104 cm is. Het doel
    lag dus boven de referentie, en dat het rondje toch sloot kwam doordat `np.interp` aan
    beide kanten klemde.
    """
    target_m = 0.8

    inverse: StoreOutput = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(delta_h_available=target_m, **SMALL_POLDER_SUMMER),
    )
    assert inverse.status is SolveStatus.EXACT

    forward: StoreOutput = await calculate_store_given_area(
        test_context,
        StoreInputGivenArea(
            area_available_ha=inverse.data["delta_open_water_ha"], **SMALL_POLDER_SUMMER
        ),
    )
    assert forward.dh_with_measure_m == pytest.approx(target_m, abs=1e-3)


@pytest.mark.asyncio
async def test_store_target_above_reference_needs_no_measure(test_context):
    result: StoreOutput = await calculate_store_given_h(
        test_context, StoreInputGivenH(delta_h_available=2.1, **SMALL_POLDER_SUMMER)
    )
    assert result.status is SolveStatus.NO_MEASURE_NEEDED
    assert result.data["delta_open_water_ha"] == 0
    assert "niet nodig" in result.description


@pytest.mark.asyncio
async def test_store_target_below_optimum_is_infeasible(test_context):
    result: StoreOutput = await calculate_store_given_h(
        test_context, StoreInputGivenH(delta_h_available=0.01, **SMALL_POLDER_SUMMER)
    )
    assert result.status is SolveStatus.ACTION_INFEASIBLE
    assert result.data["delta_open_water_ha"] > 0
    assert "niet haalbaar" in result.description


@pytest.mark.asyncio
async def test_store_rejects_more_open_water_than_the_polder_has(test_context):
    """8000 ha open water op een polder van 4000 ha werd eerder stil geaccepteerd."""
    with pytest.raises(ModelRetry):
        await calculate_store_given_area(
            test_context,
            StoreInputGivenArea(area_available_ha=8000, **SMALL_POLDER_SUMMER),
        )


def test_store_rejects_negative_area():
    """Negatief extra open water wordt door het schema afgewezen, niet door de toolbody.

    `area_available_ha` heeft `ge=0`, dus het model komt niet eens tot stand. Dat is een
    laag eerder dan voorheen en levert een pydantic-fout met veldpad op.
    """
    with pytest.raises(ValidationError):
        StoreInputGivenArea(area_available_ha=-500, **SMALL_POLDER_SUMMER)

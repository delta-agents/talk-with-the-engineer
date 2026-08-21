"""Maatregel bergen: land omzetten in open water.

Grijpt aan op `pct_open_water` van de polder-toestand. Beide richtingen lopen over
dezelfde `simulate`: vooruit met `evaluate`, achteruit met `solve`.
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import BergenAction
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    describe_forward,
    describe_inverse,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import evaluate, solve
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SQUARE_METRES_PER_HECTARE = 10_000


def _data(result, volume_rain_mm, rainfall_per_day):
    state_after = result.state_after
    return {
        "volume_rain_mm": volume_rain_mm,
        "rainfall_per_day": rainfall_per_day,
        # het antwoord: hoeveel open water er bij moet
        "delta_open_water_ha": result.magnitude,
        # de situatie na de maatregel
        "area_ha_required_open_water": state_after.area_open_water_ha,
        "area_m2_required_open_water": state_after.area_open_water_ha
        * SQUARE_METRES_PER_HECTARE,
        "new_area_percentage": state_after.pct_open_water,
        "dh_reference_cm": result.dh_reference_m * 100,
        "dh_with_measure_cm": result.dh_with_measure_m * 100,
        "dh_reduction_cm": result.dh_reduction_m * 100,
        "feasible_dh_min_cm": result.feasible_dh_min_m * 100,
        "feasible_dh_max_cm": result.feasible_dh_max_m * 100,
        "magnitude_at_optimum_ha": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

    state = PolderState.from_water_system_input(input)
    reference = simulate(state, input)
    return state, reference.volume_rain_mm, reference.rainfall_per_day_mm.tolist()


@log_tool_call
async def calculate_store_given_h(ctx, input: StoreInputGivenH) -> StoreOutput:
    """Hoeveel open water is er nodig om de waterstandstijging onder een grens te houden?

    Bergen = store.
    """
    state, volume_rain_mm, rainfall_per_day = _simulation_context(input)
    result = solve(state, input, BergenAction(), input.delta_h_available)

    return StoreOutput.from_solve_result(
        result,
        data=_data(result, volume_rain_mm, rainfall_per_day),
        description=describe_inverse(result, input.return_period, input.language),
    )


@log_tool_call
async def calculate_store_given_area(ctx, input: StoreInputGivenArea) -> StoreOutput:
    """Welke waterstandstijging hoort bij een gegeven hoeveelheid extra open water?

    Bergen = store.
    """
    state, volume_rain_mm, rainfall_per_day = _simulation_context(input)
    action = BergenAction(delta_open_water_ha=input.area_available_ha)
    result = evaluate(state, input, action)

    return StoreOutput.from_solve_result(
        result,
        data=_data(result, volume_rain_mm, rainfall_per_day),
        description=describe_forward(result, input.return_period, input.language),
    )

"""Maatregel vasthouden: de afvoer van een deel van het land vertragen.

Grijpt aan op `retention_fraction` van de polder-toestand, een fractie van het
LANDoppervlak. Anders dan bergen en afvoeren heeft deze maatregel een optimum: voorbij een
zeker areaal valt de vertraagde afvoer van het ene deel samen met de piek van het andere en
wordt het weer slechter. `solve` zoekt daarom eerst dat optimum.
"""

from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
    RetentionOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    describe_forward,
    describe_inverse,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.solve import evaluate, solve
from talk_with_the_engineer.utils.logging_utils import log_tool_call


def _data(result, volume_rain_mm, rainfall_per_day):
    state_after = result.state_after
    return {
        "volume_rain_mm": volume_rain_mm,
        "rainfall_per_day": rainfall_per_day,
        # het antwoord: hoeveel land er voor retentie wordt ingericht
        "area_polder_delayed_ha": result.magnitude,
        "area_percentage_delayed": state_after.retention_fraction * 100,
        "days_to_retain": state_after.days_to_retain,
        "dh_reference_cm": result.dh_reference_m * 100,
        "dh_with_measure_cm": result.dh_with_measure_m * 100,
        "dh_reduction_cm": result.dh_reduction_m * 100,
        "feasible_dh_min_cm": result.feasible_dh_min_m * 100,
        "feasible_dh_max_cm": result.feasible_dh_max_m * 100,
        "magnitude_at_optimum_ha": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

    state = PolderState.from_water_system_input(
        input, days_to_retain=input.days_to_retain_discharge
    )
    reference = simulate(state, input)
    return state, reference.volume_rain_mm, reference.rainfall_per_day_mm.tolist()


@log_tool_call
async def calculate_retention_given_h(
    ctx, input: RetentionInputGivenH
) -> RetentionOutput:
    """Hoeveel land moet voor retentie worden ingericht om onder een grens te blijven?

    Vasthouden = retention.
    """
    state, volume_rain_mm, rainfall_per_day = _simulation_context(input)
    result = solve(state, input, VasthoudenAction(), input.delta_h_available)

    return RetentionOutput.from_solve_result(
        result,
        data=_data(result, volume_rain_mm, rainfall_per_day),
        description=describe_inverse(result, input.return_period, input.language),
    )


@log_tool_call
async def calculate_retention_given_area(
    ctx, input: RetentionInputGivenArea
) -> RetentionOutput:
    """Welke waterstandstijging hoort bij een gegeven retentie-areaal?

    Vasthouden = retention.
    """
    if input.delta_area_ha < 0:
        raise ModelRetry(
            "delta_area_ha is het areaal dat voor retentie wordt ingericht en kan niet "
            "negatief zijn."
        )

    state, volume_rain_mm, rainfall_per_day = _simulation_context(input)
    action = VasthoudenAction(delta_retention_ha=input.delta_area_ha)
    result = evaluate(state, input, action)

    return RetentionOutput.from_solve_result(
        result,
        data=_data(result, volume_rain_mm, rainfall_per_day),
        description=describe_forward(result, input.return_period, input.language),
    )

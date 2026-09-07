"""Maatregel bergen: land omzetten in open water.

Grijpt aan op `pct_open_water` van de polder-toestand. Beide richtingen lopen over
dezelfde `simulate`: vooruit met `evaluate`, achteruit met `solve`.
"""

from talk_with_the_engineer.core.actions import BergenAction
from talk_with_the_engineer.epistemics.assumptions import assumed_defaults
from talk_with_the_engineer.epistemics.priceless import priceless_posts
from talk_with_the_engineer.epistemics.uncertainty import supported_digits
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.interface.schemas.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)
from talk_with_the_engineer.interface.descriptions import (
    append_assumptions,
    append_spread,
    describe_forward,
    describe_inverse,
)
from talk_with_the_engineer.core.inverse import (
    evaluate,
    solve,
)
from talk_with_the_engineer.epistemics.uncertainty import (
    forward_answer_for,
    inverse_answer_for,
    spread_of,
    uncertainty_for,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

SQUARE_METRES_PER_HECTARE = 10_000


def _data(result, rain):
    state_after = result.state_after
    return {
        # bruto - verlies = som van de netto dagreeks; zie _simulation_context
        **rain,
        # het antwoord: hoeveel open water er bij moet
        "delta_open_water_ha": result.magnitude,
        # de situatie na de maatregel
        "area_ha_required_open_water": state_after.area_open_water_ha,
        "area_m2_required_open_water": state_after.area_open_water_ha
        * SQUARE_METRES_PER_HECTARE,
        "new_area_percentage": state_after.pct_open_water,
        "magnitude_at_optimum_ha": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    from talk_with_the_engineer.core.transition import (
        simulate,
        storm_shape,
    )

    state = PolderState.from_water_system_input(input)
    reference = simulate(state, input.to_storm())
    return state, storm_shape(reference, input.to_storm())


@log_tool_call
async def calculate_store_given_h(ctx, input: StoreInputGivenH) -> StoreOutput:
    """Hoeveel open water is er nodig om de waterstandstijging onder een grens te houden?

    Bergen = store.
    """
    state, rain = _simulation_context(input)
    result = solve(state, input.to_storm(), BergenAction(), input.delta_h_available)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        inverse_answer_for(BergenAction, "delta_h_available"),
        has_cost=result.cost is not None,
    )

    return StoreOutput.from_solve_result(
        result,
        sensitivity=sensitivity,
        caveats=caveats,
        data=_data(result, rain),
        priceless=priceless_posts(input, result.measure_nl),
        description=append_assumptions(
            append_spread(
                describe_inverse(
                    result,
                    input,
                    input.language,
                    supported_digits(
                        spread_of(sensitivity, result.magnitude), result.magnitude
                    ),
                ),
                sensitivity,
                result.magnitude,
                "ha",
                input.language,
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )


@log_tool_call
async def calculate_store_given_area(ctx, input: StoreInputGivenArea) -> StoreOutput:
    """Welke waterstandstijging hoort bij een gegeven hoeveelheid extra open water?

    Bergen = store.
    """
    state, rain = _simulation_context(input)
    action = BergenAction(delta_open_water_ha=input.area_available_ha)
    result = evaluate(state, input.to_storm(), action)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        forward_answer_for(lambda: action),
        has_cost=result.cost is not None,
    )

    return StoreOutput.from_solve_result(
        result,
        sensitivity=sensitivity,
        caveats=caveats,
        data=_data(result, rain),
        priceless=priceless_posts(input, result.measure_nl),
        description=append_assumptions(
            append_spread(
                describe_forward(
                    result,
                    input,
                    input.language,
                    supported_digits(
                        spread_of(sensitivity, result.magnitude), result.magnitude
                    ),
                ),
                sensitivity,
                result.magnitude,
                "ha",
                input.language,
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
    )

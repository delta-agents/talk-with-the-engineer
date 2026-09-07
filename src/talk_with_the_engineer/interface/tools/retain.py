"""Maatregel vasthouden: de afvoer van een deel van het land vertragen.

Grijpt aan op `retention_fraction` van de polder-toestand, een fractie van het
LANDoppervlak. Anders dan bergen en afvoeren heeft deze maatregel een optimum: voorbij een
zeker areaal valt de vertraagde afvoer van het ene deel samen met de piek van het andere en
wordt het weer slechter. `solve` zoekt daarom eerst dat optimum.
"""

from talk_with_the_engineer.core.actions import (
    VasthoudenAction,
)
from talk_with_the_engineer.interface.schemas.retain import (
    RetentionInputGivenArea,
    RetentionInputGivenH,
    RetentionOutput,
)
from talk_with_the_engineer.epistemics.assumptions import assumed_defaults
from talk_with_the_engineer.epistemics.priceless import priceless_posts
from talk_with_the_engineer.epistemics.uncertainty import supported_digits
from talk_with_the_engineer.core.state import PolderState
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


def _data(result, rain):
    state_after = result.state_after
    return {
        # bruto - verlies = som van de netto dagreeks; zie _simulation_context
        **rain,
        # het antwoord: hoeveel land er voor retentie wordt ingericht
        "area_polder_delayed_ha": result.magnitude,
        "area_percentage_delayed": state_after.retention_fraction * 100,
        "days_to_retain": state_after.days_to_retain,
        "magnitude_at_optimum_ha": result.magnitude_at_optimum,
    }


def _simulation_context(input):
    """De uitgangstoestand en de bui, zoals deze tool ze rapporteert.

    `days_to_retain_discharge` wordt niet meer hier vertaald: `from_water_system_input`
    leest hem zelf van de invoer. Die vertaling stond op twee plekken - hier wel en in de
    gevoeligheidsroutine niet - en dat was precies de stale rij uit B3.
    """
    from talk_with_the_engineer.core.transition import (
        simulate,
        storm_shape,
    )

    state = PolderState.from_water_system_input(input)
    reference = simulate(state, input.to_storm())
    return state, storm_shape(reference, input.to_storm())


@log_tool_call
async def calculate_retention_given_h(
    ctx, input: RetentionInputGivenH
) -> RetentionOutput:
    """Hoeveel land moet voor retentie worden ingericht om onder een grens te blijven?

    Vasthouden = retention.
    """
    state, rain = _simulation_context(input)
    result = solve(state, input.to_storm(), VasthoudenAction(), input.delta_h_available)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        inverse_answer_for(VasthoudenAction, "delta_h_available"),
        has_cost=result.cost is not None,
    )

    return RetentionOutput.from_solve_result(
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
async def calculate_retention_given_area(
    ctx, input: RetentionInputGivenArea
) -> RetentionOutput:
    """Welke waterstandstijging hoort bij een gegeven retentie-areaal?

    Vasthouden = retention.
    """
    # De ondergrens op `delta_area_ha` staat in het invoermodel, waar hij ook in het schema
    # terechtkomt; hier stond hij eerder een tweede keer.
    state, rain = _simulation_context(input)
    action = VasthoudenAction(delta_retention_ha=input.delta_area_ha)
    result = evaluate(state, input.to_storm(), action)

    assumptions = assumed_defaults(input)
    sensitivity, caveats = uncertainty_for(
        input,
        forward_answer_for(lambda: action),
        has_cost=result.cost is not None,
    )

    return RetentionOutput.from_solve_result(
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

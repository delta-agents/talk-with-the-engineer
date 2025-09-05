"""
Calculates holding capacity
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.hold import (
    HoldInput,
    HoldOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call


# TODO: refactor to polder_hold_tool when we add brook = beek
@log_tool_call
async def hold_tool(ctx, input: HoldInput) -> HoldOutput:
    """
    Given a return period return the amount of area needed to hold all the water.
    Specifically for a polder system.
    Hold = Vasthouden
    """
    # same calculation for all
    flow_per_day, rainfall_per_day, model_matrix, volume_rain_mm = get_rainfall(input)

    # TODO: Hold is different
    # need a parameter more: delay_when_held_in_polder_days = 2 days
    # We need an extra model matrix, where we delay the rainfall for part of the area
    # and see how much area is needed to hold the water.

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    description = (
        f"Holding capacity needed is not yet implemented of, we do know the volume is  {data['volume_rain_mm']}mm"
        + f" with a return period of {input.return_period} years"
        + f" and a model matrix {data['model_matrix']}"
    )
    return HoldOutput(
        data=data,
        description=description,
    )

"""
Example of a tool cal
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInput,
    StoreOutput,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call
from pydantic_ai import ModelRetry


@log_tool_call
async def store_tool(ctx, input: StoreInput) -> StoreOutput:
    """

    Given a return period return the amount of area needed to hold all the water.
    """

    return_period_dict = {
        100: 30,  # mm
        200: 60,  # mm
    }

    if input.return_period:
        rainfall_amount_mm = return_period_dict[input.return_period]

    else:
        ModelRetry(
            f"Invalid return period, should be one of: {list(return_period_dict.keys())}"
        )

    volume = rainfall_amount_mm * input.area
    data = {"rainfall": rainfall_amount_mm, "volume": volume}

    return StoreOutput(
        data=data,
        description=f"A storage capacity of {data['volume']}m3 is needed for a return period of {input.return_period} years",
    )

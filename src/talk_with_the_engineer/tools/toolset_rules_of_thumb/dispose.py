"""
Example of a tool cal
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.dispose import (
    DisposeInput,
    DisposeOutput,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call
from pydantic_ai import ModelRetry


@log_tool_call
async def dispose_tool(ctx, input: DisposeInput) -> DisposeOutput:
    """

    Given a return period return the amount of area needed to hold all the water.
    """

    return_period_dict = {100: {"mm": 30}, 200: {"mm": 60}}

    if input.return_period:
        data = return_period_dict[input.return_period]

    else:
        ModelRetry(
            f"Invalid return period, should be one of: {list(return_period_dict.keys())}"
        )

    return DisposeOutput(
        data=data,
        description=f"Storage capacity of {data['mm']}mm with a return period of {input.return_period} years",
    )

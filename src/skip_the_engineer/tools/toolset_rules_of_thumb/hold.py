"""
Example of a tool cal
"""

from skip_the_engineer.models.modelset_rules_of_thumb.hold import (
    HoldInput,
    HoldOutput,
)
from skip_the_engineer.utils.logging_utils import log_tool_call
from pydantic_ai import ModelRetry

@log_tool_call
async def hold_tool(ctx, input: HoldInput) -> HoldOutput:
    """

    Given a return period return the amount of area needed to hold all the water. 
    """

    return_period_dict = {
       100: {"mm": 30},
       200: {"mm": 60}
    }

    if input.return_period:
       data = return_period_dict[input.return_period]  

    else:
       ModelRetry("Invalid return period")



    return HoldOutput(data=data, description="Example data")

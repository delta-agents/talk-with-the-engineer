"""
Example of a tool cal
"""

from AI_agents_template.models.modelset_1.example1 import (
    Example1Input,
    Example1Output,
)
from AI_agents_template.utils.logging_utils import log_tool_call


@log_tool_call
async def example1_tool(ctx, input: Example1Input) -> Example1Output:
    """
    Show example1.
    """
    #  you can access any context added to the ctx: Deps object
    ctx.deps.cache_database_db
    data = {"example": 0, "of": 1, "how": 2, "data": 3, "might": 4, "look": 5}
    new_data = {}
    for val in data:
        new_data[val] = data[val] + input.index
    return Example1Output(data=new_data, description="Example data")

"""
Example of a tool cal
"""

from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInput,
    StoreOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call


@log_tool_call
async def store_tool(ctx, input: StoreInput) -> StoreOutput:
    """

    Given a return period returns the flow rate.
    """

    flow_per_day, rainfall_per_day, model_matrix, volume_rain_mm = get_rainfall(input)  # noqa: F821

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    description = (
        f"Holding capacity of {data['volume_rain_mm']}mm"
        + f" with a return period of {input.return_period} years"
        + f" and a model matrix {data['model_matrix']}"
    )
    return StoreOutput(
        data=data,
        description=description,
    )

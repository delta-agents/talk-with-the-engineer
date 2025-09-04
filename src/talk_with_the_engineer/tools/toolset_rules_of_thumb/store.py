"""
Example of a tool cal
"""

import numpy as np
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

    disposal_capacity_mm_d = (
        input.disposal_capacity_m3_per_day / input.area_m2 * 1000
    )  # m3/d / m2 = m/d -> *1000 = mm/d
    unaccounted_flow = np.zeros_like(flow_per_day)
    # TODO: make cumulative instead of stepwise
    for index, dh in enumerate(flow_per_day):
        unaccounted_flow[index] = max(dh - disposal_capacity_mm_d, 0)
    area_m2_current_open_water = input.area_m2 * (input.percentage_open_water / 100)

    delta_h_m_flow = (
        (unaccounted_flow / 1000) * input.area_m2 / area_m2_current_open_water
    )  # mm/d * m2 = mm*m2/d / 1000 = m3/d
    # to see how much additional storage we need to reduce this delta_h_m to
    area_m2_required_open_water = area_m2_current_open_water * (
        delta_h_m_flow / input.delta_h_available
    )
    area_ha_required_open_water = area_m2_required_open_water / 10000

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_day"] = flow_per_day.tolist()
    data["delta_h_m_flow"] = delta_h_m_flow.tolist()
    data["area_ha_required_open_water"] = area_ha_required_open_water.tolist()
    data["area_m2_required_open_water"] = area_m2_required_open_water.tolist()

    description = (
        f"Holding capacity of {data['volume_rain_mm']}mm"
        + f" with a return period of {input.return_period} years"
        + f" and a model matrix {data['model_matrix']}"
    )
    return StoreOutput(
        data=data,
        description=description,
    )

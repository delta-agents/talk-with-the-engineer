"""
Example of a tool cal
"""

import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.hold import (
    HoldInput,
    HoldOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall_stats import (
    get_rainfall_stats,
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

    volume_rain_mm = get_rainfall_stats(
        return_period=input.return_period,
        time_of_year=input.time_of_year,
        length_event_hrs=input.length_event_hrs,
        rainfall_regime=input.rainfall_regime,
    )
    disposal_curve = _get_disposal_curve(days_to_dispose=input.days_to_dispose)
    length_rainfall_even_days = (input.length_event_hrs / 24)
    volume_rain_mm_per_day = volume_rain_mm / length_rainfall_even_days
    MODEL_DAY_LENGTH = 7 # by then all water as left
    model_matrix = np.zeros((MODEL_DAY_LENGTH, length_rainfall_even_days))
    for column in range(length_rainfall_even_days):
        for row, value in enumerate(disposal_curve):
            model_matrix[row+column, column] = value


    data = {}
    data["volume_rain_mm"] = volume_rain_mm
    data["model_matrix"] = model_matrix
    data["volume_rain_mm_per_day"] = volume_rain_mm_per_day
    description = f"Holding capacity of {data['volume_rain_mm']}mm"\
                  + f" with a return period of {input.return_period} years"\
                  + f" and a model matrix {data['model_matrix']}"
    return HoldOutput(
        data=data,
        description=description,
    )


def _get_disposal_curve(days_to_dispose)-> list:
    """From HKV PR4991.10 • september 2024: Tabel 39
    Neerslag-afvoerrelatie,
    3 mogelijkheden,
    vertaling van de dagneerslag
    uit een vierdaags neerslagpatroon
    naar regionale afvoer over 2, 3 of 4 dagen.
    """
    data = {
        2: [0.35, 0.65],
        3: [0.25, 0.5, 0.25],
        4: [0.25, 0.25, 0.25, 0.25],
    }
    return data[days_to_dispose]

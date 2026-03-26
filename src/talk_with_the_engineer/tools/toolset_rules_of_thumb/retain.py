"""
Calculates retention capacity
"""

from pathlib import Path

import numpy as np
import pandas as pd
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    BaseInput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenH,
    RetentionInputGivenArea,
    RetentionOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_calculations import (
    clcMax_retain,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    get_discharge,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call

# eerste opzet
# adjust teh prc according to the input given by the user
prcAlst = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # % toename afvoercapaciteit
maxMtrLst = list(np.ones_like(prcAlst) * -9.99)  # max peiloverschreiding maatregel

@log_tool_call
async def calculate_retention_given_h(
    ctx, input: RetentionInputGivenH
) -> RetentionOutput:
    """
    Given a return period return the amount of area needed to retain all the water.
    Specifically for a polder system.
    Retention = Vasthouden
    """
    effect, rainfall_per_day, volume_rain_mm, model_matrix, flow_per_hour_l_s_ha = (
        calculate_effect_retain(input)
    )

    delta_h_available = input.delta_h_available

    # Interpolate the reduction in delta_h based on the percentage_area_available
    area_percentage_delayed = np.interp(
        delta_h_available, effect["dH_mtr [m]"], effect["percA [%]"]
    )
    area_polder_delayed_ha = area_percentage_delayed / 100 * input.area_ha

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["area_polder_delayed_ha"] = area_polder_delayed_ha
    data["area_percentage_delayed"] = area_percentage_delayed

    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_hour_l_s_ha"] = flow_per_hour_l_s_ha.tolist()

    delta_h_cm = input.delta_h_available * 100
    delay_days = input.days_to_retain_discharge
    return_period = input.return_period

    description_nl = (
        f"Met de maatregel 'vasthouden' (vertragen van neerslag met {delay_days} dagen) "
        f"kan de waterstandstijging minder dan {delta_h_cm:.0f} cm blijven "
        f"voor een bui eens per {return_period} jaar, "
        f"wanneer {area_percentage_delayed:.0f} % ({area_polder_delayed_ha:.0f} ha) van het gebied voor retentie wordt ingericht. \n"
        f"Door de maatregel 'vasthouden' wordt het maximum van de piekafvoer verkleind ten opzicht van een situatie zonder maatregelen."
    )

    description_en = (
        f"With the 'retention' measure (delaying rainfall by {delay_days} days) "
        f"the water level can remain below {delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years, "
        f"when {area_percentage_delayed:.0f} % ({area_polder_delayed_ha:.0f} ha) of the area is used for retention. \n"
        f"By the 'retention' measure, the maximum of the peak discharge is reduced."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return RetentionOutput(
        data=data,
        description=description,
    )


@log_tool_call
async def calculate_retention_given_area(
    ctx, input: RetentionInputGivenArea
) -> RetentionOutput:
    """
    Given a change in area for retention, return the resulting change in water level (can be reduction or increase).
    Specifically for a polder system.
    Retention = Vasthouden
    """

    effect, rainfall_per_day, volume_rain_mm, model_matrix, flow_per_hour_l_s_ha = (
        calculate_effect_retain(input)
    )

    area_available_ha = input.delta_area_ha
    percentage_area_available = area_available_ha / input.area_ha * 100

    # Interpolate the reduction in delta_h based on the percentage_area_available
    change_in_delta_h_m = np.interp(
        percentage_area_available, effect["percA [%]"], effect["dH_mtr [m]"]
    )

    change_in_delta_h_cm = change_in_delta_h_m * 100  # convert to cm

    # Prepare data dictionary
    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["model_matrix"] = model_matrix.tolist()
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["flow_per_hour_l_s_ha"] = flow_per_hour_l_s_ha.tolist()
    data["delta_area_ha"] = input.delta_area_ha
    data["change_in_delta_h_cm"] = change_in_delta_h_cm
    data["change_in_delta_h_m"] = change_in_delta_h_m

    delay_days = input.days_to_retain_discharge
    delta_area_ha = input.delta_area_ha
    return_period = input.return_period

    description_nl = (
        f"Als de maatregel 'vasthouden' (vertragen van neerslag met {delay_days} dagen) "
        f"wordt toegepast op {delta_area_ha:.0f} ha, "
        f"is de waterstandstijging {change_in_delta_h_cm:.0f} cm "
        f"bij een bui van eens per {return_period} jaar. \n"
        f"Door de maatregel 'vasthouden' wordt het maximum van de piekafvoer verkleind ten opzichte van een situatie zonder maatregelen."
    )

    description_en = (
        f"When the 'retention' measure (delaying rainfall by {delay_days} days) "
        f"is applied to {delta_area_ha:.0f} ha, "
        f"the water level increase is {change_in_delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years. \n"
        f"By the 'retention' measure, the maximum of the peak discharge is reduced."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return RetentionOutput(
        data=data,
        description=description,
    )


def calculate_effect_retain(input: BaseInput):
    rainfall_per_day, volume_rain_mm = get_rainfall(input)  # noqa: F821
    flow_per_hour_l_s_ha, model_matrix = get_discharge(input, rainfall_per_day)  # noqa: F821

    effect = pd.DataFrame(
        list(zip(prcAlst, maxMtrLst)), columns=["percA [%]", "dH_mtr [m]"]
    )

    debug = True
    if debug:
        path = Path(__file__).parent.parent.parent.parent.parent
        Qd_file = pd.read_csv(
            path / "scripts" / "scripts_Ton" / "drainage.csv",
            sep=",",
            encoding="latin1",
        )
        Qd = Qd_file.copy()
    else:
        Qd = pd.DataFrame(flow_per_hour_l_s_ha, columns=["drainage [l/s/ha]"])

    # VB polder
    totA = input.area_ha  # 4000  # ha
    area_open_water = input.percentage_open_water / 100 * totA  # ha open water (3,5%)
    area_land = totA - area_open_water  # ha overig
    pmpQ = input.discharge_capacity_m3_per_sec  # m3/s capaciteit
    dt = input.days_to_retain_discharge
    effect["dH_mtr [m]"] = effect["percA [%]"].apply(
        lambda x: clcMax_retain(x, Qd, area_open_water, area_land, pmpQ, dt)
    )

    return effect, rainfall_per_day, volume_rain_mm, model_matrix, flow_per_hour_l_s_ha

"""
Example of a tool cal
"""

from pathlib import Path

import numpy as np
import pandas as pd
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    BaseInput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.discharge import (
    DischargeInputGivenH,
    DischargeInputGivenDischarge,
    DischargeOutput,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_rainfall import (
    get_rainfall,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_discharge import (
    get_discharge,
)
from talk_with_the_engineer.utils.logging_utils import log_tool_call
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_calculations import (
    clcMax_discharge,
)

# eerste opzet
# adjust the prc according to the input given by the user
prcAlst = list(np.linspace(0, 100, 101))  # % toename afvoercapaciteit
maxMtrLst = list(np.ones_like(prcAlst) * -9.99)  # max peiloverschreiding maatregel


@log_tool_call
async def calculate_discharge_given_h(
    ctx, input: DischargeInputGivenH
) -> DischargeOutput:
    """

    Given a change in water level, return the amount of discharge capacity needed to achieve this change.
    Discharge = Afvoeren
    """
    effect, rainfall_per_day, volume_rain_mm, model_matrix, flow_per_hour_l_s_ha = (
        calculate_effect_discharge(input)
    )

    delta_h_available = input.delta_h_available

    # Interpolate the reduction in delta_h based on the percentage_area_available
    effect_sorted = effect.sort_values(by="dH_mtr [m]").reset_index(drop=True)
    effect_percentage = np.interp(
        delta_h_available, effect_sorted["dH_mtr [m]"], effect_sorted["percA [%]"]
    )
    # TODO: check results and add filtering for too low area_available, which would give a negative reduction in delta_h
    extra_discharge_capacity_m3_d_required = (
        effect_percentage / 100
    ) * input.discharge_capacity_m3_per_day

    extra_discharge_capacity_mm_d_required = (
        extra_discharge_capacity_m3_d_required / input.area_m2 * 1000
    )  # m3/d/m2=m/d/1000=mm/d
    extra_discharge_capacity_m3_per_min_required = (
        extra_discharge_capacity_m3_d_required / (60 * 24)
    )
    extra_discharge_capacity_m3_per_sec_required = (
        extra_discharge_capacity_m3_per_min_required / 60
    )

    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["effect_percentage"] = effect_percentage
    data["effect"] = effect.to_dict(orient="list")

    data["extra_discharge_capacity_m3_d_required"] = (
        extra_discharge_capacity_m3_d_required
    )
    data["extra_discharge_capacity_mm_d_required"] = (
        extra_discharge_capacity_mm_d_required
    )
    data["extra_discharge_capacity_m3_per_min_required"] = (
        extra_discharge_capacity_m3_per_min_required
    )
    data["extra_discharge_capacity_m3_per_sec_required"] = (
        extra_discharge_capacity_m3_per_sec_required
    )

    # TODO: check if this is correct
    extra_discharge_capacity_m3_per_min_required = (
        extra_discharge_capacity_m3_per_min_required
    )
    total_discharge_capactiy_m3_per_min = (
        extra_discharge_capacity_m3_per_min_required
        + input.discharge_capacity_m3_per_min
    )
    total_discharge_capactiy_mm_d = (
        #                             min * 60 = hr, * 24 = d, * 1000 = mm
        total_discharge_capactiy_m3_per_min * 60 * 24 / input.area_m2 * 1000
    )

    return_period = input.return_period
    delta_h_cm = input.delta_h_available * 100
    discharge_capacity_m3_per_min = input.discharge_capacity_m3_per_min
    extra_discharge_capacity_percentage = (
        extra_discharge_capacity_m3_per_min_required
        / discharge_capacity_m3_per_min
        * 100
    )

    description_nl = (
        f"Om de waterstand voor een bui van eens per {return_period} jaar "
        f"met {delta_h_cm:.0f} cm te verlagen, "
        f"moet de huidige afvoercapaciteit ({discharge_capacity_m3_per_min:.0f} m3/min) "
        f"met {extra_discharge_capacity_percentage:.0f} % ({total_discharge_capactiy_m3_per_min:.0f} m3/min) toenemen. \n"
        f"Door de maatregel 'afvoeren' wordt de capaciteit {total_discharge_capactiy_mm_d:.0f} mm/dag."
    )

    description_en = (
        f"To lower the water level by {delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years, "
        f"we need to increase the current discharge capacity ({discharge_capacity_m3_per_min:.0f} m3/min) "
        f"with {extra_discharge_capacity_percentage:.0f} % ({extra_discharge_capacity_m3_per_min_required:.0f} m3/min). \n"
        f"By the 'discharge' measure, the discharge capacity is increased to {total_discharge_capactiy_mm_d:.0f} mm/day."
    )
    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return DischargeOutput(
        data=data,
        description=description,
    )


@log_tool_call
async def calculate_discharge_given_discharge(
    ctx, input: DischargeInputGivenDischarge
) -> DischargeOutput:
    """

    Given a change in discharge capacity, return the resulting change in water level (can be reduction or increase).
    Discharge = Afvoeren
    """
    effect, rainfall_per_day, volume_rain_mm, model_matrix, flow_per_hour_l_s_ha = (
        calculate_effect_discharge(input)
    )

    percentage_area_available = (
        input.delta_discharge_capacity_m3_per_min
        / input.discharge_capacity_m3_per_min
        * 100
    )

    # Interpolate the reduction in delta_h based on the percentage_area_available
    effect_sorted = effect.sort_values(by="percA [%]").reset_index(drop=True)
    change_in_delta_h_m = np.interp(
        percentage_area_available,
        effect_sorted["percA [%]"],
        effect_sorted["dH_mtr [m]"],
    )
    # TODO: check results and add filtering for too low area_available, which would give a negative reduction in delta_h
    change_in_delta_h_cm = change_in_delta_h_m * 100

    # Prepare data dictionary
    data = {}
    data["volume_rain_mm"] = float(volume_rain_mm)
    data["rainfall_per_day"] = rainfall_per_day.tolist()
    data["delta_discharge_capacity_m3_per_min"] = (
        input.delta_discharge_capacity_m3_per_min
    )
    data["effect"] = effect.to_dict(orient="list")

    return_period = input.return_period
    delta_discharge_capacity_m3_per_min = input.delta_discharge_capacity_m3_per_min
    new_discharge_capacity_mm_d = (
        input.discharge_capacity_mm_d + input.delta_discharge_capacity_mm_d
    )

    description_nl = (
        f"Als met de maatregel 'afvoeren' de afvoercapaciteit wordt uitgebreid met {delta_discharge_capacity_m3_per_min:.0f} m3/min, "
        f"is de waterstandverlaging {change_in_delta_h_cm:.0f} cm "
        f"bij een bui van eens per {return_period} jaar. \n"
        f"Door de maatregel 'afvoeren' wordt de totale capaciteit {new_discharge_capacity_mm_d:.0f} mm/dag."
    )
    description_en = (
        f"When the 'discharge' measure increases the discharge capacity by {delta_discharge_capacity_m3_per_min:.0f} m3/min, "
        f"the water level reduction is {change_in_delta_h_cm:.0f} cm "
        f"for a rainfall event with a return period of {return_period} years. \n"
        f"By the 'discharge' measure, the total discharge capacity is increased to {new_discharge_capacity_mm_d:.0f} mm/day."
    )

    if input.language == "nl":
        description = description_nl
    if input.language == "en":
        description = description_en

    return DischargeOutput(
        data=data,
        description=description,
    )


def calculate_effect_discharge(input: BaseInput):
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

    effect["dH_mtr [m]"] = effect["percA [%]"].apply(
        lambda x: clcMax_discharge(x, Qd, area_open_water, area_land, pmpQ)
    )

    return effect, rainfall_per_day, volume_rain_mm, model_matrix, flow_per_hour_l_s_ha

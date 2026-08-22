"""Een systeemvraag: een bui op een selectie van gebieden die op elkaar lozen.

De enige tool die meer dan één gebied aanneemt, en hij geeft geen rij per gebied terug maar
de bindende beperking en waar hij zit. Zie `RegionOutput` voor waarom.
"""

import numpy as np
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    assumed_defaults,
    model_caveats,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.region import (
    RegionInput,
    RegionOutput,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.system import (
    BOUNDARY,
    SystemState,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.descriptions import (
    append_assumptions,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.network import simulate_network
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate
from talk_with_the_engineer.utils.logging_utils import log_tool_call


def _system_of(input: RegionInput) -> SystemState:
    known = {node.name for node in input.nodes}
    polders = []
    for node in input.nodes:
        if node.drains_to is not None and node.drains_to not in known:
            raise ModelRetry(
                f"Gebied {node.name!r} loost op {node.drains_to!r}, en dat gebied zit niet "
                "in de selectie. Voeg het toe, of laat `drains_to` weg als het buiten het "
                "systeem loost."
            )
        polders.append(
            PolderState(
                area_ha=node.area_ha,
                pct_open_water=node.percentage_open_water,
                retention_fraction=node.retention_fraction or 0.0,
                connections=(
                    Connection(
                        to=node.drains_to or OUTSIDE,
                        capacity_out_m3_per_sec=node.discharge_capacity_m3_per_sec,
                        head_max_m=node.head_max_m,
                    ),
                ),
            )
        )
    try:
        return SystemState.from_polders(
            polders, names=[node.name for node in input.nodes]
        )
    except ValueError as error:
        raise ModelRetry(
            f"Deze selectie is geen geldig afwateringssysteem: {error}"
        ) from error


def _binding_node(system, result, input):
    """Het gebied waarvan het gemaal het hardst wordt geblokkeerd op zijn eigen piekuur.

    Dat is waar de koppeling knelt. Het verschil tussen geinstalleerd en werkend vermogen op
    het beslissende uur is de grootheid die een model per gebied niet kan zien: je betaalt
    voor het eerste en je krijgt het tweede.
    """
    worst_name, worst_fraction = None, 0.0
    for index in range(system.size):
        installed = system.capacity_out_m3_per_sec[index]
        if installed <= 0 or system.downstream[index] == BOUNDARY:
            continue
        peak_hour = int(np.argmax(result.water_level_m[index]))
        working = result.exchange_m3_per_sec[index][peak_hour]
        fraction = float(max(0.0, 1.0 - working / installed))
        if fraction > worst_fraction:
            worst_name, worst_fraction = system.names[index], fraction
    return worst_name, (worst_fraction if worst_name else None)


def _coupling_effect(system, result, input, worst_index) -> float:
    """Hoeveel hoger de piek is dan wanneer dit gebied los zou zijn gerekend."""
    node = input.nodes[worst_index]
    isolated = simulate(
        PolderState(
            area_ha=node.area_ha,
            pct_open_water=node.percentage_open_water,
            retention_fraction=node.retention_fraction or 0.0,
            pump_capacity_m3_per_sec=node.discharge_capacity_m3_per_sec,
        ),
        input,
    ).dh_max_m
    return float(result.dh_max_m[worst_index] - isolated)


def _describe(input, system, result, worst_index, binding, blocked, coupling) -> str:
    worst = system.names[worst_index]
    language = input.language
    if language == "en":
        text = (
            f"Across {system.size} areas in {result.depth} topological layers, the highest "
            f"rise is {result.dh_max_m[worst_index] * 100:.0f} cm, in {worst!r}."
        )
        if coupling is not None and coupling > 0.01:
            text += (
                f" That is {coupling * 100:.0f} cm more than the same area computed on its "
                f"own, so that much is passed on from upstream."
            )
        if binding:
            text += (
                f" The coupling pinches at {binding!r}: at the hour of its own peak, "
                f"{blocked * 100:.0f} % of its installed pumping capacity was unavailable."
            )
        return text

    text = (
        f"Over {system.size} gebieden in {result.depth} topologische lagen is de hoogste "
        f"stijging {result.dh_max_m[worst_index] * 100:.0f} cm, in {worst!r}."
    )
    if coupling is not None and coupling > 0.01:
        text += (
            f" Dat is {coupling * 100:.0f} cm meer dan hetzelfde gebied los gerekend, dus "
            f"zoveel komt er van bovenstrooms bij."
        )
    if binding:
        text += (
            f" De koppeling knelt bij {binding!r}: op het uur van zijn eigen piek was "
            f"{blocked * 100:.0f} % van het geinstalleerde gemaalvermogen niet beschikbaar."
        )
    return text


@log_tool_call
async def calculate_region_given_storm(ctx, input: RegionInput) -> RegionOutput:
    """Wat doet een bui op een groep gebieden die op elkaar lozen?

    Region = systeemvraag over meerdere gebieden.
    """
    system = _system_of(input)
    result = simulate_network(system, input)

    worst_index = int(np.argmax(result.dh_max_m))
    binding, blocked = _binding_node(system, result, input)
    coupling = _coupling_effect(system, result, input, worst_index)

    assumptions = assumed_defaults(input)
    return RegionOutput(
        description=append_assumptions(
            _describe(
                input, system, result, worst_index, binding, blocked, coupling
            ),
            assumptions,
            input.language,
        ),
        node_count=system.size,
        depth=result.depth,
        converged=result.converged,
        iterations=result.iterations,
        worst_node=system.names[worst_index],
        worst_dh_m=float(result.dh_max_m[worst_index]),
        median_dh_m=float(np.median(result.dh_max_m)),
        lowest_dh_m=float(result.dh_max_m.min()),
        binding_node=binding,
        blocked_capacity_fraction=blocked,
        coupling_effect_m=coupling,
    )

"""Wateroverlast op systeemschaal: de cascade van gebieden die op elkaar lozen.

De vraag is niet "wat doet deze bui" maar "waar loopt de afvoer vast". Het proces is
DRAINAGE: neerslag komt in het ene gebied terecht, wordt afgevoerd naar het volgende, en
ergens in die keten knelt het - een gemaal dat niet weg kan wat er binnenkomt, of een
benedenstroomse stand die de bovenstroomse afvoer blokkeert. Vandaar `cascade`: het is de
keten die wordt doorgerekend, niet een gebied.

De enige tool die meer dan één gebied aanneemt, en hij geeft geen rij per gebied terug maar
de bindende beperking en waar hij zit. Zie `CascadeOutput` voor waarom.

De droge tegenhanger is `calculate_allocation_given_shortage`: daar is de schaarste de
klem en gaat het over verdelen, hier is de afvoercapaciteit de klem en gaat het over
drainage.
"""

import numpy as np
from pydantic_ai import ModelRetry

from talk_with_the_engineer.epistemics.assumptions import assumed_defaults
from talk_with_the_engineer.epistemics.caveats import model_caveats
from talk_with_the_engineer.core.connection import (
    OUTSIDE,
    Connection,
)
from talk_with_the_engineer.interface.schemas.cascade import (
    CascadeInput,
    CascadeOutput,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.system import (
    BOUNDARY,
    SystemState,
)
from talk_with_the_engineer.interface.descriptions import (
    append_assumptions,
    counted,
)
from talk_with_the_engineer.core.network import simulate_network
from talk_with_the_engineer.epistemics.uncertainty import sensitivity_of
from talk_with_the_engineer.core.transition import simulate
from talk_with_the_engineer.utils.logging_utils import log_tool_call


def _system_of(input: CascadeInput) -> SystemState:
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
                target_level_rise_m=node.target_level_rise_m,
                level_margin_m=node.level_margin_m,
                days_to_discharge=(node.days_to_discharge or input.days_to_discharge),
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


BINDING_TIE_TOLERANCE = 1e-6
"""Wanneer twee gebieden even hard geblokkeerd zijn.

Een miljoenste van het geinstalleerde vermogen. Twee polders met dezelfde opvoerhoogte op
dezelfde boezem komen exact gelijk uit; deze marge vangt de laatste bit van de iteratie op
en niet een echt verschil.
"""

BINDING_FLOOR = 1e-6
"""Onder deze fractie is er geen blokkade, alleen drijvende-komma ruis.

Dezelfde orde als `BINDING_TIE_TOLERANCE`, en om dezelfde reden: dit is de laatste bit van
de iteratie. Zonder ondergrens wordt een fractie van 1e-15 een conclusiezin die "0 %" meldt
en zichzelf dus tegenspreekt.
"""


def _binding_node(system, result, input):
    """De gebieden waarvan het gemaal het hardst wordt GEBLOKKEERD op hun eigen piekuur.

    Dat is waar de koppeling knelt: capaciteit die er staat maar die de benedenstroomse
    stand wegneemt. Je betaalt voor het geinstalleerde vermogen en je krijgt het effectieve.

    **Blokkade en niet inzet.** De maat is `1 - effectief / geinstalleerd`, met de effectieve
    capaciteit uit de derating - en nadrukkelijk niet `1 - verpompt / geinstalleerd`. Die
    tweede meet inzet: een ruim bemeten polder die op zijn piekuur weinig te verpompen heeft
    haalt zijn capaciteit niet, en dat is geen knelpunt maar ruimte. Op die maat verschijnt
    de melding juist waar een gebied stilstaat en verdwijnt hij zodra het volloopt.

    Zonder kopafhankelijkheid is de effectieve capaciteit per constructie gelijk aan de
    geinstalleerde, en dan is er geen bindende knoop - terecht, want zonder terugkoppeling
    kan een benedenstroomse stand niets blokkeren.

    Levert een LIJST en niet een naam, want de gelijke stand bestaat echt. Bij twee polders
    met dezelfde opvoerhoogte op dezelfde volle boezem staan beide gemalen volledig stil, en
    dan koos de vergelijking op `>` stil de eerste uit de selectie - terwijl de andere de
    hoogste stijging kan hebben. Er is in dit model niets dat tussen die twee kiest, en dat
    hoort in het antwoord te staan in plaats van in de volgorde van de invoer.
    """
    fractions = {}
    for index in range(system.size):
        installed = system.capacity_out_m3_per_sec[index]
        if installed <= 0 or system.downstream[index] == BOUNDARY:
            continue
        peak_hour = int(np.argmax(result.water_level_m[index]))
        # de capaciteit die op dat uur BESCHIKBAAR was, niet wat er is verpompt
        effective = result.capacity_m3_per_sec[index][peak_hour]
        fractions[system.names[index]] = float(max(0.0, 1.0 - effective / installed))

    if not fractions:
        return [], None
    worst_fraction = max(fractions.values())
    if worst_fraction <= BINDING_FLOOR:
        return [], None
    binding = [
        name
        for name, fraction in fractions.items()
        if fraction >= worst_fraction - BINDING_TIE_TOLERANCE
    ]
    return binding, worst_fraction


def _rise_above_original_datum(system, result):
    """De stijging per knoop boven het OORSPRONKELIJKE peil, dus inclusief de peilopzet.

    `NetworkResult.dh_max_m` meet boven het OPGEZETTE streefpeil van elke knoop, want dat is
    het nulpunt van de waterbalans. Een inundatienorm geldt boven het oorspronkelijke peil,
    dus de opzet hoort erbij opgeteld - precies wat `dh_total_above_original_datum_m` op de
    eenpolder-kant doet. Zonder deze optelling zou peilopzet in de cascade gratis zijn: hij
    koopt bufferdiepte en de opgesnoepte marge zou nergens te zien zijn.

    Bij knopen zonder peilopzet - en dat zijn ze allemaal zolang de beller het veld weglaat -
    is dit exact `dh_max_m`, dus bestaande antwoorden veranderen niet.
    """
    return result.dh_max_m + system.target_level_rise_m


def _coupling_effect(system, result, input, worst_index) -> float:
    """Hoeveel hoger de piek is dan wanneer dit gebied los zou zijn gerekend."""
    node = input.nodes[worst_index]
    isolated = simulate(
        PolderState(
            area_ha=node.area_ha,
            pct_open_water=node.percentage_open_water,
            retention_fraction=node.retention_fraction or 0.0,
            pump_capacity_m3_per_sec=node.discharge_capacity_m3_per_sec,
            target_level_rise_m=node.target_level_rise_m,
            level_margin_m=node.level_margin_m,
            days_to_discharge=node.days_to_discharge or input.days_to_discharge,
        ),
        input.to_storm(),
    ).dh_max_m
    # beide boven het opgezette peil, want het verschil moet de KOPPELING zijn en niet de
    # peilband: die is in beide doorrekeningen dezelfde
    return float(result.dh_max_m[worst_index] - isolated)


def _binding_phrase(binding: list[str], language: str) -> str:
    """De bindende gebieden als een opsomming, met "even hard" erbij zodra het er meer zijn.

    Een enkele naam noemen terwijl twee gemalen even hard stilstaan leest als een aanwijzing:
    "de koppeling knelt bij 'polder A'" wijst dan een gebied aan terwijl er niets is dat A
    boven B kiest.
    """
    names = [repr(name) for name in binding]
    if len(names) == 1:
        return names[0]
    joiner = " and " if language == "en" else " en "
    listed = ", ".join(names[:-1]) + joiner + names[-1]
    return (
        f"{listed} (equally hard, so this model does not choose between them)"
        if language == "en"
        else f"{listed} - even hard, dus dit model kiest daar niet tussen"
    )


def _describe(
    input, system, result, rise, worst_index, binding, blocked, coupling
) -> str:
    worst = system.names[worst_index]
    language = input.language
    if language == "en":
        text = (
            f"Across {counted(system.size, 'area', 'areas')} in "
            f"{counted(result.depth, 'topological layer', 'topological layers')}, the "
            f"highest rise is {rise[worst_index] * 100:.0f} cm, in {worst!r}."
        )
        if coupling is not None and coupling > 0.01:
            text += (
                f" That is {coupling * 100:.0f} cm more than the same area computed on its "
                f"own, so that much is passed on from upstream."
            )
        if binding:
            text += (
                f" The coupling pinches at {_binding_phrase(binding, language)}: at the "
                f"hour of its own peak, {blocked * 100:.0f} % of its installed pumping "
                f"capacity was unavailable."
            )
        return text

    text = (
        f"Over {counted(system.size, 'gebied', 'gebieden')} in "
        f"{counted(result.depth, 'topologische laag', 'topologische lagen')} is de hoogste "
        f"stijging {rise[worst_index] * 100:.0f} cm, in {worst!r}."
    )
    if coupling is not None and coupling > 0.01:
        text += (
            f" Dat is {coupling * 100:.0f} cm meer dan hetzelfde gebied los gerekend, dus "
            f"zoveel komt er van bovenstrooms bij."
        )
    if binding:
        text += (
            f" De koppeling knelt bij {_binding_phrase(binding, language)}: op het uur van "
            f"zijn eigen piek was {blocked * 100:.0f} % van het geinstalleerde "
            f"gemaalvermogen niet beschikbaar."
        )
    return text


def _worst_rise_for(variant: CascadeInput):
    """Het gemelde antwoord van deze tool bij een aangepaste bui: de hoogste stijging [m].

    Dit is wat `sensitivity_of` nodig heeft. De cascade had als enige maatregeltool geen
    `sensitivity`, terwijl er juist hier vier waarden worden aangenomen zodra de beller
    alleen een terugkeertijd opgeeft - en de bandbreedte daarop is precies wat een systeem
    van vijftig knopen onleesbaar maakt zonder.

    De hele doorrekening opnieuw en geen linearisatie, net als bij de andere tools: twee
    netwerksimulaties per aangenomen veld, en die kosten elk milliseconden.
    """
    system = _system_of(variant)
    result = simulate_network(system, variant.to_storm())
    return float(_rise_above_original_datum(system, result).max()), None


@log_tool_call
async def calculate_cascade_given_excess(ctx, input: CascadeInput) -> CascadeOutput:
    """Waar loopt de drainage vast als een groep gebieden op elkaar loost?

    Cascade = wateroverlast op systeemschaal. De keten voert af naar buiten; deze tool
    zoekt de hoogste waterstandstijging en de knoop waar de koppeling bindend wordt.
    """
    system = _system_of(input)
    result = simulate_network(system, input.to_storm())

    rise = _rise_above_original_datum(system, result)
    worst_index = int(np.argmax(rise))
    binding, blocked = _binding_node(system, result, input)
    coupling = _coupling_effect(system, result, input, worst_index)

    assumptions = assumed_defaults(input)
    sensitivity = sensitivity_of(input, _worst_rise_for)
    caveats = model_caveats(
        input,
        coupling_law=any(node.head_max_m for node in input.nodes),
        worst_rise_m=float(rise[worst_index]),
    )
    return CascadeOutput(
        description=append_assumptions(
            _describe(
                input, system, result, rise, worst_index, binding, blocked, coupling
            ),
            assumptions,
            input.language,
        ),
        assumptions=assumptions,
        sensitivity=sensitivity,
        caveats=caveats,
        node_count=system.size,
        depth=result.depth,
        converged=result.converged,
        iterations=result.iterations,
        worst_node=system.names[worst_index],
        worst_dh_m=float(rise[worst_index]),
        median_dh_m=float(np.median(rise)),
        lowest_dh_m=float(rise.min()),
        binding_node=binding[0] if binding else None,
        binding_nodes=binding,
        blocked_capacity_fraction=blocked,
        coupling_effect_m=coupling,
    )

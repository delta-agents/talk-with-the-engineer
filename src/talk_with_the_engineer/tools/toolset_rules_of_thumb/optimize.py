"""De pakketzoeker: het goedkoopste maatregelpakket dat aan twee eisen tegelijk voldoet.

`solve` is de inverse van *één* maatregel. Dit is iets anders, en die twee bewust niet in
één functie: zodra er meerdere maatregelen en meerdere eisen zijn, is het geen inverse meer
maar een optimalisatie. Zie issue #28 punt 6.

**Twee eisen, en ze delen een schaarse grootheid.** Peilopzet vergroot de voorraad en
verkleint de marge tot inundatie met exact dezelfde centimeters, dus ze zijn niet los te
optimaliseren:

    dh_total_above_original_datum_m <= inundatienorm
    retained_volume_mm              >= minimale voorraad

Dat is precies wat de demo moet laten zien. Met alleen de inundatie-eis zegt het antwoord
"altijd pompen", want afvoeren is met een lineaire prijs bij elke ambitie het goedkoopst.
Voeg de voorraadeis toe en dat houdt geen stand: afvoeren draagt niets bij aan de voorraad,
bergen aan beide, en peilopzet is de enige die voorraad direct koopt. Daarmee **ontstaat de
trits uit het model** in plaats van dat hij eroverheen wordt gelegd.

**De vorm: enumeratie buiten, continu binnen.** Vier actietypen geeft vijftien niet-lege
mixen; per mix wordt de goedkoopste maatvoering gezocht met SLSQP. Geen genetisch algoritme
en geen Bayesiaanse optimalisatie - de dimensie is vier, de doorrekening kost 0,06 ms, en
het antwoord moet uit te leggen zijn. "We enumereren de mixen en lossen de continue
hoeveelheden op tegen de twee eisen" is auditeerbaar; een black box niet.
"""

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
from scipy.optimize import minimize

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    PeilopzetAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

DEFAULT_ACTIONS = (
    VasthoudenAction(),
    BergenAction(),
    AfvoerenAction(),
    PeilopzetAction(),
)
"""De vier acties, in de volgorde van de trits met peilopzet erachter.

De volgorde is niet vrij: `apply` wordt sequentieel toegepast en bergen verandert het
landoppervlak waar vasthouden zijn fractie tegen rekent. Vasthouden eerst houdt die
conversie tegen de oorspronkelijke toestand, wat de leesbare keuze is - "30 % van het land"
betekent dan 30 % van het land dat er nu ligt.
"""

FEASIBILITY_TOLERANCE = 1e-6
NEGLIGIBLE_FRACTION = 1e-4
"""Onder deze fractie van de bovengrens is een maatvoering ruis en geen maatregel."""
GRADIENT_STEP = 1e-4


@dataclass(frozen=True)
class Constraints:
    """De twee eisen. `None` betekent: deze eis wordt niet gesteld."""

    max_dh_total_m: float | None = None
    """Inundatienorm, gemeten boven het OORSPRONKELIJKE peil - dus inclusief peilopzet."""
    min_storage_mm: float | None = None
    """Minimale voorraad onder het streefpeil, in mm over de polder."""

    @property
    def any_set(self) -> bool:
        return self.max_dh_total_m is not None or self.min_storage_mm is not None


@dataclass
class Package:
    """Een maatregelpakket met zijn maatvoering, prijs en de uitkomst ervan."""

    quantities: dict[str, float]
    cost: float
    state_after: PolderState
    dh_total_m: float
    storage_mm: float
    feasible: bool
    binding: tuple[str, ...] = field(default_factory=tuple)
    """Welke eisen precies op hun grens liggen; dat is waar de prijs vandaan komt."""


@dataclass
class OptimizeResult:
    best: Package | None
    packages: tuple[Package, ...]
    """Alle onderzochte mixen, ook de onhaalbare. Dat maakt het antwoord navolgbaar."""
    problem_infeasible: bool
    """Geen enkele mix haalt de eisen. Dit is de PROBLEM_INFEASIBLE uit `SolveStatus`."""


def _apply_all(state: PolderState, actions, quantities) -> PolderState:
    for action, quantity in zip(actions, quantities):
        state = action.at(max(float(quantity), 0.0)).apply(state)
    return state


def outcome_of(state: PolderState, storm, actions, quantities):
    """De twee uitlezingen van dezelfde doorrekening, plus de prijs.

    Eén simulatie, twee vragen - het world-modelargument zonder retoriek. `dh_total` telt de
    peilopzet mee omdat een inundatienorm boven het oorspronkelijke peil geldt en niet boven
    het opgezette.
    """
    after = _apply_all(state, actions, quantities)
    result = simulate(after, storm)
    cost = sum(
        action.at(max(float(quantity), 0.0)).cost(state) or 0.0
        for action, quantity in zip(actions, quantities)
    )
    return after, result.dh_total_above_original_datum_m, after.retained_volume_mm, cost


def _finite_difference(function, x, step=GRADIENT_STEP):
    """Centrale differenties. De gradiënt die SLSQP nodig heeft, expliciet en getest.

    Bewust geen `jac=None`: dan doet scipy voorwaartse differenties met een eigen stap, en
    dan is de gradiënt een implementatiedetail van de optimizer in plaats van iets van ons.
    Bij vier variabelen en 0,06 ms per doorrekening kost dit acht simulaties, dus een halve
    milliseconde.

    Dit is O(aantal variabelen) simulaties. Op polderschaal is dat gratis; op nationale
    schaal is het precies de reden dat de adjoint uit §7 nodig is - daar zou dit het aantal
    knopen keer een simulatie kosten in plaats van één backward pass.
    """
    x = np.asarray(x, dtype=float)
    gradient = np.zeros_like(x)
    for index in range(len(x)):
        forward, backward = x.copy(), x.copy()
        forward[index] += step
        backward[index] -= step
        gradient[index] = (function(forward) - function(backward)) / (2 * step)
    return gradient


def optimise_mix(
    state: PolderState, storm, actions, constraints: Constraints
) -> Package:
    """Zoek de goedkoopste maatvoering voor één vaste actiemix."""
    bounds = [(0.0, action.upper_bound(state)) for action in actions]
    start = np.array([0.05 * high for _low, high in bounds])

    def cost_of(x):
        return outcome_of(state, storm, actions, x)[3]

    def inundation_margin(x):
        """>= 0 als de norm gehaald wordt."""
        _after, dh_total, _storage, _cost = outcome_of(state, storm, actions, x)
        return constraints.max_dh_total_m - dh_total

    def storage_margin(x):
        _after, _dh, storage, _cost = outcome_of(state, storm, actions, x)
        return storage - constraints.min_storage_mm

    constraint_list = []
    if constraints.max_dh_total_m is not None:
        constraint_list.append(
            {
                "type": "ineq",
                "fun": inundation_margin,
                "jac": lambda x: _finite_difference(inundation_margin, x),
            }
        )
    if constraints.min_storage_mm is not None:
        constraint_list.append(
            {
                "type": "ineq",
                "fun": storage_margin,
                "jac": lambda x: _finite_difference(storage_margin, x),
            }
        )

    solution = minimize(
        cost_of,
        start,
        jac=lambda x: _finite_difference(cost_of, x),
        method="SLSQP",
        bounds=bounds,
        constraints=constraint_list,
        options={"maxiter": 200, "ftol": 1e-6},
    )
    quantities = np.clip(
        solution.x, [low for low, _ in bounds], [high for _, high in bounds]
    )
    # Een maatvoering van 0,001 ha is geen maatregel maar een restje van de zoektocht, en
    # als "vasthouden: 0,001" leest hij als een keuze. Op nul zetten en opnieuw doorrekenen,
    # zodat het gerapporteerde pakket ook echt de uitkomst is die erbij staat.
    quantities = np.where(
        quantities < NEGLIGIBLE_FRACTION * np.array([high for _, high in bounds]),
        0.0,
        quantities,
    )

    after, dh_total, storage, cost = outcome_of(state, storm, actions, quantities)
    margins = {}
    if constraints.max_dh_total_m is not None:
        margins["inundatie"] = constraints.max_dh_total_m - dh_total
    if constraints.min_storage_mm is not None:
        margins["voorraad"] = storage - constraints.min_storage_mm

    feasible = all(margin >= -FEASIBILITY_TOLERANCE for margin in margins.values())
    binding = tuple(name for name, margin in margins.items() if abs(margin) <= 1e-3)
    return Package(
        quantities={
            action.name_nl: float(quantity)
            for action, quantity in zip(actions, quantities)
        },
        cost=float(cost),
        state_after=after,
        dh_total_m=float(dh_total),
        storage_mm=float(storage),
        feasible=feasible,
        binding=binding,
    )


def optimize(
    state: PolderState,
    storm,
    constraints: Constraints,
    actions=DEFAULT_ACTIONS,
    max_mix_size: int | None = None,
) -> OptimizeResult:
    """Het goedkoopste pakket dat aan de eisen voldoet, over alle actiemixen.

    `max_mix_size` begrenst hoeveel maatregelen er tegelijk mogen worden ingezet. Standaard
    alle - dat is bij vier acties vijftien mixen en dus vijftien SLSQP-runs, samen ruim
    onder een seconde. Wordt hij gezet, dan staat er in de uitvoer welke mixen niet zijn
    onderzocht; stil begrenzen leest als "alles gedekt" terwijl dat niet zo is.
    """
    if not constraints.any_set:
        raise ValueError(
            "geef minstens een eis; zonder eis is het goedkoopste pakket altijd niets doen"
        )

    largest = max_mix_size or len(actions)
    packages = []
    for size in range(1, largest + 1):
        for mix in combinations(actions, size):
            packages.append(optimise_mix(state, storm, mix, constraints))

    feasible = [package for package in packages if package.feasible]
    best = min(feasible, key=lambda package: package.cost) if feasible else None
    return OptimizeResult(
        best=best,
        packages=tuple(packages),
        problem_infeasible=not feasible,
    )

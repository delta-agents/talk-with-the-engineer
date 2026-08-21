"""Inverse richting: welke maatvoering hoort bij een doel-waterstand?

Voorheen werd hiervoor een sweep van 101 punten uitgerekend en daarin geinterpoleerd met
`np.interp`. Dat klemt stil buiten het haalbare bereik en kost 101 doorrekeningen, ook als
er maar een antwoord nodig is. Hier wordt in plaats daarvan gezocht: eerst het optimum van
de maatregel, dan bisectie op de dalende tak.

Vormen van de responscurve, gemeten over de neerslagstatistiek:

* bergen en afvoeren zijn monotoon dalend
* vasthouden is unimodaal - eerst dalend, dan weer stijgend, met het minimum tussen 67 en
  93 % afhankelijk van de bui. Dat is modelgedrag: de vertraagde afvoer van het ene deel
  valt samen met de piek van het andere. Het staat ook zo in Ton's rekenblad.

De gulden snede dekt beide: bij een monotoon dalende functie ligt het minimum op de
bovengrens.
"""

import numpy as np
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import Action
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    LimitReason,
    OptimumKind,
    SolveResult,
    SolveStatus,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

GOLDEN_RATIO_COMPLEMENT = (np.sqrt(5.0) - 1.0) / 2.0  # 0.618...
COARSE_POINTS = 33
DH_TOLERANCE_M = 1e-4
MAX_ITERATIONS = 200


def minimise_unimodal(
    objective, low, high, coarse_points=COARSE_POINTS, tolerance=None
):
    """Zoek het minimum van `objective` op [low, high].

    Eerst een grof raster om het minimum in te sluiten, dan de gulden snede binnen dat
    interval. Het raster maakt de zoektocht robuust tegen milde afwijkingen van
    unimodaliteit; de kosten zijn verwaarloosbaar omdat een doorrekening onder een
    milliseconde blijft.
    """
    if high <= low:
        return low, objective(low)

    tolerance = tolerance or (high - low) * 1e-6

    grid = np.linspace(low, high, coarse_points)
    values = np.array([objective(x) for x in grid])
    index = int(values.argmin())

    bracket_low = grid[max(index - 1, 0)]
    bracket_high = grid[min(index + 1, coarse_points - 1)]
    best_x, best_value = float(grid[index]), float(values[index])

    left, right = bracket_low, bracket_high
    x1 = right - GOLDEN_RATIO_COMPLEMENT * (right - left)
    x2 = left + GOLDEN_RATIO_COMPLEMENT * (right - left)
    f1, f2 = objective(x1), objective(x2)

    for _ in range(MAX_ITERATIONS):
        if right - left < tolerance:
            break
        if f1 < f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - GOLDEN_RATIO_COMPLEMENT * (right - left)
            f1 = objective(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + GOLDEN_RATIO_COMPLEMENT * (right - left)
            f2 = objective(x2)

    for candidate_x, candidate_value in ((x1, f1), (x2, f2)):
        if candidate_value < best_value:
            best_x, best_value = float(candidate_x), float(candidate_value)
    return best_x, best_value


def bisect_decreasing(objective, low, high, target, tolerance=DH_TOLERANCE_M):
    """Vind `x` op [low, high] met `objective(x) == target`, voor een dalende functie."""
    value_low, value_high = objective(low), objective(high)
    if value_low <= target:
        return low
    if value_high >= target:
        return high

    for _ in range(MAX_ITERATIONS):
        middle = 0.5 * (low + high)
        value = objective(middle)
        if abs(value - target) < tolerance:
            return middle
        if value > target:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def classify_optimum(dh_at, magnitude_at_optimum, dh_min, upper_bound) -> OptimumKind:
    """Zeg wat er voorbij `magnitude_at_optimum` gebeurt.

    Alle drie de maatregelen leveren een `magnitude_at_optimum`, maar het betekent er niet
    bij alle drie hetzelfde. Vasthouden heeft een echt binnenoptimum: verder gaan maakt de
    stijging weer groter. Afvoeren daalt monotoon tot de stijging niet verder kan zakken
    en blijft daarna vlak - daar is meer capaciteit zinloos maar niet schadelijk. Dat
    verschil is niet uit het getal zelf af te lezen, en de naam "optimum" suggereert het
    verkeerde antwoord.

    Kost een extra doorrekening, op de bovengrens. Dat is verwaarloosbaar naast de
    tientallen die `minimise_unimodal` er al doet.
    """
    if magnitude_at_optimum >= upper_bound * (1 - 1e-9):
        return OptimumKind.UPPER_BOUND
    if dh_at(upper_bound) > dh_min + DH_TOLERANCE_M:
        return OptimumKind.INTERIOR
    return OptimumKind.PLATEAU


def solve(
    state: PolderState,
    storm,
    action: Action,
    target_dh_m: float,
    **simulate_kwargs,
) -> SolveResult:
    """Bepaal de maatvoering van `action` waarmee de waterstandstijging `target_dh_m` wordt.

    Levert altijd een `SolveResult`; buiten het haalbare bereik met status `INFEASIBLE` en
    de best haalbare waterstand erbij, in plaats van een stil geklemd getal.
    """

    def dh_at(magnitude):
        return simulate(
            action.at(magnitude).apply(state), storm, **simulate_kwargs
        ).dh_max_m

    dh_reference_m = simulate(state, storm, **simulate_kwargs).dh_max_m
    upper_bound = action.upper_bound(state)

    magnitude_at_optimum, dh_min = minimise_unimodal(dh_at, 0.0, upper_bound)
    optimum_kind = classify_optimum(dh_at, magnitude_at_optimum, dh_min, upper_bound)

    def _result(magnitude, status, limit_reason):
        applied = action.at(magnitude)
        return SolveResult(
            status=status,
            limit_reason=limit_reason,
            magnitude=magnitude,
            unit=action.unit,
            measure_nl=action.name_nl,
            cost=applied.cost(state),
            cost_range=applied.cost_range(state),
            state_before=state,
            state_after=applied.apply(state),
            target_dh_m=target_dh_m,
            dh_reference_m=dh_reference_m,
            dh_with_measure_m=dh_at(magnitude),
            feasible_dh_min_m=dh_min,
            feasible_dh_max_m=dh_reference_m,
            magnitude_at_optimum=magnitude_at_optimum,
            optimum_kind=optimum_kind,
        )

    if dh_reference_m <= target_dh_m:
        return _result(0.0, SolveStatus.NO_MEASURE_NEEDED, LimitReason.NONE)

    if target_dh_m < dh_min:
        # het optimum ligt binnen het bereik als de maatregel zelf uitgeput raakt, en op de
        # bovengrens als de fysieke grens eerder komt; `classify_optimum` maakt datzelfde
        # onderscheid, dus die is hier de enige bron
        limit_reason = (
            LimitReason.PHYSICAL_UPPER_BOUND
            if optimum_kind is OptimumKind.UPPER_BOUND
            else LimitReason.MEASURE_OPTIMUM
        )
        return _result(magnitude_at_optimum, SolveStatus.INFEASIBLE, limit_reason)

    magnitude = bisect_decreasing(dh_at, 0.0, magnitude_at_optimum, target_dh_m)
    return _result(magnitude, SolveStatus.EXACT, LimitReason.NONE)


def evaluate(
    state: PolderState,
    storm,
    action: Action,
    **simulate_kwargs,
) -> SolveResult:
    """Voorwaartse richting: welke waterstand hoort bij deze maatvoering?

    Levert hetzelfde model als `solve`, zodat beide richtingen hetzelfde haalbare bereik
    en dezelfde toestandsvelden rapporteren.
    """
    upper_bound = action.upper_bound(state)
    if action.magnitude > upper_bound:
        raise ModelRetry(
            f"Een maatvoering van {action.magnitude:.0f} {action.unit} is niet mogelijk "
            f"in dit watersysteem; het maximum is {upper_bound:.0f} {action.unit}."
        )

    def dh_at(magnitude):
        return simulate(
            action.at(magnitude).apply(state), storm, **simulate_kwargs
        ).dh_max_m

    dh_reference_m = simulate(state, storm, **simulate_kwargs).dh_max_m
    magnitude_at_optimum, dh_min = minimise_unimodal(dh_at, 0.0, upper_bound)
    dh_with_measure_m = dh_at(action.magnitude)

    return SolveResult(
        status=SolveStatus.EXACT,
        limit_reason=LimitReason.NONE,
        magnitude=action.magnitude,
        unit=action.unit,
        measure_nl=action.name_nl,
        cost=action.cost(state),
        cost_range=action.cost_range(state),
        state_before=state,
        state_after=action.apply(state),
        target_dh_m=None,
        dh_reference_m=dh_reference_m,
        dh_with_measure_m=dh_with_measure_m,
        feasible_dh_min_m=dh_min,
        feasible_dh_max_m=dh_reference_m,
        magnitude_at_optimum=magnitude_at_optimum,
        optimum_kind=classify_optimum(
            dh_at, magnitude_at_optimum, dh_min, upper_bound
        ),
    )

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
from pydantic import BaseModel, ConfigDict
from pydantic_ai import ModelRetry

from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AanvoerenAction,
    Action,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    FIELD_RANGES,
    Sensitivity,
    field_value_text,
    in_language,
    language_of,
    model_caveats,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    LimitReason,
    OptimumKind,
    SolveResult,
    SolveStatus,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    simulate,
    simulate_deficit,
)

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


def classify_optimum(
    dh_at, magnitude_at_optimum, dh_min, upper_bound, action=None
) -> OptimumKind:
    """Zeg wat er voorbij `magnitude_at_optimum` gebeurt.

    Alle drie de maatregelen leveren een `magnitude_at_optimum`, maar het betekent er niet
    bij alle drie hetzelfde. Vasthouden heeft een echt binnenoptimum: verder gaan maakt de
    stijging weer groter. Afvoeren daalt monotoon tot de stijging niet verder kan zakken
    en blijft daarna vlak - daar is meer capaciteit zinloos maar niet schadelijk. Dat
    verschil is niet uit het getal zelf af te lezen, en de naam "optimum" suggereert het
    verkeerde antwoord.

    Voorbemaling is een derde geval: de curve wordt vlak, maar niet omdat de waterstand
    niet lager kan - omdat het gemaal niet sneller leegmaalt. Meer marge afspreken helpt
    dan niet, een groter gemaal wel. Welk van de twee een vlak stuk is, is een modelfeit
    over de maatregel en niet uit de curve te lezen, dus zegt de actie het zelf via
    `plateau_kind`.

    Kost een extra doorrekening, op de bovengrens. Dat is verwaarloosbaar naast de
    tientallen die `minimise_unimodal` er al doet.
    """
    if magnitude_at_optimum >= upper_bound * (1 - 1e-9):
        return OptimumKind.UPPER_BOUND
    if dh_at(upper_bound) > dh_min + DH_TOLERANCE_M:
        return OptimumKind.INTERIOR
    if action is None:
        return OptimumKind.PLATEAU
    return OptimumKind(action.plateau_kind)


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
    magnitude_optimum_kind = classify_optimum(
        dh_at, magnitude_at_optimum, dh_min, upper_bound, action
    )

    def _result(magnitude, status, limit_reason):
        applied = action.at(magnitude)
        return SolveResult(
            status=status,
            limit_reason=limit_reason,
            magnitude=magnitude,
            unit=action.unit,
            measure_nl=action.name_nl,
            magnitude_before=applied.current_magnitude(state),
            share_delta_pp=applied.area_share_delta(state),
            share_of_nl=applied.share_of_nl,
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
            magnitude_optimum_kind=magnitude_optimum_kind,
        )

    if dh_reference_m <= target_dh_m:
        return _result(0.0, SolveStatus.NO_MEASURE_NEEDED, LimitReason.NONE)

    if target_dh_m < dh_min:
        # het optimum ligt binnen het bereik als de maatregel zelf uitgeput raakt, en op de
        # bovengrens als de fysieke grens eerder komt; `classify_optimum` maakt datzelfde
        # onderscheid, dus die is hier de enige bron
        limit_reason = (
            LimitReason.PHYSICAL_UPPER_BOUND
            if magnitude_optimum_kind is OptimumKind.UPPER_BOUND
            else LimitReason.MEASURE_OPTIMUM
        )
        return _result(
            magnitude_at_optimum, SolveStatus.ACTION_INFEASIBLE, limit_reason
        )

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
    optimum_kind = classify_optimum(
        dh_at, magnitude_at_optimum, dh_min, upper_bound, action
    )

    # Voorbij een BINNENoptimum is het antwoord nog steeds exact - de vraag was "wat doet
    # deze maatvoering" - maar de maatvoering is duurder en slechter dan een kleinere. Op
    # de referentiepolder betaalt 3800 ha 44 % meer dan 2645 ha voor een 5 cm hogere
    # stijging, en dat was uitsluitend af te leiden uit `magnitude_optimum_kind` naast
    # `magnitude_at_optimum` - twee velden die nergens als paar worden geintroduceerd.
    past_optimum = (
        optimum_kind is OptimumKind.INTERIOR
        and action.magnitude > magnitude_at_optimum * (1 + 1e-9)
    )

    return SolveResult(
        status=SolveStatus.EXACT,
        limit_reason=LimitReason.PAST_OPTIMUM if past_optimum else LimitReason.NONE,
        magnitude=action.magnitude,
        unit=action.unit,
        measure_nl=action.name_nl,
        magnitude_before=action.current_magnitude(state),
        share_delta_pp=action.area_share_delta(state),
        share_of_nl=action.share_of_nl,
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
        magnitude_optimum_kind=optimum_kind,
    )


class SupplySolveResult(BaseModel):
    """Uitkomst van de inverse op de droogtekant.

    Eigen type en niet `SolveResult`, om dezelfde reden als `SupplyOutput`: hier is geen
    waterstandstijging en geen haalbaar bereik daarvan, maar een uitzakking en een volume
    onvervulde vraag.
    """

    model_config = ConfigDict(frozen=True)

    status: SolveStatus
    supply_capacity_m3_per_sec: float
    state_before: PolderState
    state_after: PolderState
    demand_mm: float
    supplied_mm: float
    buffer_mm: float
    shortfall_mm: float
    drawdown_m: float
    days_until_buffer_empty: float
    available_source_volume_m3: float = float("inf")
    """Wat de bron over deze periode kon leveren [m3]; `inf` als hij onbeperkt is."""
    source_volume_used_m3: float = 0.0
    """Wat er werkelijk door de inlaat is gegaan [m3]."""
    days_until_source_empty: float = float("inf")
    """Wanneer de bron leeg is [dagen]; `inf` als hij het houdt of onbeperkt is.

    Deze drie stonden al in `DeficitResult` en bleven daar hangen. Dat kon zolang de bron
    een getal was dat de beller zelf had ingetypt - hij wist wat hij had opgegeven. Zodra het
    volume uit de droogtestatistiek komt, is het een uitkomst en niet meer een invoer, en dan
    is een antwoord dat verandert zonder te laten zien waardoor onbruikbaar.
    """


def _supply_result(state, deficit, capacity, status) -> SupplySolveResult:
    after = AanvoerenAction(
        delta_supply_capacity_m3_per_sec=capacity - state.supply_capacity_m3_per_sec
    ).apply(state)
    outcome = simulate_deficit(after, deficit)
    return SupplySolveResult(
        status=status,
        supply_capacity_m3_per_sec=capacity,
        state_before=state,
        state_after=after,
        demand_mm=outcome.demand_mm,
        supplied_mm=outcome.supplied_mm,
        buffer_mm=outcome.buffer_mm,
        shortfall_mm=outcome.shortfall_mm,
        drawdown_m=-outcome.dh_min_m,
        days_until_buffer_empty=outcome.days_until_buffer_empty,
        available_source_volume_m3=float(
            getattr(deficit, "available_source_volume_m3", float("inf"))
        ),
        source_volume_used_m3=outcome.source_volume_used_m3,
        days_until_source_empty=outcome.days_until_source_empty,
    )


def solve_supply(
    state: PolderState, deficit, tolerance_mm: float = 1e-6
) -> SupplySolveResult:
    """Bepaal de inlaatcapaciteit die het tekort dekt zonder dat er vraag overblijft.

    De onvervulde vraag daalt monotoon met de capaciteit - vastgelegd in
    `test_more_supply_is_monotonically_better` - dus bisectie volstaat en er is geen
    optimum te zoeken zoals op de natte kant. Dat verschil is echt: meer inlaat is nooit
    contraproductief, meer areaal vasthouden wel.

    Merk op dat de eigen berging alleen *tijd* koopt en geen dekking: bij een constant
    tekort is de benodigde capaciteit `vraag - berging/duur`, dus hij loopt op met de duur
    van de droogte. Daarom is `length_days` een gemelde aanname en geen detail.
    """

    def shortfall_at(capacity):
        action = AanvoerenAction(
            delta_supply_capacity_m3_per_sec=capacity - state.supply_capacity_m3_per_sec
        )
        return simulate_deficit(action.apply(state), deficit).shortfall_mm

    # De ondergrens van de zoektocht is de inlaat die er AL ligt en niet nul. Nul zou
    # betekenen dat de bestaande inlaat wordt afgebroken, en dat is geen maatregel die deze
    # tool kent - `AanvoerenAction` weigert een negatieve uitbreiding dan ook.
    existing = state.supply_capacity_m3_per_sec
    if shortfall_at(existing) <= tolerance_mm:
        return _supply_result(state, deficit, existing, SolveStatus.NO_MEASURE_NEEDED)

    upper_bound = existing + AanvoerenAction().upper_bound(state)
    if shortfall_at(upper_bound) > tolerance_mm:
        return _supply_result(
            state, deficit, upper_bound, SolveStatus.ACTION_INFEASIBLE
        )

    # Bewust geen `bisect_decreasing`: die zoekt een capaciteit waar het tekort *gelijk* aan
    # het doel is, en het tekort is nul over een heel interval in plaats van in een punt.
    # De vraag hier is de KLEINSTE capaciteit die het tekort wegwerkt, en dat is een
    # binaire zoektocht op een monotone voorwaarde. Met de gelijkheidsvorm kwam er de
    # bovengrens uit - 5 l/s/ha waar 0,46 het antwoord is - omdat de randcontrole
    # `waarde >= doel` bij doel nul al op de bovengrens aansloeg.
    low, high = existing, upper_bound
    for _ in range(MAX_ITERATIONS):
        if high - low < upper_bound * 1e-12:
            break
        middle = 0.5 * (low + high)
        if shortfall_at(middle) > tolerance_mm:
            low = middle
        else:
            high = middle
    return _supply_result(state, deficit, high, SolveStatus.EXACT)


def evaluate_supply(
    state: PolderState, deficit, capacity_m3_per_sec: float | None = None
) -> SupplySolveResult:
    """Voorwaartse richting: wat doet deze inlaatcapaciteit?

    `state` draagt de BESTAANDE inlaat en `capacity_m3_per_sec` is de totale capaciteit
    waarmee gerekend wordt, dus bestaand plus uitbreiding. Die twee uit elkaar houden is
    wat `measure.before` en `measure.delta` betekenis geeft: staan ze allebei op de totale
    inlaat, dan is de uitbreiding per constructie nul en meldt het antwoord dat er niets
    hoeft te gebeuren.
    """
    if capacity_m3_per_sec is None:
        capacity_m3_per_sec = state.supply_capacity_m3_per_sec
    return _supply_result(state, deficit, capacity_m3_per_sec, SolveStatus.EXACT)


def sensitivity_of(input, answer_for) -> list[Sensitivity]:
    """De spreiding van het antwoord over de velden die de beller heeft weggelaten.

    `answer_for(variant) -> (getal, opmerking)` is de doorrekening van de tool zelf met een
    aangepaste invoer. Dat is per tool twee regels en het houdt deze functie onwetend van
    wat "het antwoord" is - bij de inverse tools de maatvoering, bij de voorwaartse de
    waterstand.

    Alleen weggelaten velden: daar is de onzekerheid van ons. Wat de beller zelf invulde
    weet hij, en een bandbreedte eromheen zouden wij verzinnen.

    Kosten: twee doorrekeningen per veld, dus bij een kale aanroep een tiental. Op een
    inverse van 5 ms is dat een paar tienden van een seconde en het is de enige manier om
    van "dit veld doet veel" een getal te maken.
    """
    language = language_of(input)
    invalid = in_language(
        {
            "nl": "deze waarde is in dit watersysteem niet geldig",
            "en": "this value is not valid in this water system",
        },
        language,
    )
    reported = []
    for field in sorted(input.assumed_fields & set(FIELD_RANGES)):
        low_value, high_value = FIELD_RANGES[field]
        answers, notes = [], []
        for value in (low_value, high_value):
            try:
                answer, note = answer_for(input.model_copy(update={field: value}))
            except (ValueError, ModelRetry):
                answer, note = None, invalid
            answers.append(answer)
            notes.append(note)
        # Een opmerking per KOLOM. Ze stonden eerder samengevoegd in een veld `note`, met
        # een enkelvoudig "bij deze waarde" erin - en zodra beide kolommen `null` zijn,
        # wat bij `no_measure_needed` en bij `action_infeasible` gebeurt, verwees dat naar
        # twee waarden tegelijk zonder te zeggen welke welke was.
        reported.append(
            Sensitivity(
                field=field,
                # de weergave en niet de ruwe waarde: de buiduur gaat in uren in en komt in
                # dagen terug. Zie `FIELD_VALUE_TEXT`.
                low_value=field_value_text(field, low_value, language),
                high_value=field_value_text(field, high_value, language),
                low_answer=answers[0],
                high_answer=answers[1],
                low_note=notes[0],
                high_note=notes[1],
            )
        )
    return reported


def spread_of(sensitivity, reported_answer: float) -> float:
    """De grootste afstand tussen het gemelde antwoord en een rand van het bereik.

    Dit is wat `supported_digits` nodig heeft. Bewust het maximum en niet de spreiding
    tussen de randen: als het antwoord dicht bij de ene rand ligt is de afstand naar de
    andere de eerlijke maat voor hoe hard het kan bewegen.
    """
    distances = [
        abs(value - reported_answer)
        for item in sensitivity
        for value in (item.low_answer, item.high_answer)
        if value is not None
    ]
    return max(distances, default=0.0)


def inverse_answer_for(action_factory, target_field: str):
    """Bouw de `answer_for` die `sensitivity_of` nodig heeft, voor een inverse tool.

    Het gemelde antwoord van een inverse tool is de maatvoering, dus dat is wat er
    gevarieerd wordt. Een variant die een andere STATUS oplevert krijgt geen getal maar een
    opmerking: "geen maatregel nodig" is geen kleine maatvoering maar een ander antwoord, en
    het als 0 in een bereik zetten zou dat verstoppen.
    """

    def answer_for(variant):
        state = PolderState.from_water_system_input(variant)
        result = solve(state, variant, action_factory(), getattr(variant, target_field))
        language = language_of(variant)
        if result.status is SolveStatus.NO_MEASURE_NEEDED:
            return None, in_language(
                {
                    "nl": "bij deze waarde is er geen maatregel nodig",
                    "en": "at this value no measure is needed",
                },
                language,
            )
        if result.status is SolveStatus.ACTION_INFEASIBLE:
            return None, in_language(
                {
                    "nl": "bij deze waarde is het doel met deze maatregel niet haalbaar",
                    "en": "at this value the target cannot be reached with this measure",
                },
                language,
            )
        return result.magnitude, None

    return answer_for


def forward_answer_for(action_factory):
    """Idem voor een voorwaartse tool: daar is het gemelde antwoord de waterstandstijging."""

    def answer_for(variant):
        state = PolderState.from_water_system_input(variant)
        return evaluate(state, variant, action_factory()).dh_with_measure_m, None

    return answer_for


def uncertainty_for(input, answer_for, **caveat_context):
    """De spreiding en de caveats in een aanroep; wat elke tool aan zijn uitvoer hangt."""
    return sensitivity_of(input, answer_for), model_caveats(input, **caveat_context)

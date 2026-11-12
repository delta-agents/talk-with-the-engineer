"""Inverse richting: welke maatvoering hoort bij een doel-waterstand?

Dat is de inverse ONTWERPvraag en geen inverse modellering. In de hydrologie betekent invers
doorgaans het schatten van parameters uit observaties - doorlatendheid uit stijghoogtes, dus
calibratie. Hier staat de parametrisatie vast en is de maatregel de onbekende.

Er wordt GEZOCHT en niet geveegd: eerst het optimum van de maatregel, dan bisectie op de
dalende tak. Een sweep over een raster met `np.interp` ertussen zou hetzelfde antwoord
benaderen en twee dingen slechter doen - hij klemt stil buiten het haalbare bereik in
plaats van het te melden, en hij kost honderd doorrekeningen ook als er een antwoord nodig
is.

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

from talk_with_the_engineer.core.actions import (
    SupplyAction,
    Action,
)
from talk_with_the_engineer.core.exogenous import (
    UNLIMITED,
    BoundaryCondition,
    Deficit,
    Storm,
)
from talk_with_the_engineer.core.results import (
    LimitReason,
    OptimumKind,
    SolveResult,
    SolveStatus,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.transition import (
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
    storm: Storm,
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

    def solve_result(magnitude, status, limit_reason):
        applied = action.at(magnitude)
        return SolveResult(
            status=status,
            # alleen bij `EXACT` is er een doel geraakt; bij de andere statussen is de
            # maatvoering een grens of een nulmaatregel, en dan valt er niets te raken
            dh_tolerance_m=(DH_TOLERANCE_M if status is SolveStatus.EXACT else None),
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
        return solve_result(0.0, SolveStatus.NO_MEASURE_NEEDED, LimitReason.NONE)

    if target_dh_m < dh_min:
        # het optimum ligt binnen het bereik als de maatregel zelf uitgeput raakt, en op de
        # bovengrens als de fysieke grens eerder komt; `classify_optimum` maakt datzelfde
        # onderscheid, dus die is hier de enige bron
        limit_reason = (
            LimitReason.PHYSICAL_UPPER_BOUND
            if magnitude_optimum_kind is OptimumKind.UPPER_BOUND
            else LimitReason.MEASURE_OPTIMUM
        )
        return solve_result(
            magnitude_at_optimum, SolveStatus.ACTION_INFEASIBLE, limit_reason
        )

    magnitude = bisect_decreasing(dh_at, 0.0, magnitude_at_optimum, target_dh_m)
    return solve_result(magnitude, SolveStatus.EXACT, LimitReason.NONE)


def evaluate(
    state: PolderState,
    storm: Storm,
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
    # de referentiecasus (4000 ha, 3,5 % open water, gemaal 5 m3/s) betaalt 3800 ha
    # vasthouden 44 % meer dan 2645 ha voor een 5 cm hogere
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
    soil_store_mm: float = 0.0
    """De bodemvoorraad waarmee gerekend is [mm over de polder]; nul zonder bodem."""
    soil_supplied_mm: float = 0.0
    """Wat er uit de bodem is gekomen [mm over de polder]."""
    unreachable_mm: float = 0.0
    """Vraag die het bodemplafond niet doorlaat [mm over de polder]."""
    days_until_soil_empty: float = float("inf")
    """Wanneer de bodemvoorraad op is [dagen]."""
    soil_transfer_mm_per_day: float = float("inf")
    """Het bodemplafond [mm/dag over land]; `inf` zonder bodem."""
    soil_binding_link: str | None = None
    """Welke schakel het plafond zet, als dat uit een gebiedstype komt."""
    days_until_source_empty: float = float("inf")
    """Wanneer de bron leeg is [dagen]; `inf` als hij het houdt of onbeperkt is.

    Deze drie stonden al in `DeficitResult` en bleven daar hangen. Dat kon zolang de bron
    een getal was dat de beller zelf had ingetypt - hij wist wat hij had opgegeven. Zodra het
    volume uit de droogtestatistiek komt, is het een uitkomst en niet meer een invoer, en dan
    is een antwoord dat verandert zonder te laten zien waardoor onbruikbaar.
    """

    @property
    def binding_link(self) -> str | None:
        """De traagste schakel tussen de bron en de wortelzone; `None` als de vraag rond komt.

        De rangorde is die van het advies dat eruit volgt, en hij loopt van binnen naar
        buiten. Knijpt het bodemplafond af, dan helpt geen enkele hoeveelheid water erbij en
        is het antwoord onderwaterdrainage of subirrigatie. Is de bodemvoorraad binnen de
        periode op, dan helpt alleen water van buiten. Is de BRON leeg, dan is het een
        verdelingsvraag en geen kunstwerkvraag. Blijft er daarna vraag over, dan is de inlaat
        de klem, en dat is de enige van de vier waar een groter kunstwerk het antwoord is.
        """
        if self.unreachable_mm > 0.0:
            return self.soil_binding_link or "plafond_opgegeven"
        if np.isfinite(self.days_until_soil_empty) and self.soil_store_mm > 0.0:
            return "voorraad_op"
        if np.isfinite(self.days_until_source_empty):
            return "bron_leeg"
        if self.shortfall_mm > 0.0:
            return "inlaat"
        return None


def supply_result(
    state,
    deficit: Deficit,
    capacity,
    status,
    boundary: BoundaryCondition = UNLIMITED,
) -> SupplySolveResult:
    after = SupplyAction(
        delta_supply_capacity_m3_per_sec=capacity - state.supply_capacity_m3_per_sec
    ).apply(state)
    outcome = simulate_deficit(after, deficit, boundary)
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
        available_source_volume_m3=float(boundary.available_source_volume_m3),
        source_volume_used_m3=outcome.source_volume_used_m3,
        days_until_source_empty=outcome.days_until_source_empty,
        soil_store_mm=outcome.soil_store_mm,
        soil_supplied_mm=outcome.soil_supplied_mm,
        unreachable_mm=outcome.unreachable_mm,
        days_until_soil_empty=outcome.days_until_soil_empty,
        soil_transfer_mm_per_day=state.soil.transfer_mm_per_day,
        soil_binding_link=state.soil.binding_link,
    )


def solve_supply(
    state: PolderState,
    deficit: Deficit,
    tolerance_mm: float = 1e-6,
    boundary: BoundaryCondition = UNLIMITED,
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
        action = SupplyAction(
            delta_supply_capacity_m3_per_sec=capacity - state.supply_capacity_m3_per_sec
        )
        return simulate_deficit(action.apply(state), deficit, boundary).shortfall_mm

    # De ondergrens van de zoektocht is de inlaat die er AL ligt en niet nul. Nul zou
    # betekenen dat de bestaande inlaat wordt afgebroken, en dat is geen maatregel die deze
    # tool kent - `SupplyAction` weigert een negatieve uitbreiding dan ook.
    existing = state.supply_capacity_m3_per_sec
    if shortfall_at(existing) <= tolerance_mm:
        return supply_result(
            state, deficit, existing, SolveStatus.NO_MEASURE_NEEDED, boundary
        )

    upper_bound = existing + SupplyAction().upper_bound(state)
    if shortfall_at(upper_bound) > tolerance_mm:
        return supply_result(
            state, deficit, upper_bound, SolveStatus.ACTION_INFEASIBLE, boundary
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
    return supply_result(state, deficit, high, SolveStatus.EXACT, boundary)


def evaluate_supply(
    state: PolderState,
    deficit: Deficit,
    capacity_m3_per_sec: float | None = None,
    boundary: BoundaryCondition = UNLIMITED,
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
    return supply_result(
        state, deficit, capacity_m3_per_sec, SolveStatus.EXACT, boundary
    )

"""Een bui doorrekenen op een netwerk van polders.

Wat polder A wegpompt is de aanvoer van polder B. Dat is niet `capacity_out`, want het
gemaal draait alleen als er water is - precies de informatie die de klem weggooit en die
`slack` teruggeeft. Zie PLAN_UITWISSELING_EN_NETWERK.md Sec. 6.3.

Twee gevallen, en het onderscheid is of er terugkoppeling is:

* **zonder derating** is een pass per topologische diepte **exact**. Geen iteratie, geen
  tolerantie, geen convergentievraag.
* **met kopafhankelijke capaciteit** is het een vast-puntiteratie, die begint bij vrije
  afstroming en de capaciteit nooit laat stijgen. Zie de toelichting in `simulate_network`:
  dat laatste is een keuze en niet een eigenschap, want een lagere bovenstroomse uitstroom
  kan een gemaal juist deblokkeren.

Let op de richting bij een niet-geconvergeerd antwoord: de tussenliggende iteraties zijn
optimistisch over de afvoer en dus **onveilig** over de standen. Daarom rapporteert
`NetworkResult` of hij geconvergeerd is, en is er `bracket_network` voor grenzen die altijd
gelden.
"""

from dataclasses import dataclass

import numpy as np

from talk_with_the_engineer.models.modelset_rules_of_thumb.system import (
    BOUNDARY,
    SystemState,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb import simulate as core
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    HOURS_PER_DAY,
    _drainage_daily_for_storm,
    blend_retention,
    clamped_scan,
    slack_of,
    to_hourly,
)

MAX_ITERATIONS = 50
CONVERGENCE_M3_PER_SEC = 1e-10


@dataclass
class NetworkResult:
    """Uitkomst van een netwerkdoorrekening.

    `water_level_m` en `exchange_m3_per_sec` zijn (knopen x uren). `dh_max_m` is per knoop
    de grootheid waar de vuistregels op sturen.
    """

    dh_max_m: np.ndarray
    water_level_m: np.ndarray
    exchange_m3_per_sec: np.ndarray
    inflow_m3_per_sec: np.ndarray
    slack_m: np.ndarray
    iterations: int
    converged: bool
    depth: int
    """Aantal topologische lagen, en dus het aantal passes per iteratie."""

    def require_converged(self) -> "NetworkResult":
        """Gooi een fout als er niet geconvergeerd is.

        Bestaat als aparte stap omdat een niet-geconvergeerd antwoord bruikbaar is als
        ondergrens op de standen en onbruikbaar als antwoord. Wie het als antwoord wil
        gebruiken, moet die keuze opschrijven.
        """
        if not self.converged:
            raise ValueError(
                f"de pompschema's zijn na {self.iterations} iteraties niet geconvergeerd; "
                "de standen hierin zijn optimistisch over de afvoer en dus onveilig"
            )
        return self


def node_forcing(system: SystemState, storm) -> tuple[np.ndarray, np.ndarray]:
    """Eigen afvoer [m3/s] en directe neerslag [m/uur] per knoop, als (knopen x uren).

    Een bui over het hele systeem: de dagafvoerreeks hangt alleen van de bui af, dus die
    wordt een keer uitgerekend. Wat per knoop verschilt is het retentie-areaal, en dat is
    een lineaire menging - vectoriseerbaar - behalve dat de vertraagde reeks van
    `days_to_retain` afhangt. Knopen met dezelfde vertraging gaan daarom samen; dat zijn er
    in de praktijk een handvol, niet duizenden.
    """
    drainage_daily_mm, _, rainfall_on_water_mm, _ = _drainage_daily_for_storm(
        storm.return_period,
        storm.time_of_year,
        storm.length_event_hrs,
        storm.rainfall_regime,
        storm.name_rainfall_pattern,
        storm.days_to_discharge,
        True,
    )

    per_group = {}
    for days in np.unique(system.days_to_retain):
        per_group[int(days)] = blend_retention(drainage_daily_mm, int(days), 1.0)
    longest = max(len(series) for series in per_group.values())
    longest = max(longest, len(drainage_daily_mm))

    def padded(series):
        out = np.zeros(longest)
        out[: len(series)] = series
        return out

    undelayed = padded(drainage_daily_mm)

    # Tot hier is alles BOUWKANT: buistatistiek en vertragingsreeksen hangen alleen van de
    # bui af, niet van een maatregel. Die blijft numpy, en dat is precies de scheiding uit
    # BOUW_WP13_WP15.md WP15.1.
    #
    # Vanaf hier komen de maatregelen binnen - `retention_fraction` is vasthouden en
    # `area_land_ha` hangt van bergen af - dus vanaf hier is het `xp`, en wordt er niet meer
    # in een buffer geschreven. Per groep en niet per knoop: een lus over duizenden knopen is
    # precies wat de vectorisatie over de breedte moet vermijden, en hij kostte hier de helft
    # van de tijd. De stukken gaan aan het eind met `concatenate` samen en een STATISCHE
    # inverse permutatie zet ze terug in knoopvolgorde - dezelfde vorm als `_forward_pass`.
    xp = core.xp
    pieces, order = [], []
    for days, series in per_group.items():
        group = np.flatnonzero(system.days_to_retain == days)
        fraction = system.retention_fraction[group][:, None]
        pieces.append((1.0 - fraction) * undelayed + fraction * padded(series))
        order.append(group)
    inverse = np.argsort(np.concatenate(order))
    daily = xp.concatenate(pieces)[inverse]

    drainage_l_s_ha = xp.repeat(daily / HOURS_PER_DAY * 10 / 3.6, HOURS_PER_DAY, axis=1)
    runoff_m3_per_sec = drainage_l_s_ha * system.area_land_ha[:, None] * 1e-3

    # De directe neerslag is voor elke knoop dezelfde reeks - hij hangt van de bui af en niet
    # van de knoop - dus dit is een uitzending en geen buffervulling. `np.zeros` met een
    # sliced toewijzing deed hier hetzelfde, maar met mutatie.
    hourly_rain_m = to_hourly(rainfall_on_water_mm / HOURS_PER_DAY) / 1000.0
    hours = drainage_l_s_ha.shape[1]
    overlap = min(len(hourly_rain_m), hours)
    one_row = np.zeros(hours)
    one_row[:overlap] = hourly_rain_m[:overlap]
    direct_precipitation_m = xp.broadcast_to(xp.asarray(one_row), (system.size, hours))
    return runoff_m3_per_sec, direct_precipitation_m


def _forward_pass(system, levels_of_capacity, runoff, direct, factor, margin, levels):
    """Een pass van bron naar rand, met de gegeven effectieve capaciteit per knoop.

    Binnen een laag gaan alle knopen in een aanroep; het aantal passes is de diepte van de
    graaf. De aanvoer van een knoop is de SOM over alle kanten die erop uitkomen, dus een
    scatter-add en geen toewijzing: met `inflow[to] = exchange[from]` overschrijft de tweede
    bovenstroomse polder de eerste, en dat is stil verkeerd op elke graaf die geen ketting is.

    **Functioneel opgeschreven, en dat is de hele reden dat deze functie er zo uitziet.**
    Hier stonden vier buffers die per laag met `water_level[group] = ...` werden gevuld, en
    een `np.add.at` die in-place optelde. Allebei zijn het mutatie, en dat is wat een tracer
    niet aankan - het was na de derating de laatste blokkade op dit pad. Nu:

    * de lagen leveren stukken op die aan het eind met `concatenate` aan elkaar gaan, en een
      STATISCHE inverse permutatie zet ze terug in knoopvolgorde. `levels` is topologie, dus
      die permutatie is bekend voordat er gerekend wordt;
    * de aanvoer groeit met `inflow = inflow + scatter_add(...)` in plaats van in-place.

    Wat er NIET is veranderd: er wordt nog steeds per laag over een deelverzameling gerekend
    en niet over de volle breedte. Dat scheelt op 8500 knopen een factor diepte, en gemeten
    is deze vorm niet langzamer dan de vorige (0,97x). Zie issue #45 voor de metingen en voor
    waarom een incidentiematrix - de andere voor de hand liggende vorm - hier juist afvalt.
    """
    xp = core.xp
    hours = runoff.shape[1]
    inflow = xp.zeros((system.size, hours))
    heights, slacks, moves = [], [], []

    for group in levels:
        delta = (runoff[group] + inflow[group] - levels_of_capacity[group]) * factor[
            group, None
        ] + direct[group]
        height = clamped_scan(delta, -margin[group, None], np.inf)
        group_slack = slack_of(height, delta)
        moved = levels_of_capacity[group] - group_slack / factor[group, None]

        heights.append(height)
        slacks.append(group_slack)
        moves.append(moved)

        downstream = system.downstream[group]
        receiving = downstream != BOUNDARY
        # een tak op TOPOLOGIE en niet op een gerekende waarde: `system.downstream` is
        # statisch, dus deze `if` valt weg zodra er getraceerd wordt
        if receiving.any():
            inflow = inflow + core.scatter_add(
                moved[receiving], downstream[receiving], system.size
            )

    # de lagen samen bevatten elke knoop precies een keer; `argsort` van die volgorde is de
    # inverse permutatie, en hij hangt alleen van de topologie af
    order = np.concatenate(levels)
    inverse = np.argsort(order)
    return (
        xp.concatenate(heights)[inverse],
        xp.concatenate(moves)[inverse],
        inflow,
        xp.concatenate(slacks)[inverse],
    )


def derate_once(system: SystemState, capacity, water_level):
    """Een iteratie van de derating: de effectieve capaciteit gegeven de huidige standen.

    Puur en vormvast - array in, array uit, geen tak op een arraywaarde en geen mutatie van
    de toestand. Dat is niet alleen netjes: het is precies de deelverzameling die een tracer
    aankan, en daarmee de laatste stap om het NETWERKpad differentieerbaar te kunnen maken.
    Zie `simulate_network` voor het stopbeleid, dat hier bewust buiten staat.

    Twee dingen zijn hier anders opgeschreven dan in de lus waar deze functie uit komt, en
    allebei om dezelfde reden:

    * de benedenstroomse stand komt via `where` in plaats van via een toewijzing op een
      boolean masker. `downstream_level[receiving] = ...` is in-place mutatie met fancy
      indexing, en dat vertaalt niet - de randknopen krijgen nu een dummy-index waarvan de
      waarde daarna wordt weggemaskeerd;
    * de deling door `head_max_m` gebeurt op een noemer die nooit nul is. Een knoop zonder
      kopafhankelijkheid heeft `head_max_m = inf`, dus de breuk is nul en de klem geeft 1.

    `minimum` en niet de ruwe derating, en dat is een keuze met gevolgen.

    Het plan (PLAN_TOOLS_REFACTOR.md Sec. 8.3) stelt dat de reeks pompschema's van nature
    monotoon daalt. Dat argument is niet rond: een lagere bovenstroomse uitstroom verlaagt de
    benedenstroomse stand, en dat kan een gemaal juist *deblokkeren* - de capaciteit gaat dan
    weer omhoog. Een ruwe vast-puntiteratie kan daarop oscilleren.

    Door de capaciteit nooit te laten stijgen is de reeks monotoon dalend per constructie,
    begrensd door nul, en dus convergent zonder stabiliteitsvoorwaarde. De prijs is dat het
    antwoord conservatief is over de afvoer - een gemaal dat onderweg is geblokkeerd blijft
    geblokkeerd - en dus veilig over de standen. Dat is een keuze en geen bewijs.

    Diezelfde constructie maakt de stap **idempotent op zijn vaste punt**: staat de reeks
    stil, dan blijft hij stil. Daar leunt het vaste budget van `simulate_network` op.
    """
    # `core.xp` en niet een geimporteerde `xp`, en dat is geen stijlkwestie. De schakelaar
    # werkt door `simulate.xp` te HERBINDEN; een `from ... import xp` legt de backend vast op
    # het moment van importeren en zou die herbinding stil missen - de functie bleef dan op
    # numpy staan terwijl de rest van de kern was omgezet. Via de module wordt hij bij elke
    # aanroep opnieuw opgezocht.
    xp = core.xp
    receiving = system.downstream != BOUNDARY
    # een geldige index voor iedereen; de randknopen worden hierna weggemaskeerd
    safe_index = xp.where(receiving, system.downstream, 0)
    downstream_level = xp.where(receiving[:, None], water_level[safe_index], 0.0)
    derated = system.capacity_out_m3_per_sec[:, None] * xp.clip(
        1.0 - downstream_level / system.head_max_m[:, None], 0.0, 1.0
    )
    return xp.minimum(capacity, derated)


def simulate_network(
    system: SystemState,
    storm,
    max_iterations: int = MAX_ITERATIONS,
    iterations: int | None = None,
) -> NetworkResult:
    """Reken een bui door op een netwerk van polders.

    Twee stopbeleiden op dezelfde dynamica, en ze horen hetzelfde antwoord te geven:

    * `iterations=None` (standaard): itereren tot de derating stilstaat. Snel, en het gedrag
      dat er altijd was.
    * `iterations=n`: precies `n` keer `derate_once`, zonder uitgangstest.

    **Waarom die tweede bestaat.** De uitgangstest is een `if` op een arraywaarde, en dat is
    de enige constructie in het netwerkpad die een tracer niet aankan - in JAX wordt het
    `lax.while_loop`, en die is niet reverse-mode differentieerbaar. Een lus met een vast
    aantal stappen rolt wel uit. Deze variant is dus de vorm die later differentieerbaar kan
    zijn, en hij is vandaag gewoon numpy: er komt geen afhankelijkheid bij.

    **Waarom hij hetzelfde antwoord geeft.** `derate_once` is idempotent op zijn vaste punt -
    zie daar - dus zodra de reeks stilstaat verandert extra itereren niets. Zolang het budget
    ruim genoeg is, is het antwoord bit voor bit gelijk aan dat van de adaptieve variant.
    `test_a_fixed_budget_gives_the_same_answer` legt dat vast, en
    `test_the_iteration_budget_is_not_tight` bewaakt dat het budget ruim genoeg blijft.

    Gemeten: twee iteraties op een platte selectie, en op een diepe ketting loopt het mee met
    de diepte tot ongeveer negen en dan niet verder - ook niet bij diepte twintig. Het budget
    schaalt dus niet met de netwerkgrootte.
    """
    runoff, direct = node_forcing(system, storm)
    factor = system.metres_per_m3_per_sec
    margin = system.level_margin_m
    levels = system.topological_levels()

    capacity = system.capacity_out_m3_per_sec.astype(float).copy()
    capacity = np.repeat(capacity[:, None], runoff.shape[1], axis=1)

    # Het stopbeleid is een keuze op een STATISCHE waarde - hoeveel iteraties - en niet op
    # een arraywaarde. Daarom staat deze tak een tracer niet in de weg: hij valt weg bij het
    # samenstellen, waarna er een lus met een vast aantal stappen overblijft.
    if iterations is not None:
        performed = 0
        for _ in range(iterations):
            water_level, exchange, inflow, slack = _forward_pass(
                system, capacity, runoff, direct, factor, margin, levels
            )
            if not system.has_derating:
                break
            capacity = derate_once(system, capacity, water_level)
            performed += 1
        else:
            # de laatste doorrekening hoort bij de laatst bijgewerkte capaciteit
            water_level, exchange, inflow, slack = _forward_pass(
                system, capacity, runoff, direct, factor, margin, levels
            )
        return NetworkResult(
            dh_max_m=water_level.max(axis=1),
            water_level_m=water_level,
            exchange_m3_per_sec=exchange,
            inflow_m3_per_sec=inflow,
            slack_m=slack,
            iterations=performed,
            converged=True,
            depth=len(levels),
        )

    previous = None
    iterations = 0
    converged = True
    while True:
        water_level, exchange, inflow, slack = _forward_pass(
            system, capacity, runoff, direct, factor, margin, levels
        )
        if not system.has_derating:
            break

        updated = derate_once(system, capacity, water_level)

        iterations += 1
        if (
            previous is not None
            and np.abs(updated - previous).max() < CONVERGENCE_M3_PER_SEC
        ):
            break
        previous, capacity = updated, updated
        if iterations >= max_iterations:
            converged = False
            break

    return NetworkResult(
        dh_max_m=water_level.max(axis=1),
        water_level_m=water_level,
        exchange_m3_per_sec=exchange,
        inflow_m3_per_sec=inflow,
        slack_m=slack,
        iterations=iterations,
        converged=converged,
        depth=len(levels),
    )


def levels_from(runoff, inflow, capacity, factor, margin) -> np.ndarray:
    """De waterstanden bij een gegeven aanvoer en capaciteit, alle knopen in een scan.

    Geen topologie nodig: de aanvoer is hier gegeven in plaats van berekend. Dat maakt hem
    geschikt voor de grenzen in `bracket_network`, waar juist de aanvoer wordt vastgezet.
    """
    delta = (runoff + inflow - capacity) * factor[:, None]
    return clamped_scan(delta, -margin[:, None], np.inf)


def bracket_network(system: SystemState, storm) -> tuple[np.ndarray, np.ndarray]:
    """Veilige onder- en bovengrens op de piekstanden, in twee scans en zonder iteratie.

    Is die klem smal genoeg om de beslissing te nemen, dan hoeft er niet geitereerd te
    worden - en hij geldt ook als de iteratie niet convergeert.

    **Correctie op PLAN_TOOLS_REFACTOR.md Sec. 8.3.** Daar staat dat vrije afstroming een
    ondergrens op de standen geeft en volledig geblokkeerd een bovengrens. Dat klopt voor
    een knoop zonder bovenstroomse buren en niet voor de rest, want vrije afstroming
    maximaliseert ook de *aanvoer* van benedenstrooms. Twee effecten in tegengestelde
    richting, dus geen van beide configuraties is een grens.

    De stand van een knoop stijgt met de aanvoer en daalt met de eigen capaciteit, en
    derating kan capaciteiten alleen verlagen. De grenzen zijn dus gemengd:

    * **ondergrens**: geen aanvoer, eigen gemaal op volle capaciteit;
    * **bovengrens**: de aanvoer van vrije afstroming, want meer kan het niet zijn, en het
      eigen gemaal uit.

    De bovengrens is ruim - een gemaal dat helemaal niet draait - maar hij is geldig, en dat
    is hier het punt.
    """
    runoff, direct = node_forcing(system, storm)
    factor = system.metres_per_m3_per_sec
    margin = system.level_margin_m
    levels = system.topological_levels()
    hours = runoff.shape[1]

    free_capacity = np.repeat(
        system.capacity_out_m3_per_sec[:, None].astype(float), hours, axis=1
    )
    # vrije afstroming geeft de maximale uitstroom, en dus de maximale aanvoer
    _, _, max_inflow, _ = _forward_pass(
        system, free_capacity, runoff, direct, factor, margin, levels
    )

    lowest = levels_from(
        runoff + direct / factor[:, None],
        np.zeros_like(runoff),
        free_capacity,
        factor,
        margin,
    )
    highest = levels_from(
        runoff + direct / factor[:, None],
        max_inflow,
        np.zeros_like(free_capacity),
        factor,
        margin,
    )
    return lowest.max(axis=1), highest.max(axis=1)

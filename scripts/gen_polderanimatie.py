"""Genereert het @keyframes-blok van de polderanimaties uit de rekenkern.

Twee kanten, één kern met de klem gespiegeld:

* NAT   een bui van acht dagen, T=10. Het peil stijgt door de norm heen en de
        watergang zwelt buiten zijn oevers: `polderpeil`, `poldergemaal`,
        `polderregen`, `polderinundatie`.
* DROOG een neerslagtekort over het groeiseizoen, T=10 uit STOWA 2025-23. Het
        peil zakt door de peilband naar de bodem en de watergang krimpt:
        `polderdroogte`, `polderdorst`.

Uitvoer gaat naar stdout en hoort tussen de twee GEGENEREERD-bakens in style.css.
Zie de README onder "De animatie".
"""

import sys

sys.path.insert(0, "src")
import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    OUTSIDE,
    Connection,
    single_pump_connection,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import (
    NO_SOIL,
    simulate,
    simulate_deficit,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.utils_drought import (
    cumulative_deficit_mm,
)

NORM_CM = 30.0
N = 34  # stops: vloeiend genoeg, en nog te lezen in de CSS
KANAAL = 0.05  # halve breedte van de watergang, in plaateenheden
# Halve breedte van de overstroming bij de piek. ILLUSTRATIEF: het model geeft
# een stand en geen inundatiecontour. Zie de README.
OVERSTROMING = 0.20
COS30, SIN30 = 0.8660254, 0.5

# ── de droge kant ──────────────────────────────────────────────────────────
SEIZOEN_DAGEN = 183  # 1 april tot 1 oktober, het venster van de statistiek
REGIO = "Aa_en_Maas"  # een van de eenentwintig; noord-zuid scheelt 23 %
SCENARIO = "Referentie"  # huidig klimaat
HERHAALTIJD = 10
BAND_CM = 30.0  # peilopzet 20 + peilmarge 10; zonder band is er niets te zien
# Hoe smal de watergang wordt als het peil op de bodem van de band staat.
# ILLUSTRATIEF, net als de breedte van de overstroming: het model geeft een
# stand, en hoe breed een watergang bij die stand is hangt aan zijn profiel.
KRIMP = 0.45


class Bui:
    return_period = 10.0
    time_of_year = "summer"
    length_event_hrs = 192.0
    rainfall_regime = "R"
    name_rainfall_pattern = "p1c"
    days_to_discharge = 2


state = PolderState(
    area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
)
r = simulate(state, Bui())

peil = np.asarray(r.water_level_m) * 100.0  # cm
pomp = np.asarray(r.pumped_m3_per_sec) / 1.5  # fractie van de capaciteit
regen = np.repeat(np.asarray(r.rainfall_per_day_mm), 24)[: len(peil)]
regen = np.pad(regen, (0, max(0, len(peil) - len(regen))))
piek = float(peil.max())
idx = np.linspace(0, len(peil) - 1, N).astype(int)


def blok(naam, waarden, vorm):
    regels = [f"@keyframes {naam} {{"]
    for k, j in enumerate(idx):
        regels.append(f"  {k / (N - 1) * 100:.3g}% {{ {vorm(float(waarden[j]))} }}")
    regels.append("}")
    return "\n".join(regels)


def inundatie_matrix(h_cm: float) -> str:
    """Een schaling LANGS de watergang-as, uitgedrukt als schermmatrix.

    De axonometrische projectie is lineair, dus `y` schalen om de hartlijn van de
    watergang is op het scherm ook een lineaire afbeelding. Met M de projectie is
    dat M · diag(1, k) · M⁻¹, en dat werkt uit tot

        [[(1+k)/2,              cos30/sin30 · (1-k)/2],
         [sin30/cos30 · (1-k)/2, (1+k)/2              ]]

    onafhankelijk van de plaatgrootte. Daarom kan dit gewoon in CSS: één matrix
    per stop, met `transform-box: fill-box` zodat het middelpunt de hartlijn is.
    """
    over = max(0.0, h_cm - NORM_CM) / max(piek - NORM_CM, 1e-9)
    k = 1.0 + (OVERSTROMING / KANAAL - 1.0) * min(over, 1.0)
    a = (1 + k) / 2
    b = SIN30 / COS30 * (1 - k) / 2
    c = COS30 / SIN30 * (1 - k) / 2
    return f"transform: matrix({a:.4f}, {b:.4f}, {c:.4f}, {a:.4f}, 0, 0);"


# ── de droge doorrekening ──────────────────────────────────────────────────
tekort_mm = cumulative_deficit_mm(REGIO, SCENARIO, HERHAALTIJD)
per_dag = tekort_mm / SEIZOEN_DAGEN


class Tekort:
    deficit_mm_per_day = per_dag
    length_days = SEIZOEN_DAGEN


droge_polder = PolderState(
    area_ha=1000,
    pct_open_water=5.0,
    connections=(
        Connection(to=OUTSIDE, capacity_out_m3_per_sec=1.5, capacity_in_m3_per_sec=0.0),
    ),
    target_level_rise_m=0.20,
    level_margin_m=0.10,
)
d = simulate_deficit(droge_polder, Tekort(), NO_SOIL)
stand = np.asarray(d.water_level_m) * 100.0  # cm, negatief
idx_droog = np.linspace(0, len(stand) - 1, N).astype(int)


def blok_droog(naam, waarden, vorm):
    regels = [f"@keyframes {naam} {{"]
    for k, j in enumerate(idx_droog):
        regels.append(f"  {k / (N - 1) * 100:.3g}% {{ {vorm(float(waarden[j]))} }}")
    regels.append("}")
    return "\n".join(regels)


def krimp_matrix(h_cm: float) -> str:
    """Dezelfde afbeelding als de overstroming, met k KLEINER dan een.

    Nat zwelt de watergang buiten zijn oevers, droog krimpt hij erbinnen. Eén
    formule, k aan weerszijden van een - dat is "een kern, klem gespiegeld" op
    het scherm.
    """
    diep = min(max(-h_cm, 0.0) / BAND_CM, 1.0)
    k = 1.0 - (1.0 - KRIMP) * diep
    a = (1 + k) / 2
    b = SIN30 / COS30 * (1 - k) / 2
    c = COS30 / SIN30 * (1 - k) / 2
    return f"transform: matrix({a:.4f}, {b:.4f}, {c:.4f}, {a:.4f}, 0, 0);"


print("/* ── GEGENEREERD — niet met de hand bijwerken ─────────────────────────")
print(f"   Uit de rekenkern. Nat: een bui van acht dagen, T=10, piek {piek:.1f} cm")
print(f"   tegen een norm van {NORM_CM:.0f} cm. Droog: {tekort_mm:.0f} mm over")
print(f"   {SEIZOEN_DAGEN} dagen ({REGIO}, {SCENARIO}, T={HERHAALTIJD}), een band van")
print(f"   {BAND_CM:.0f} cm, buffer leeg na {d.days_until_buffer_empty:.1f} dagen.")
print("   Regenereren: python3 scripts/gen_polderanimatie.py — zie de README. */")
print()
print(blok("polderpeil", peil, lambda v: f"transform: scaleY({max(v, 0) / piek:.4f});"))
print()
print(
    blok(
        "poldergemaal",
        pomp,
        lambda v: f"opacity: {0.12 + 0.88 * min(max(v, 0), 1):.3f};",
    )
)
print()
regen_top = float(regen.max())
print(
    blok(
        "polderregen", regen, lambda v: f"opacity: {min(max(v, 0) / regen_top, 1):.3f};"
    )
)
print()
print(blok("polderinundatie", peil, inundatie_matrix))
print()
print(blok_droog("polderdroogte", stand, krimp_matrix))
print()
# Het land droogt op naar rato van het CUMULATIEVE tekort, niet van de stand:
# de stand staat na tien dagen al op de bodem en daarna verandert er niets meer,
# terwijl het tekort de hele zomer doorloopt.
print(
    blok_droog(
        "polderdorst",
        np.arange(len(stand)),
        lambda v: f"opacity: {min(v / max(len(stand) - 1, 1), 1) * 0.55:.3f};",
    )
)
print()
print("/* ── einde GEGENEREERD ─────────────────────────────────────────────── */")

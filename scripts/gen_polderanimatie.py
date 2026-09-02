"""Genereert het @keyframes-blok van de polderanimaties uit de rekenkern.

Uitvoer gaat naar stdout en hoort tussen de twee GEGENEREERD-bakens in style.css.
Zie de README onder "De animatie".
"""

import sys

sys.path.insert(0, "src")
import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    single_pump_connection,
)
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

NORM_CM = 30.0
N = 34  # stops: vloeiend genoeg, en nog te lezen in de CSS
KANAAL = 0.05  # halve breedte van de watergang, in plaateenheden
# Halve breedte van de overstroming bij de piek. ILLUSTRATIEF: het model geeft
# een stand en geen inundatiecontour. Zie de README.
OVERSTROMING = 0.20
COS30, SIN30 = 0.8660254, 0.5


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


print("/* ── GEGENEREERD — niet met de hand bijwerken ─────────────────────────")
print("   Uit de rekenkern: de referentiepolder onder een bui van acht dagen met")
print(f"   een herhaaltijd van tien jaar. Piek {piek:.1f} cm, norm {NORM_CM:.0f} cm.")
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
print("/* ── einde GEGENEREERD ─────────────────────────────────────────────── */")

"""Genereert de overschrijdingsfrequentielijnen: waterstand tegen terugkeertijd.

Het huisidioom van de waterveiligheid - een frequentielijn is een reeks hoogtes
met hun overschrijdingsfrequentie. Hier per maatregel een lijn, zodat je ziet
dat het effect NIET constant is over de terugkeertijd: afvoeren verzadigt,
bergen blijft doorgroeien, en peilopzet maakt het overal even veel slechter.

De grootheid op de y-as is de stijging boven het OORSPRONKELIJKE peil, dus
inclusief peilopzet - dat is de grootheid waar de inundatienorm over gaat.

Uitvoer: SVG-padjes voor de figuur `frequentielijn` in presentatie.js.
"""

import sys

sys.path.insert(0, "src")
import numpy as np
from talk_with_the_engineer.models.modelset_rules_of_thumb.actions import (
    AfvoerenAction,
    BergenAction,
    VasthoudenAction,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.connection import (
    single_pump_connection,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.state import PolderState
from talk_with_the_engineer.tools.toolset_rules_of_thumb.simulate import simulate

NORM_CM = 30.0
T_MIN, T_MAX = 1.0, 100.0  # twee decaden; alle kruisingen liggen onder T=40
PIEK_MAX = 100.0
# Het kader is kleiner dan het hele vlak: onder de grafiek staat de polder in
# 2,5D, zodat te zien is WAARMEE gerekend wordt - en zodat elke maatregel op
# dezelfde beat boven een lijn en beneden een ingreep laat zien.
X0, X1, Y0, Y1 = 96, 520, 40, 182

# De herhaaltijden die de statistiek zelf bijhoudt, binnen het venster.
T = np.array([1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0, 100.0])


def bui(t):
    class B:
        return_period = float(t)
        time_of_year = "summer"
        length_event_hrs = 192.0
        rainfall_regime = "R"
        name_rainfall_pattern = "p1c"
        days_to_discharge = 2

    return B()


s0 = PolderState(
    area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
)


def scherm(t, piek):
    x = X0 + (X1 - X0) * (np.log10(t) - np.log10(T_MIN)) / (
        np.log10(T_MAX) - np.log10(T_MIN)
    )
    y = Y1 - (Y1 - Y0) * min(max(piek, 0) / PIEK_MAX, 1.0)
    return x, y


def veilig_tot(hoogten):
    """Tot welke terugkeertijd blijft deze lijn onder de norm?

    Log-lineair interpoleren tussen de twee omliggende herhaaltijden, want de as
    is logaritmisch in T en lineair interpoleren zou daar systematisch naast
    zitten.
    """
    onder = hoogten <= NORM_CM
    if onder.all():
        return f"> {T_MAX:.0f}"
    if not onder[0]:
        return f"< {T_MIN:.0f}"
    i = int(np.argmax(~onder))
    f = (NORM_CM - hoogten[i - 1]) / (hoogten[i] - hoogten[i - 1])
    t = 10 ** (np.log10(T[i - 1]) + f * (np.log10(T[i]) - np.log10(T[i - 1])))
    return f"{t:.0f}"


# Peilopzet is eruit: hij gaat omhoog en dat leidt af van de vraag die deze
# figuur stelt, namelijk wat een maatregel je aan bescherming oplevert.
varianten = [
    ("geen", None),
    ("bergen", BergenAction().at(10)),
    ("vasthouden", VasthoudenAction().at(708)),
    ("afvoeren", AfvoerenAction().at(0.5)),
]

print(f"// y-as 0..{PIEK_MAX:.0f} cm, x-as T={T_MIN:.0f}..{T_MAX:.0f} (log)")
print(f"// norm op y={Y1 - (Y1 - Y0) * NORM_CM / PIEK_MAX:.1f}")
for t in (1, 10, 100):
    print(f"// T={t:<4d} op x={scherm(t, 0)[0]:.1f}")
for naam, a in varianten:
    s = a.apply(s0) if a else s0
    h = np.array(
        [(simulate(s, bui(t)).dh_max_m + s.target_level_rise_m) * 100 for t in T]
    )
    xy = [scherm(t, p) for t, p in zip(T, h)]
    pad = "M" + " L".join(f"{p[0]:.1f} {p[1]:.1f}" for p in xy)
    print(f"\n// {naam}: T=10 geeft {h[3]:.1f} cm, veilig tot T={veilig_tot(h)}")
    print(f"//   eindpunt {xy[-1][0]:.1f} {xy[-1][1]:.1f}")
    print(f'{naam}: "{pad}",')
    if naam == "geen":
        # De losse runs: één doorrekening per herhaaltijd, vóór ze een lijn zijn.
        print("// runs: " + " ".join(f"{x:.0f},{y:.0f}" for x, y in xy))

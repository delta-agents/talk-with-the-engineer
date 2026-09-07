"""Reproduceert de pakkettabel uit de resultatensectie van de presentatie.

Print de vijf rijen exact zoals ze in `talk/mdp-presentatie/inhoud.js` staan,
zodat elk bedrag op het scherm met één commando na te rekenen is.

De pakketzoeker enumereert de niet-lege actiemixen en lost per mix de continue
maatvoering op tegen de eisen. Er zit dus GEEN toeval in: dezelfde invoer geeft
hetzelfde pakket.

Let op de laatste kolom. `peilopzet` heeft geen prijs in euro's - hij kost
drooglegging - dus zodra hij in een pakket zit, is het gerapporteerde bedrag te
LAAG. Dat staat ook zo op het scherm.
"""

import sys

sys.path.insert(0, "src")
from talk_with_the_engineer.core.connection import (
    single_pump_connection,
)
from talk_with_the_engineer.core.state import PolderState
from talk_with_the_engineer.core.package import (
    Constraints,
    optimize,
)


class Bui:
    """De referentiebui: acht dagen, herhaaltijd tien jaar, zomer."""

    return_period = 10.0
    time_of_year = "summer"
    length_event_hrs = 192.0
    rainfall_regime = "R"
    name_rainfall_pattern = "p1c"
    days_to_discharge = 2


# De referentiepolder: 1000 ha, 5 % open water, gemaal 1,5 m3/s.
state = PolderState(
    area_ha=1000, pct_open_water=5.0, connections=single_pump_connection(1.5)
)

EISEN = [
    ("norm 30 cm", dict(max_dh_total_m=0.30)),
    ("norm 20 cm", dict(max_dh_total_m=0.20)),
    ("norm 30 cm + voorraad 10 mm", dict(max_dh_total_m=0.30, min_storage_mm=10.0)),
    ("norm 30 cm + voorraad 15 mm", dict(max_dh_total_m=0.30, min_storage_mm=15.0)),
    ("norm 20 cm + voorraad 15 mm", dict(max_dh_total_m=0.20, min_storage_mm=15.0)),
]

EENHEID = {
    "vasthouden": "ha land",
    "bergen": "ha",
    "afvoeren": "m3/s",
    "aanvoeren": "m3/s",
    "peilopzet": "m",
}

print(f"{'eis':30s} {'kosten':>12s}  pakket")
print("-" * 78)
for label, eisen in EISEN:
    p = optimize(state, Bui(), Constraints(**eisen)).best
    inzet = ", ".join(
        f"{naam} {hoeveel:.3g} {EENHEID[naam]}"
        for naam, hoeveel in p.quantities.items()
        if hoeveel > 1e-9
    )
    prijsloos = (
        " [bedrag te LAAG: " + ", ".join(p.priceless) + " zonder prijs]"
        if p.priceless
        else ""
    )
    print(f"{label:30s} {p.cost / 1e6:9.2f} mln  {inzet}{prijsloos}")
    print(
        f"{'':30s} {'':12s}  piek {p.dh_total_m * 100:.1f} cm, "
        f"voorraad {p.storage_mm:.1f} mm, bindend: {', '.join(p.binding)}"
    )

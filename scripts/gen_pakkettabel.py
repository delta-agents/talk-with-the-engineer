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
from talk_with_the_engineer.core.reference import (
    REFERENCE_POLDER,
    REFERENCE_STORM,
)
from talk_with_the_engineer.core.package import (
    Constraints,
    optimize,
)


state = REFERENCE_POLDER

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
    p = optimize(state, REFERENCE_STORM, Constraints(**eisen)).best
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

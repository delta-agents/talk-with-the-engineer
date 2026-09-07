"""Genereert de responsecurve van bergen, en de twee lezingen ervan.

Dit is de plaat bij `T`. Eén kromme - hoeveel hectare open water tegen hoe hoog
de piek komt - en twee manieren om hem te lezen:

* HEEN  geef de maatregel, lees de stand. Dat is `simulate`.
* TERUG geef de stand die je wilt, lees de maatregel. Dat is `solve`, en die is
        exact: bisectie op een monotone tak, geen zoektocht in het duister.

De twee getallenvoorbeelden komen uit diezelfde twee functies, zodat wat op het
scherm staat te reproduceren is met twee regels code.

Uitvoer gaat naar stdout en hoort in `transitiePaneel` in teken/schema.js.
"""

import sys

sys.path.insert(0, "src")


# Het kader van het onderste paneel in `transitiePaneel`. X0 en X1 zijn zo
# gekozen dat de plot op het scherm precies onder die van de statistiekplaat bij
# `E` valt: die staat op 96..520 in een viewBox van 660, deze op 85..592 in een
# viewBox van -30..760, en beide worden op hun breedte uitgetekend.
X0, X1, Y0, Y1 = 85.0, 592.0, 268.0, 408.0
HA_MAX = 80.0  # hectare open water erbij, over de volle breedte
PIEK_MAX = 40.0  # centimeter, over de volle hoogte

HEEN_HA = 40.0  # het voorbeeld heen: deze maatregel, welke stand?
TERUG_CM = 30.0  # het voorbeeld terug: de inundatienorm, welke maatregel?

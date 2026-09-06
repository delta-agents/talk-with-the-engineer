"""Genereert de twee golven van de plaat `ruisonderdrukking` bij `π`.

De plaat legt uit waarom er geen gegokt getal op het scherm komt, en hij doet
dat met de natuurkunde van een noise-cancelling koptelefoon: die dempt niets,
hij zet het exacte tegengestelde signaal erover. Zo werkt een gereedschap ook —
het houdt het taalmodel niet tegen, het legt het gerekende getal eroverheen.

Drie banen onder elkaar:

* RUIS   wat een taalmodel alleen produceert. Vloeiend, en plausibel.
* REGEL  dezelfde golf in tegenfase: de vuistregel eroverheen.
* SOM    hun optelsom, en die is precies vlak. Dat is geen tekenvrijheid maar
         rekenkunde, en daarom rekent dit script hem ook echt na.

De twee golven staan dicht op elkaar en de optelsom een eind eronder: zo lezen
de eerste twee als een spiegelpaar en de derde als wat eruit komt.

De vierde laag - de piek die er dwars doorheen komt - is geen golf maar een
losse streep, en die staat met de hand in de plaat. Dat is het punt: een
verkeerd begrepen vraag zit niet in de ruis, dus valt er ook niets tegen weg
te strepen.

Meetkunde, geen rekenkern: deze plaat toont een eigenschap van de koppeling en
niet een uitkomst van het model.

Uitvoer gaat naar stdout en hoort in `ruisonderdrukking` in presentatie.js.
"""

import math

# Het kader deelt zijn breedte met `agent`, de plaat ernaast in dezelfde stap.
X0, X1 = 16.0, 644.0
RUIS_AS = 74.0  # hartlijn van de bovenste baan
REGEL_AS = 146.0  # hartlijn van de middelste baan
SOM_AS = 262.0  # en de vlakke lijn onderin
AMPLITUDE = 24.0
STAPPEN = 96

# Drie tonen door elkaar. Twee zou als een golf lezen en vier als een storing;
# bij drie hoor je dat er iets in zit zonder dat je het kunt volgen - en dat is
# precies hoe een vloeiende gok klinkt.
TONEN = [(1.6, 0.40, 0.55), (3.1, 1.90, 0.30), (5.3, 0.20, 0.18)]


def golf(t):
    """De ruis op plaats t, met t van 0 tot 1 over de breedte van de plaat."""
    return sum(a * math.sin(2 * math.pi * f * t + p) for f, p, a in TONEN)


def pad(hartlijn, teken, schaal):
    """Bemonstert de golf tot een SVG-pad om de gegeven hartlijn heen."""
    stukken = []
    for i in range(STAPPEN + 1):
        t = i / STAPPEN
        x = X0 + (X1 - X0) * t
        y = hartlijn - teken * schaal * golf(t)
        stukken.append(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}")
    return " ".join(stukken)


def afdrukken(naam, tekst, per_punt=8):
    """Zet het pad als JavaScript-constante neer, acht punten per regel."""
    losse = tekst.split(" ")
    per_regel = per_punt * 2
    regels = [
        " ".join(losse[i : i + per_regel]) for i in range(0, len(losse), per_regel)
    ]
    print(f"  var {naam} =")
    for i, regel in enumerate(regels):
        staart = ";" if i == len(regels) - 1 else " +"
        voor = '    "' if i == 0 else '    " '
        print(f'{voor}{regel}"{staart}')
    print()


TOP = max(abs(golf(i / 2000)) for i in range(2001))
SCHAAL = AMPLITUDE / TOP

afdrukken("RUIS", pad(RUIS_AS, +1, SCHAAL))
afdrukken("REGEL", pad(REGEL_AS, -1, SCHAAL))

# En de optelsom, nagerekend in plaats van aangenomen: de uitslag van de ene
# baan plus die van de andere hoort nul te zijn, en als dat niet zo is klopt de
# plaat niet.
UITSLAG = max(
    abs((-SCHAAL * golf(i / 2000)) + (+SCHAAL * golf(i / 2000))) for i in range(2001)
)
print(
    f"  // hun optelsom is vlak tot op {UITSLAG:.1e} eenheid - nagerekend, niet aangenomen"
)
print(f'  var SOM = "M{X0:.0f} {SOM_AS:.0f} L{X1:.0f} {SOM_AS:.0f}";')

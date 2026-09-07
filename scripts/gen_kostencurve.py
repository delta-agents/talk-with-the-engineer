"""Genereert de kostencurve: wat het goedkoopste pakket kost per beschermingseis.

Dit is de vorm die de literatuur gebruikt. Van Dantzig (1956) en Eijgenraam
zetten de INVESTERINGSKOSTEN tegen het veiligheidsniveau en tellen daar de
resterende verwachte schade bij op; het optimum ligt waar die som minimaal is.

Wij kunnen alleen de eerste helft tekenen. De vermeden jaarschade hebben we
niet, dus de curve die je erbij nodig hebt om een optimum te vinden ontbreekt -
en dat is precies wat deze figuur zichtbaar moet maken.
"""

import sys

sys.path.insert(0, "src")

X0, X1, Y0, Y1 = 96, 520, 44, 250
NORM_LINKS, NORM_RECHTS = 36.0, 10.0  # links de kale piek, rechts de ambitie
KOSTEN_MAX = 2.0e6

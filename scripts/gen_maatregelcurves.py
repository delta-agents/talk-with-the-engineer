"""Genereert de responsecurven van de geprijsde maatregelen: piek tegen euro's.

Eén as voor alle drie, en die as is GELD. Dat is de eerlijke vergelijker: welke
maatregel koopt de meeste centimeter per euro. Normaliseren op "deel van wat
maximaal kan" zou afvoeren plat maken, want zijn bovengrens is twintig keer het
gemaal en dat is geen ambitie maar een zoekgrens.

Uitvoer: SVG-padjes voor de figuur `maatregelcurves` in teken/curven.js.
"""

import sys

sys.path.insert(0, "src")

NORM_CM = 30.0
GELD_MAX = 3.0e6  # de x-as loopt tot drie miljoen; daarboven is alles vlak
PIEK_MAX = 40.0
# Het vlak in de viewBox. X1 op 520 en niet op 600: rechts van de curve-einden
# moet ruimte zijn voor de labels, want een label OP een lijn is onleesbaar.
X0, X1, Y0, Y1 = 96, 520, 44, 250

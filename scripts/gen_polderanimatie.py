"""Genereert het @keyframes-blok van de polderanimaties uit de rekenkern.

Twee kanten, één kern met de klem gespiegeld:

* NAT   een bui van acht dagen, T=10. Het peil stijgt door de norm heen en de
        watergang zwelt buiten zijn oevers: `polderpeil`, `poldergemaal`,
        `polderregen`, `polderinundatie`.
* DROOG een neerslagtekort over het groeiseizoen, T=10 uit STOWA 2025-23. Het
        peil zakt door de peilband naar de bodem en de watergang krimpt:
        `polderdroogte`, `polderdorst`.

De bergingsvijver is een apart object en volgt zijn eigen twee blokken:
`polderberging` vult mee met de bui, `polderbergingdroog` valt droog met het
seizoen.

Uitvoer gaat naar stdout en hoort tussen de twee GEGENEREERD-bakens in
gegenereerd.css.
Zie de README onder "De animatie".
"""

import sys

sys.path.insert(0, "src")

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

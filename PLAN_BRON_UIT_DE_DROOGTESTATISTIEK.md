# Plan van aanpak — het bronvolume uit de droogtestatistiek

Versie 1 · 27 augustus 2026 · branch `feat/bronvolume-uit-de-droogtestatistiek` · **gebouwd**

**Stand van zaken: WP-A tot en met WP-H staan er, met de toetsen uit Sec. 5.** Wat er
gemeten is, op de referentiepolder van 4000 ha in Rijn en IJssel met een bron die in een
normaal jaar 12 mln m³ levert:

| uitkomst | waarde |
|---|---|
| de vraag bij T2 / T10 / T100 (Referentie) | 168 → 269 → 380 mm |
| het aanbod bij diezelfde drie | 12,00 → 10,93 → 9,35 mln m³ (fractie 1,00 → 0,91 → 0,78) |
| **T100 met een vaste bron tegenover een meebewegende** | **tekort 69 mm tegenover 136 mm** |
| Referentie tegenover Hd_2100 bij T10 | vraag 269 → 451 mm, aanbod 10,93 → 7,52 mln m³, tekort 0 → 252 mm |
| de bron als klem | `days_until_source_empty` = 113 van de 183 dagen bij T100 |
| monotonie van het aanbod | 0 van de 294 (waterschap, scenario, rivier) stijgt |
| de tekortcijfers | bit voor bit ongewijzigd |
| tests | 625 groen (was 606) |

De regel die eruit springt is de derde: bij een T100-droogte stond de helft van het tekort
niet in het antwoord, omdat de bron op zijn normaaljaar bleef staan terwijl de vraag met de
herhaaltijd meeliep.

Dit document sluit aan op `PLAN_UITWISSELING_EN_NETWERK.md` (WP14: de eindige bron) en op
`PLAN_DROOGTE_EIS_ALS_WATERSTAND.md` (de droogte-as). Het beantwoordt één vraag:

> **De watervraag schaalt met de herhaaltijd van de droogte, het aanbod niet. Wat is er
> nodig om het bronvolume net zo goed van de extremiteit van de droogte af te laten hangen
> als het neerslagtekort dat al doet?**

---

## 0. Hoe de bron er nu in zit

`available_source_volume_m3` (`models/…/supply.py:172`) is een los getal dat de beller
opgeeft; weglaten betekent onbeperkt. De keten erachter bevat geen enkele beslissing:

1. de tool zet hem in de frozen dataclass `Deficit` (`tools/…/supply.py:45`), met `inf`
   als het veld `None` is;
2. `solve_supply` / `evaluate_supply` → `_supply_result` (`solve.py:303`) →
   `simulate_deficit`;
3. in `simulate_deficit` (`simulate.py:785-811`) wordt de inlaatcapaciteit een reeks per
   uur: vol tot de cumulatieve levering het beschikbare volume passeert, een deelbaar
   laatste uur, daarna nul. Eén pass is exact, want de bronbeperking is inactief zolang er
   voorraad is.

Wat er **niet** gebeurt, en dat is precies het gat:

| | vraag | aanbod |
|---|---|---|
| komt uit | `drought_region` + `drought_scenario` + `drought_return_period` | de beller, uit zijn hoofd |
| schaalt met de herhaaltijd | ja | **nee** |
| schaalt met het klimaatscenario | ja | **nee** |
| staat in de uitvoer | `demand_mm` | niets |

En twee kleinere gaten van dezelfde soort: `DeficitResult` rékent
`days_until_source_empty` en `source_volume_used_m3` uit, maar `_supply_result` neemt ze
niet over, dus ze halen `SupplyOutput` niet. De bron is nu alleen zichtbaar in het tekort
dat hij veroorzaakt. Zodra het volume met de herhaaltijd meebeweegt is dat te weinig: dan
verandert het antwoord om een reden die de beller niet kan zien.

## 1. Wat er al ligt — en dat is meer dan `drought_statistics.json` laat zien

`drought_statistics.json` draagt één indicator, en zegt dat ook in zijn eigen `meta`:

> "alleen de indicator neerslagtekort; de andere STOWA-indicatoren (45-daagse som, droge
> dagen, Rijn/Maas-afvoer) staan hier niet in"

Maar de bron-Excels waaruit dat bestand is gebouwd dragen ze wel. Per RACMO-jaar staat er:

| kolom | inhoud |
|---|---|
| 1, 3 | maximaal cumulatief neerslagtekort (mm) + GEV-herhaaltijd — **dit gebruiken we al** |
| 4, 6 | minimale 45-daagse neerslagsom + herhaaltijd |
| 7, 8 | aantal droge dagen + herhaaltijd |
| **9, 10** | **minimale 7-daagse Rijnafvoer (m³/s) + GEV-herhaaltijd** |
| **11, 12** | **minimale 7-daagse Maasafvoer (m³/s) + GEV-herhaaltijd** |

Eenentwintig waterschappen × zeven scenario's × 240 jaren, alle vier de kolommen overal
gevuld, en de jaar-ID's zijn tussen de waterschappen identiek. De rivierafvoer is landelijk
en dus in elk bestand hetzelfde getal; het **neerslagtekort** is regionaal. Dat asymmetrie
bepaalt de vorm van de statistiek hieronder: de rivier is niet per waterschap, maar de
*koppeling* tussen droogte en rivier is dat wel, want de herhaaltijd van het tekort is
regionaal.

## 2. De statistische keuze — en waarom níet "dezelfde herhaaltijd"

De verleidelijke koppeling is: T10-droogte, dus T10-lage rivierafvoer. Die is fout, en dat
is te meten. Over de 240 RACMO-jaren van Aa en Maas:

| meting | waarde |
|---|---|
| corr(neerslagtekort, minimale 7-daagse Rijnafvoer) | **−0,31** |
| herhaaltijd van de Rijnafvoer in de jaren met een T10-tekort | **T3 tot T58** |

Een T10-droogte in de polder komt dus *niet* met een T10-droogte op de rivier. Aflezen bij
dezelfde herhaaltijd zou een correlatie van 1 opleggen die er niet is, en zou het aanbod
systematisch te laag zetten.

**De koppeling die er wel is, is conditioneel.** Elke rij is één jaar, dus tekort en
rivierafvoer staan naast elkaar: je kunt vragen wat de rivier deed in de jaren waarin dít
waterschap een tekort van deze zeldzaamheid had. Twee schattingsvormen zijn geprobeerd:

| vorm | gedrag |
|---|---|
| mediaan van de *k* dichtstbijzijnde jaren in log T | ruis; niet-monotoon, en bij T50–T100 eenzijdig omdat het venster alleen naar beneden bestaat (Fryslân: 0,86 → 0,92 → 0,92 van T25 naar T100) |
| **log-log-regressie van de afvoer op de herhaaltijd van het tekort** | glad, monotoon, geen staartartefact; en de zwakte van het verband komt als `r` mee naar buiten |

Het wordt de regressie: `ln Q_min7 = a + b · ln T_tekort`, per waterschap, per scenario, per
rivier, over de jaren waarvoor het bestand een numerieke herhaaltijd geeft (T ≥ 2 — exact
dezelfde jaren die `build_drought_statistics.py` nu al gebruikt voor het tekort).

**Twee klemmen, allebei omdat het model iets niet mag zeggen wat de statistiek niet draagt:**

* `b ≤ 0`. Bij 15 van de 294 fits (bijna allemaal Maas) is de helling licht positief — ruis
  bij `r ≈ −0,3`. Ongeklemd zou de tabel zeggen dat een zeldzamere droogte *meer* aanvoer
  oplevert. Geklemd wordt het "de herhaaltijd doet hier niets", en dat is de eerlijke lezing.
* `fractie ≤ 1`. Een tweejaarlijkse droogte komt in de Referentie op 1,02 uit; het
  normaaljaar is de mediaan over álle 240 jaren, natte inbegrepen, dus binnen de ruis is dat
  gelijk. Boven de 1 uitkomen leest in een droogtetool als een fout.

## 3. Wat het model krijgt: een fractie, geen kubieke meters

De uitkomst van §2 is een **beschikbaarheidsfractie** ten opzichte van een normaal jaar:

```
availability_fraction(waterschap, scenario, T, rivier)
    = min(1, Q_fit(waterschap, scenario, T, rivier) / Q_normaaljaar(rivier))

Q_normaaljaar = mediaan van de minimale 7-daagse afvoer over de 240 jaren van
                het Referentie-scenario:  Rijn 1077 m³/s, Maas 50,2 m³/s
```

en de tool rekent daarmee:

```
available_source_volume_m3 = source_volume_normal_year_m3 × availability_fraction
```

**Waarom een fractie en geen absoluut volume.** De afvoer bij Lobith is niet het water bij
jouw inlaat. Daartussen zitten het verdeelnetwerk, het Distributiemodel en de
verdringingsreeks, en die kennen wij hier niet. Een m³ uit deze statistiek zou een getal
verzinnen; een fractie laat de lokale kennis waar hij hoort — bij de beller, die weet wat
zijn bron in een normaal jaar levert — en voegt eraan toe wat de statistiek wél weet: hoeveel
minder dat wordt naarmate de droogte extremer is en het klimaat verder opschuift.

**Wat de fractie oplevert**, voor Rijn en IJssel (fractie t.o.v. een normaal jaar):

| scenario | rivier | T2 | T10 | T100 | `r` van de fit |
|---|---|---|---|---|---|
| Referentie | Rijn | 1,00 | 0,91 | 0,78 | −0,36 |
| Referentie | Maas | 0,99 | 0,84 | 0,66 | −0,46 |
| Hd_2050 | Rijn | 0,85 | 0,73 | 0,60 | −0,44 |
| Hd_2100 | Rijn | 0,70 | 0,63 | 0,54 | −0,38 |
| Hd_2100 | Maas | 0,69 | 0,68 | 0,67 | −0,07 |

Daar staat meteen de belangrijkste inhoudelijke uitkomst van dit plan in, en hij is niet wat
je zou raden:

> **Het klimaatscenario doet meer met het aanbod dan de zeldzaamheid van de droogte.** Van
> T2 naar T100 zakt het aanbod ongeveer 20 %; van Referentie naar Hd_2100 zakt het ongeveer
> 30 %, en die twee stapelen tot bijna een halvering. Aan de vraagkant is het net andersom
> gerangschikt (T2→T100 is een factor 2, Referentie→Hd_2100 ongeveer +68 % bij T10). Vraag en
> aanbod bewegen dus langs verschillende assen uit elkaar, en dat is precies wat een model
> dat er maar één van kent niet kan laten zien.

**De spreiding hoort mee naar buiten.** De residuen van de fit lopen van ×0,80 (p10) tot
×1,27 (p90). Bij `r ≈ −0,3` is de fractie een verwachtingswaarde met een brede band eromheen,
en dat mag niet in één getal verdwijnen. Beide randen gaan de uitvoer in, als
`sensitivity`-regel én in de caveat.

**Eén eigenschap van de indicator moet expliciet worden benoemd**: het is de minimale
**7-daagse** afvoer, dus de diepste week. Die als index op een volume over 183 dagen
loslaten is conservatief — over het hele groeiseizoen gemiddeld valt de afvoer minder ver
terug dan in de diepste week. Het antwoord ligt daarmee aan de veilige kant, en dat hoort in
de caveat te staan en niet in een voetnoot.

---

## 4. Werkpakketten

### WP-A · de statistiek erbij bouwen

`scripts/build_drought_statistics.py` leest de kolommen 9–12 mee en schrijft per
waterschap/scenario een blok naast `return_periods`:

```json
"source_availability": {
  "Rijn": {"return_periods": {"2": 1.017, "5": 0.956, …},
           "spread_factor": [0.80, 1.25], "fit_r": -0.36},
  "Maas": { … }
}
```

`meta` krijgt `source_reference` (indicator, eenheid, de twee normaaljaar-medianen, de
methode, de twee klemmen) en de caveat-regel die zegt dat de rivierafvoer er niet in zit
wordt vervangen door wat er nu wél in zit en hoe.

### WP-B · toegang

`utils_drought.py` krijgt `source_availability(region, scenario, return_period, river)` met
hetzelfde driedelige contract als `cumulative_deficit_mm`: een getal, `None` wanneer de
herhaaltijd buiten de reeks van dat scenario valt, en een `KeyError` bij een onbekende
regio/scenario/rivier — een aanroepfout en een ontbrekende statistiek horen niet op dezelfde
manier terug te komen. Plus `available_rivers()`.

### WP-C · het invoermodel

De droogte-as verhuist naar een eigen module `models/…/drought.py`, met de constanten en twee
mixins; `supply.py` her-exporteert de constanten zodat bestaande imports blijven werken.

* `DroughtStatisticInput` — het bestaande tripel, ongewijzigd van gedrag.
* `SourceVolumeInput` — `available_source_volume_m3` (tak A, ongewijzigd) plus
  `source_volume_normal_year_m3` en `source_river` (tak B). Dezelfde vorm als het tekort al
  heeft: één van de twee, allebei tegelijk wordt geweigerd met uitleg, tak B zonder tripel of
  zonder rivier ook. De resolutie draait ná die van het tekort, want het venster moet bekend
  zijn. `_source_availability_fraction` wordt een `PrivateAttr` met property, net als
  `_cumulative_deficit_mm`: het is een uitkomst van het valideren en hoort niet in het
  invoerschema.

Geen `default` in het schema, `hide_null_branch` op de nieuwe velden — om dezelfde reden als
bij alle andere: een MCP-client vult geadverteerde standaardwaarden in en dan is niet meer te
zien wat de beller heeft weggelaten.

### WP-D · de tools

Beide aanvoertools geven het opgeloste volume door aan `Deficit`, melden de herkomst in
`data["source_statistic"]` (rivier, fractie, spreiding, normaaljaar-volume, het resulterende
volume, `fit_r`, bron), en zetten `source_volume_is_modelled` ook in de afgeleide tak.
`_supply_source_origin_caveat` krijgt een afgeleide tak die drie dingen zegt die de opgegeven
tak niet hoeft te zeggen: dat het verband zwak is (`r`), dat de spreiding ×0,8–1,3 is, en dat
de 7-daagse indicator conservatief is over een seizoen.

`optimize` hoeft niet aangepast: die krijgt zijn `Deficit` van de aanroeper en profiteert
automatisch zodra die het afgeleide volume meegeeft.

### WP-E · de bron zichtbaar in de uitvoer

`SupplySolveResult` en `SupplyOutput` krijgen `available_source_volume_m3`,
`source_volume_used_m3` en `days_until_source_empty` (`None` in plaats van `inf`);
`_supply_result` neemt ze over uit `DeficitResult`. De beschrijvende zin noemt de bron zodra
hij klemt — "de bron is na 41 van de 183 dagen leeg" is de uitlezing waar een afweging over
gaat, en hij bestaat al in de kern.

In de afgeleide tak vult de tool bovendien de `sensitivity`-lijst, die bij aanvoeren tot nu
toe altijd leeg was: het antwoord bij de p10- en de p90-rand van de fractie. Twee extra
doorrekeningen van elk ~5 ms.

### WP-F · de allocatietool

`AllocationInput` krijgt dezelfde twee mixins, zodat het bronvolume dat de verdringingsreeks
verdeelt uit dezelfde statistiek kan komen. De tekorten per knoop blijven zoals ze zijn — die
zijn per gebied en dit plan gaat over de bron.

### WP-G · toetsen

Zie §5.

### WP-H · handleiding en notebook

`read_me` (de bronnenlijst en de droge-kant-paragraaf) en
`docs/examples/notebooks/vuistregels.ipynb` noemen de afgeleide tak, met een echt getal.

---

## 5. Toetsen — de definition of done

| # | toets | eis |
|---|---|---|
| 1 | schema tegen asset | `DROUGHT_*` en de nieuwe rivierlijst blijven gelijk aan wat het bestand draagt (uitbreiding van `test_the_schema_enums_cannot_drift_from_the_asset`) |
| 2 | monotoon in T | de fractie daalt of blijft gelijk van T2 naar T100, in alle 21 × 7 × 2 combinaties |
| 3 | begrensd | 0 < fractie ≤ 1 overal |
| 4 | klimaatsignaal | Hd_2100 ligt onder Referentie bij gelijke T, in elk waterschap, voor de Rijn |
| 5 | vraag en aanbod lopen uiteen | in Rijn en IJssel, Referentie, dezelfde polder: van T2 naar T100 stijgt `demand_mm` en daalt `available_source_volume_m3`, en `shortfall_mm` stijgt harder dan bij een vaste bron |
| 6 | de twee takken sluiten elkaar uit | `available_source_volume_m3` naast `source_volume_normal_year_m3` geeft een `ModelRetry`; tak B zonder tripel of zonder rivier ook |
| 7 | tak A ongewijzigd | een aanroep met alleen `available_source_volume_m3` levert bit voor bit hetzelfde antwoord als op `main` |
| 8 | onbeperkt blijft de default | zonder een van beide takken is het gedrag ongewijzigd, en de dragende caveat gaat gewoon af |
| 9 | buiten de reeks | een afgeleide bron bij een T waar het scenario geen waarde heeft weigert met dezelfde uitleg als het tekort dat doet, en extrapoleert niet |
| 10 | de bron in de uitvoer | `days_until_source_empty` is gevuld zodra de bron binnen de periode leegraakt, en `None` als hij het houdt |
| 11 | de spreiding | de `sensitivity`-regel staat er in de afgeleide tak, met beide randen |
| 12 | massabalans | `source_volume_used_m3 ≤ available_source_volume_m3`, tot machineprecisie |
| 13 | de suite | 606 groen blijft groen |

## 6. Wat er niet in zit

* **De verdeling naar jouw inlaat.** De fractie is een index van de rivier. Wat daarvan bij
  een specifieke inlaat aankomt is het Distributiemodel en de verdringingsreeks, en dat blijft
  buiten dit model — de bestaande caveat over de herkomst van het bronvolume blijft dus staan,
  in een aangescherpte vorm.
* **Een tweede bron.** Eén rivier per aanroep. Een gebied dat uit Rijn én Maas trekt kiest de
  bindende, of rekent twee keer.
* **Grondwater en het regionale systeem.** De statistiek kent alleen de twee rivieren.
* **De 45-daagse neerslagsom en het aantal droge dagen.** Ook beschikbaar in de bron-Excels,
  ook niet in dit plan: ze beschrijven de droogte en niet het aanbod.
* **`sensitivity_of` voor de aanvoertools in het algemeen.** De aanvoertools roepen hem nog
  steeds niet aan; WP-E vult alleen de bron-regel. Dat is een eigen vraag.

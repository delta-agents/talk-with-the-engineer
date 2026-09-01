# Plan van aanpak — de schil van de pakketzoeker waar maken

`find_package_given_protection` staat op branch `feat/pakketzoeker-als-tool` en de kern
eronder is stil: anker exact op de losse afvoertool, kosten monotoon in de eis,
deterministisch. De schil eromheen is dat niet. Het bevindingenrapport
(`bevindingenrapport-pakketzoeker.md`) telt dertien reproduceerbare bevindingen, en §6
daarvan vouwt ze tot vier ingrepen en vijf spanningen. Dit plan is de uitvoering van die
vier ingrepen, in die volgorde, met per ingreep de toets die hem dichtzet.

Het doel in één zin: **elke zin en elk veld dat de tool teruggeeft is waar, draagt een
getal of een reden, en belooft niets dat de uitvoer niet waarmaakt.**

---

## 0. Wat er wordt gedaan, in één tabel

| stap | ingreep | dekt | raakt de rekenkern |
|---|---|---|---|
| K1 | twee knoppen eruit: `max_mix_size` en `switch_prices` | P3, P13, deel P12 | nee |
| K2 | de validatorhelft van de invoergrenzen | P1, P2 | nee |
| K3 | de description wordt een getaldragend sjabloon per status | P5t, P6t, P7t, P8, P9, P11 | nee |
| K4 | het antwoord draagt wat er speelt: invoerposten en de prijsband | P4, P10 | nee |

De rekenkern verandert niet. De dure paden van P5 en P7 (de kern stérker maken in plaats
van de tekst wáár maken) staan bewust buiten dit plan; zie §5.

Elke stap is een eigen commit met eigen toetsen, in deze volgorde — K1 eerst, want elke
andere volgorde bouwt weggooiwerk: validators voor een veld dat verdwijnt, sjablonen voor
een status die vervalt, budgetmetingen op een schema dat nog krimpt.

---

## 1. K1 — het mes: twee knoppen eruit

**Wat.** `max_mix_size` en `switch_prices` verdwijnen uit `OptimizeInput`; `detail`
blijft. Mee verdwijnen: `unexplored_mixes` en `switch_prices` uit `OptimizeOutput`, het
hele `SwitchPriceReading`-model, `_unexplored_mixes` en `_switch_prices` uit de tool, de
afkap-tak in de statuskeuze (`action_infeasible` kan niet meer ontstaan: de zoektocht is
altijd volledig), en de bijbehorende passages in description-opbouw en handleiding.

**Waarom dit een planwijziging is en geen fix (S3).** Het oorspronkelijke plan (§5.2 en
§5.3 van `PLAN_PAKKETZOEKER_ALS_TOOL.md`) beloofde `max_mix_size` als invoer en de
omslagprijzen "ingevouwen" in de uitvoer. Dat besluit wordt hier teruggedraaid, op twee
metingen en één ontwerpregel:

* `max_mix_size` beantwoordt geen vraag die een waterschap stelt — "wat kan één maatregel
  alleen" staat al in `detail` — en zijn nul- en negatieve waarden produceerden antwoorden
  die zichzelf tegenspraken (P3);
* `switch_price_of` zegt in zijn eigen docstring dat hij geen toolaanroep hoort te zijn,
  en de meting bevestigt dat: met een droogte-eis loopt hij over de 120 s, precies in het
  geval waarin aanvoeren prijsloos is en de omslagprijs interessant wordt;
* het verhaal — geen prijs is niet gratis, en bij welke prijs kantelt het antwoord —
  blijft volledig: de `priceless`-posten dragen het per antwoord, en de prijsas-analyse
  krijgt een cel in het voorbeeldnotebook, waar minuten rekentijd geen probleem zijn.

**Toetsen.** De tests voor de geschrapte paden vervallen
(`test_the_switch_price_is_read_off_instead_of_invented`,
`test_a_truncated_search_does_not_claim_the_problem_is_impossible`); daarvoor in de
plaats komt één toets die vastlegt dat de zoektocht altijd volledig is
(`data.mixes_examined == 31`). De omslagprijs-kernfuncties behouden hun eigen tests in
`test_optimize.py` — de kern verliest niets, alleen de deur verdwijnt.

## 2. K2 — de validatorhelft

**Wat.** Eén `model_validator` in `OptimizeInput` die de grenzen handhaaft die het schema
al adverteert, met een uitlegzin per veld in de stijl van de bestaande weigeringen:

| veld | grens | zin moet zeggen |
|---|---|---|
| `max_dh_total_m` | ≥ 0 | een negatieve inundatienorm bestaat niet; nul betekent "geen stijging toegestaan" |
| `min_storage_mm` | ≥ 0 | een negatieve voorraadeis is altijd gehaald en dus geen eis |
| `max_shortfall_mm` | ≥ 0 | nul is streng maar geldig; negatief is geen tekort |
| `deficit_mm_per_day` | > 0 | een negatief tekort is een natte periode; daarvoor zijn de natte tools |
| `length_days` | ≥ 1 | nul dagen droogte is geen droogte (dit is de P1-crash) |
| `days_to_retain_discharge` | ≥ 0 | zelfde zin als de retentietools al voeren |

Bewust het uitlegzin-patroon (zoals `RetentionInputGivenH`) en niet het kale `gt=0`
(zoals `SupplyInputGivenH`): de docstring van `hide_null_branch_and_bound` schrijft de
eerste voor, en de pydantic-dump van de tweede is precies de foutvorm die de rest van het
systeem vermijdt. Het gat is aantoonbaar lokaal — elke bestaande tool handhaaft al — dus
er wordt geen gedeelde code geraakt.

**Toetsen.** Per veld één weigeringstest op de grenswaarde eronder, plus de twee randen
die geldig moeten blijven: `max_shortfall_mm: 0` (bestaat al) en `min_storage_mm: 0`.

## 3. K3 — de description wordt weer huisstijl

**Wat.** De drie handgeschreven proza-takken in `find_package.py` en het gebruik van de
leszinnen uit `describe_region`/`describe_step_cost_plateau` maken plaats voor één
sjabloon per status in `descriptions.py`, naast `describe_inverse` en `describe_forward`,
per taal opgebouwd zoals die twee dat al doen. De maat is de huisregel: **elke zin draagt
een getal**, en uitleg die niet aan dít antwoord hangt staat in het schema en in de
handleiding, niet in elke uitvoer.

De sjablonen, met wat ze per status moeten dragen:

* **`exact`** — de eisen met hun getallen, het pakket met maatvoering en eenheid, de
  kosten met band over het geprijsde deel, en per maatregel het interval alleen wanneer
  de bovenkant uit de prijsband komt: *"Om bij een bui van eens per 1000 jaar onder
  100 cm te blijven en 20 mm voorraad te houden: afvoeren 5,7 m³/s en peilopzet 57 cm,
  10,97 mln euro (10,6–11,7 over het geprijsde deel; peilopzet kost drooglegging, geen
  euro's). Het gemaal mag binnen die band 5,7 tot 6,2 m³/s."* De vervangingslezing komt
  er alleen bij als hij de rangorde verándert, mét de pakketten en getallen.
* **`no_measure_needed`** — de twee getallen die het huissjabloon voor deze status al
  voorschrijft: de stijging zonder maatregel en de grens waar die al onder blijft (en bij
  een voorraadeis: de voorraad en de eis).
* **`problem_infeasible`** — per eis het gevraagde getal en de kleinste gevonden
  overschrijding, zonder de belofte dat minder onhaalbaar is.

Mee in deze stap, want het is dezelfde tekstlaag:

* **P5-tekst**: de veldbeschrijving van `missed_by` wordt "de kleinste overschrijding
  over de onderzochte combinaties" — punt, zonder "minder is niet te halen";
* **P6**: `MeasureRangeReading` krijgt `magnitude_max_source: Literal["prijsband",
  "zoekgrens"]`, en de description noemt alleen intervallen met bron prijsband. De
  zoekgrens blijft in het veld staan — hij is informatie — maar wordt nooit meer als
  koopadvies verwoord;
* **P7**: de rol `absent` verliest zijn universele duiding; de zin wordt "doet in dit
  gebied niet mee" en de veldbeschrijving legt beide oorzaken uit (draagt niet bij, óf
  past niet binnen de prijsband van het beste pakket);
* **P8**: vervalt vanzelf — sjablonen zijn per taal, zoals `describe_inverse`;
* **P9**: bij `no_measure_needed` is `ranges` leeg; het lege `best`-pakket blijft, want
  "niets doen" ís het antwoord.

**Toetsen.** Twee structurele bewakers naast de inhoudelijke: (1) de descriptions van
twee verschillende vragen delen geen enkele zin langer dan 40 tekens — dat maakt
lesstof-in-elke-uitvoer structureel onmogelijk; (2) elke zin in een `exact`-description
bevat een cijfer. Plus per status een inhoudstest en een Engelse variant zonder
Nederlandse fragmenten.

## 4. K4 — het antwoord draagt wat er speelt

**Wat.** Twee toevoegingen, geen tekst maar velden:

* de tool roept `priceless_posts(input, ...)` aan, zodat een opgegeven `level_margin_m`
  en een staande `target_level_rise_m` als post in `priceless` verschijnen — de 28 %
  stille korting van P4 krijgt daarmee zijn naam. De posten van de invoer en die van de
  gekozen maatregelen worden op `topic` ontdubbeld, met het onderscheid in de
  `magnitude`-tekst ("57 cm opzet als maatregel" naast "20 cm die er al staat");
* `OptimizeOutput` krijgt één veld `priced_cost_range` naast `cost_epsilon`: het interval
  over het geprijsde deel van het beste pakket, waar de epsilon uit wordt afgeleid. Eén
  veld op het topniveau en bewust niet op `PackageReading` — daar zou het vier keer in
  het gederefereerde schema staan.

De vervangingsbanden blijven onuitgegeven; `indistinguishable_as_replacement` is een
lijst pakketten en de description noemt het criterium alleen wanneer hij de lijst vult.
Wie de banden wil, zet `detail` aan zodra daar behoefte aan blijkt — niet eerder.

**Toetsen.** De P4-reproductie als regressietest: 30 cm marge verlaagt de kosten én
levert een post op; een staande opzet levert een post naast de maatregel-post. En het
epsilon-veld is narekenbaar: `cost_epsilon == (hoog - laag) / cost` uit het nieuwe veld.

---

## 5. Buiten dit plan, met reden

* **De kern versterken (S1-duur).** Een overtreding-minimaliserende doorrekening bij
  onhaalbaarheid, en een echte draagt-niet-bij-diagnose (sweep met oneindig budget)
  zouden de claims van P5 en P7 wáár maken in plaats van ze te verzwakken. Eigen
  werkpakket, alleen bij gebleken behoefte — eerst waar worden, dan sterker worden.
* **De toolsetbrede budgetbewaking (S4/P12).** De budgettoets ziet 137.502 tekens
  uitvoerschema niet, over álle tools. Eigen issue, te openen na K1 (dan is de grootste
  post al gekrompen en meet je het echte restant), met daarin ook het S5-besluit: het
  uitvoerschema is een leeskanaal, dus dedupliceren of budgetteren, niet strippen.
* **Peilmarge als maatregel in de zoekruimte.** Issue #68.
* **De vlakvraag.** `VERKENNING_BUDGETVRAAG.md`; dit plan verandert niets aan de
  spiegelbaarheid van het invoerschema (de twee herhaaltijden blijven scalair en worden
  daar lijsten).

## 6. Volgorde en oplevering

1. K1, eigen commit, suite groen, schema-omvang opnieuw gemeten en in het
   bevindingenrapport bijgeschreven;
2. K2, eigen commit, weigeringstests erbij;
3. K3, eigen commit — de grootste; het sjabloon eerst als tekst naast de huidige uitvoer
   leggen op de drie demoscenario's voordat er code wordt geraakt;
4. K4, eigen commit, regressietests op P4 en P10;
5. daarna: S4-issue openen met de nameting, en de notebook-cel voor de prijsas-analyse.

Na stap 4 hoort het bevindingenrapport per bevinding de status te dragen (verholpen in
welke commit, of bewust open met verwijzing), zodat het rapport het toetsdocument van
deze branch blijft.
